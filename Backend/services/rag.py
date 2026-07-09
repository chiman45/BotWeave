"""
services/rag.py
---------------
Retrieval-Augmented Generation (RAG) pipeline.

Components
----------
- Text chunking (no external dependency)
- Embedding via local Ollama embedding model
- Vector store via ChromaDB (persistent, per-bot)
- Keyword search via BM25 (rank_bm25 library)
- Reciprocal Rank Fusion (RRF) to merge both result lists
- Background KB embed jobs with per-job progress tracking

All vector stores are written to VECTOR_STORE_ROOT/<businessId>/.
"""

import os
import re
import logging
import threading
import pickle
from typing import Dict, List, Optional, Tuple

import requests

import config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory stores — module-level; safe because Flask runs in a single process.
# ---------------------------------------------------------------------------

# job_id -> {status, progress, total, chunks, error}
_kb_jobs: Dict[str, Dict] = {}

# business_id -> (file_mtime, BM25Okapi, chunk_list) — invalidated on file change
_bm25_cache: Dict[str, Tuple] = {}

_KB_COLLECTION = 'knowledge_base'


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = 500, overlap: int = 60) -> List[str]:
    """
    Split text into overlapping fixed-size character windows.
    No external tokenizer required — works on any script.
    """
    chunks: List[str] = []
    text = text.strip()
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> List[float]:
    """Request a single embedding vector from the local Ollama embedding model."""
    resp = requests.post(
        f'{config.OLLAMA_BASE_URL}/api/embeddings',
        json={'model': config.OLLAMA_EMBED_MODEL, 'prompt': text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['embedding']


# ---------------------------------------------------------------------------
# BM25 helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Unicode-aware tokeniser: splits on non-word chars, lowercases."""
    return re.findall(r'\w+', text.lower())


def _load_bm25(business_id: str) -> Tuple[Optional[object], Optional[List[str]]]:
    """
    Load a BM25 index from disk with mtime-based cache invalidation.
    Returns (bm25_obj, chunks) or (None, None) if the index does not exist.
    """
    index_path = os.path.join(config.VECTOR_STORE_ROOT, business_id, 'bm25_index.pkl')
    if not os.path.exists(index_path):
        return None, None
    try:
        mtime = os.path.getmtime(index_path)
        cached = _bm25_cache.get(business_id)
        if cached and cached[0] == mtime:
            return cached[1], cached[2]
        with open(index_path, 'rb') as fh:
            data = pickle.load(fh)
        bm25_obj = data['bm25']
        chunks   = data['chunks']
        _bm25_cache[business_id] = (mtime, bm25_obj, chunks)
        log.info("[BM25] Loaded index for %s (%d chunks)", business_id, len(chunks))
        return bm25_obj, chunks
    except Exception as exc:
        log.warning("[BM25] Failed to load index for %s: %s", business_id, exc)
        return None, None


def _bm25_search(
    business_id: str, query: str, top_k: int
) -> List[Tuple[str, float]]:
    """
    Run BM25 keyword search over the bot's persisted BM25 index.
    Returns [(chunk_text, score), ...] sorted by score desc, or [] if unavailable.
    """
    bm25_obj, chunks = _load_bm25(business_id)
    if bm25_obj is None or not chunks:
        return []
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = bm25_obj.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = [(chunks[i], float(scores[i])) for i in top_indices if scores[i] > 0]
    log.info("[BM25] Top scores: %s", [round(s, 3) for _, s in results[:4]])
    return results


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------

def _rrf_merge(
    vector_results: List[Tuple[str, float]],   # (text, distance) — lower is better
    bm25_results:   List[Tuple[str, float]],   # (text, score)    — higher is better
    top_k: int,
    k: int = 60,
) -> List[str]:
    """
    Reciprocal Rank Fusion across vector and BM25 ranked lists.
    Formula: rrf(d) = sum( 1 / (k + rank_i(d)) ) across all lists.
    """
    rrf: Dict[str, float] = {}
    for rank, (text, _) in enumerate(vector_results):
        rrf[text] = rrf.get(text, 0.0) + 1.0 / (k + rank + 1)
    for rank, (text, _) in enumerate(bm25_results):
        rrf[text] = rrf.get(text, 0.0) + 1.0 / (k + rank + 1)
    merged = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    log.info(
        "[RRF] vector=%d bm25=%d merged=%d -> top %d",
        len(vector_results), len(bm25_results), len(merged), top_k,
    )
    return [text for text, _ in merged[:top_k]]


# ---------------------------------------------------------------------------
# RAG query
# ---------------------------------------------------------------------------

def rag_query(business_id: str, query: str) -> str:
    """
    Hybrid retrieval: ChromaDB vector search + BM25, fused via RRF.

    Returns the top-K chunks concatenated as a single string ready for
    insertion into an LLM prompt. Returns '' if no vector store exists.

    Kill switch: set RAG_BM25_ENABLED=false in .env to use pure vector search.
    """
    store_path = os.path.join(config.VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        log.warning("[RAG] No vector store found for bot %s", business_id)
        return ''

    TOP_K      = 5   # final chunks passed to the LLM
    CANDIDATES = 10  # candidates retrieved from each source before merging

    try:
        import chromadb

        query_embedding = get_embedding(query)
        client     = chromadb.PersistentClient(path=store_path)
        collection = client.get_collection(_KB_COLLECTION)
        total      = collection.count()
        log.info("[RAG] Vector search over %d chunks for bot %s", total, business_id)

        results   = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(CANDIDATES, total),
            include=['documents', 'distances'],
        )
        docs      = results.get('documents', [[]])[0] or []
        distances = results.get('distances',  [[]])[0] or []

        # Auto-detect distance metric (cosine <1 vs. L2 potentially >10).
        if config.RAG_MAX_DISTANCE > 0:
            max_dist = config.RAG_MAX_DISTANCE
        elif distances and max(distances) > 10:
            median_d = sorted(distances)[len(distances) // 2]
            max_dist = median_d * 1.2
            log.info("[RAG] L2 metric detected; auto-threshold=%.1f", max_dist)
        else:
            max_dist = 0.55  # cosine: keep chunks with >= 45% similarity

        paired   = list(zip(docs, distances)) if distances else [(d, 0.0) for d in docs]
        filtered = [(doc, dist) for doc, dist in paired if dist <= max_dist]

        if not filtered and docs:
            filtered = paired[:max(1, config.RAG_FALLBACK_TOP_K)]
            log.warning("[RAG] Distance filter removed all chunks; using top fallback set")

        log.info(
            "[RAG] Vector: retrieved=%d kept=%d (max_dist=%.2f)",
            len(docs), len(filtered), max_dist,
        )

        vector_results = [(doc, dist) for doc, dist in filtered]

        # BM25 pass
        if config.RAG_BM25_ENABLED:
            bm25_results = _bm25_search(business_id, query, top_k=CANDIDATES)
            if not bm25_results:
                log.info("[RAG] BM25 index missing or no matches — using pure vector results")
        else:
            bm25_results = []

        final_chunks = (
            _rrf_merge(vector_results, bm25_results, top_k=TOP_K)
            if bm25_results
            else [doc for doc, _ in vector_results[:TOP_K]]
        )

        return '\n\n'.join(final_chunks)

    except Exception as exc:
        log.error("[RAG] Query failed for %s: %s", business_id, exc)
        return ''


# ---------------------------------------------------------------------------
# KB file parsing
# ---------------------------------------------------------------------------

def parse_kb_file(raw: str, ext: str) -> List[str]:
    """
    Parse raw file content into a list of text segments.
    Supports: .json (with 'content' key), .csv, .txt, .md.
    """
    import json as _json
    import csv as _csv
    import io as _io

    if ext == 'json':
        try:
            data = _json.loads(raw)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                if 'content' in data[0]:
                    texts = []
                    for item in data:
                        content = item.get('content', '')
                        url     = item.get('url', '')
                        title   = item.get('title', '')
                        section = item.get('section', '')

                        # Strip navigation breadcrumbs.
                        home_idx = content.find('Home >')
                        if home_idx != -1:
                            content = content[home_idx + len('Home >'):]

                        # Strip common footer noise.
                        for marker in ('Contact IIIT', 'Sitemap Terms', 'Back to Top',
                                       'Plot No. 7, Sector 24'):
                            idx = content.find(marker)
                            if idx != -1:
                                content = content[:idx]
                                break

                        content = content.strip()
                        if not content:
                            continue

                        parts = [f"Source URL: {url}"]
                        if title:   parts.append(f"Page Title: {title}")
                        if section: parts.append(f"Section: {section}")
                        parts.append('')
                        parts.append(content)

                        key_links = item.get('key_links', [])
                        if key_links:
                            parts.append('')
                            parts.append('Related links:')
                            for lnk in key_links[:15]:
                                lnk_text = lnk.get('text', '')
                                lnk_url  = lnk.get('url', '')
                                if lnk_text and lnk_url:
                                    parts.append(f"  - {lnk_text}: {lnk_url}")
                        texts.append('\n'.join(parts))
                    return texts
                return [_json.dumps(item, ensure_ascii=False) for item in data]
            if isinstance(data, list):
                return [str(item) for item in data]
            if isinstance(data, dict):
                return [f"{k}: {v}" for k, v in data.items()]
        except Exception:
            pass
        return [raw]

    if ext == 'csv':
        reader = _csv.DictReader(_io.StringIO(raw))
        return [', '.join(f"{k}: {v}" for k, v in row.items()) for row in reader if row]

    # .txt / .md — split on blank lines
    return [p.strip() for p in raw.split('\n\n') if p.strip()] or [raw]


# ---------------------------------------------------------------------------
# Background embed job
# ---------------------------------------------------------------------------

def start_embed_job(business_id: str, filename: str, chunks: List[str]) -> str:
    """
    Kick off a background thread to embed all chunks and write them to ChromaDB.
    Returns the job_id that the caller can use to poll progress.
    """
    import uuid
    job_id = str(uuid.uuid4())
    _kb_jobs[job_id] = {
        'status':   'processing',
        'progress': 0,
        'total':    len(chunks),
        'chunks':   0,
        'error':    None,
    }
    t = threading.Thread(
        target=_embed_job_worker,
        args=(job_id, business_id, filename, chunks),
        daemon=True,
    )
    t.start()
    log.info("[RAG] Started embed job %s for bot %s (%d chunks)", job_id, business_id, len(chunks))
    return job_id


def get_job_status(job_id: str) -> Optional[Dict]:
    """Return the status dict for the given job ID, or None if not found."""
    return _kb_jobs.get(job_id)


def _embed_job_worker(
    job_id: str, business_id: str, filename: str, all_chunks: List[str]
) -> None:
    """
    Worker function that runs in a daemon thread.
    Embeds chunks in parallel (4 workers), then persists to ChromaDB and BM25.
    """
    import uuid
    import chromadb
    from concurrent.futures import ThreadPoolExecutor, as_completed

    job   = _kb_jobs[job_id]
    total = len(all_chunks)
    all_embeddings: List[Optional[List[float]]] = [None] * total
    completed_count = [0]
    lock = threading.Lock()

    def _embed_one(idx: int, text: str) -> Tuple[int, List[float]]:
        resp = requests.post(
            f'{config.OLLAMA_BASE_URL}/api/embeddings',
            json={'model': config.OLLAMA_EMBED_MODEL, 'prompt': text},
            timeout=60,
        )
        resp.raise_for_status()
        return idx, resp.json()['embedding']

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_embed_one, i, chunk): i
                for i, chunk in enumerate(all_chunks)
            }
            for future in as_completed(futures):
                idx, vec = future.result()
                all_embeddings[idx] = vec
                with lock:
                    completed_count[0] += 1
                    done = completed_count[0]
                job['progress'] = min(round((done / total) * 95), 95)
                if done % 200 == 0 or done == total:
                    log.info("[RAG] Job %s: %d/%d chunks embedded", job_id, done, total)

        log.info("[RAG] Job %s: embedding complete, writing to ChromaDB", job_id)

        store_path = os.path.join(config.VECTOR_STORE_ROOT, business_id)
        os.makedirs(store_path, exist_ok=True)

        client = chromadb.PersistentClient(path=store_path)
        try:
            client.delete_collection(_KB_COLLECTION)
        except Exception:
            pass
        collection = client.create_collection(
            _KB_COLLECTION, metadata={'hnsw:space': 'cosine'}
        )
        ids       = [str(uuid.uuid4()) for _ in all_chunks]
        metadatas = [{'source': filename}] * len(all_chunks)
        collection.add(
            documents=all_chunks,
            embeddings=all_embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        # Build and persist BM25 index alongside the ChromaDB store.
        try:
            from rank_bm25 import BM25Okapi
            tokenized = [_tokenize(c) for c in all_chunks]
            bm25_obj  = BM25Okapi(tokenized)
            index_path = os.path.join(store_path, 'bm25_index.pkl')
            with open(index_path, 'wb') as fh:
                pickle.dump({'bm25': bm25_obj, 'chunks': all_chunks}, fh)
            log.info("[BM25] Wrote index for bot %s", business_id)
        except ImportError:
            log.warning("[BM25] rank_bm25 not installed; BM25 index skipped")

        job['progress'] = 100
        job['status']   = 'done'
        job['chunks']   = total
        log.info("[RAG] Job %s complete — %d chunks ingested for bot %s", job_id, total, business_id)

    except Exception as exc:
        log.error("[RAG] Job %s failed: %s", job_id, exc)
        job['status'] = 'error'
        job['error']  = str(exc)

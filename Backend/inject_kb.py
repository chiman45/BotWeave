#!/usr/bin/env python3
"""
inject_kb.py
============
1. Fetches any missing IIIT-NR pages (those not already in iiitnr_scraped.json)
2. Merges them into the scraped JSON
3. Builds text chunks from ALL pages
4. Embeds via local Ollama and writes to the bot's ChromaDB vector store

Usage:
    python inject_kb.py --bot-id business_1775528316422_imqyi6ygs
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup, Comment
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ── Config ────────────────────────────────────────────────────
SCRAPED_JSON    = os.path.join(os.path.dirname(__file__), 'iiitnr_scraped.json')
VECTOR_STORE_ROOT = os.path.join(os.path.dirname(__file__), 'vector_stores')
KB_COLLECTION   = 'knowledge_base'
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL    = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
CHUNK_SIZE      = 1000   # ~150 words — enough context per chunk for factual answers
CHUNK_OVERLAP   = 200    # 20% overlap so facts at chunk boundaries aren't lost
EMBED_WORKERS   = 4

# ── All important IIIT-NR pages to ensure are in the KB ───────
IMPORTANT_URLS = [
    'https://www.iiitnr.ac.in/node/3003',
    'https://www.iiitnr.ac.in/node/1246',
    'https://www.iiitnr.ac.in/content/board',
    'https://www.iiitnr.ac.in/content/yearly-reports',
    'https://www.iiitnr.ac.in/content/btech-curriculum',
    'https://www.iiitnr.ac.in/content/mtech-0',
    'https://www.iiitnr.ac.in/content/phd',
    'https://www.iiitnr.ac.in/content/syllabus',
    'https://www.iiitnr.ac.in/content/academic-calendar-archive',
    'https://www.iiitnr.ac.in/faculty',
    'https://www.iiitnr.ac.in/past-faculty',
    'https://www.iiitnr.ac.in/content/adjunct-faculty',
    'https://www.iiitnr.ac.in/content/emeritus-visits',
    'https://www.iiitnr.ac.in/content/coe-next-generation-network',
    'https://www.iiitnr.ac.in/content/patents',
    'https://www.iiitnr.ac.in/content/lab-details',
    'https://www.iiitnr.ac.in/content/iwatm21',
    'https://www.iiitnr.ac.in/content/ombudsperson-contact-details',
    'https://www.iiitnr.ac.in/content/facilities',
    'https://www.iiitnr.ac.in/content/it-infrastructure',
    'https://www.iiitnr.ac.in/content/library-glance',
    'https://www.iiitnr.ac.in/content/archive-2019',
    'https://www.iiitnr.ac.in/content/anti-ragging-committee',
    'https://www.iiitnr.ac.in/content/outreach-2025',
    'https://www.iiitnr.ac.in/content/vocational-training-programme',
    'https://www.iiitnr.ac.in/content/placement-statistics-2021-25',
    'https://www.iiitnr.ac.in/content/companies-visited-2021-25',
    'https://www.iiitnr.ac.in/content/remuneration-offered-2021-25',
    'https://www.iiitnr.ac.in/content/industry-academia-collaboration-cum-advisory-committee',
    'https://www.iiitnr.ac.in/content/training-and-placement',
    'https://www.iiitnr.ac.in/tenders',
    'https://www.iiitnr.ac.in/content/guest-house-accommodation',
    'https://www.iiitnr.ac.in/content/b-tech-admission-2025',
    'https://www.iiitnr.ac.in/content/mtech-dsai-cmit-fellowship',
    'https://www.iiitnr.ac.in/content/mtech-admission-2025',
    'https://www.iiitnr.ac.in/content/phd-admission-spring-semester-2026',
]

NOISE_TAGS = {'script', 'style', 'noscript', 'iframe', 'form'}
NOISE_SELECTORS = [
    'header', 'nav', 'footer', '#header', '#footer',
    '.main-menu', '.region-navigation', '.breadcrumb',
    '.region-sidebar-first', '.region-sidebar-second',
    '#block-search-form', '.skip-link', '.element-invisible',
]
MAIN_CONTENT_SELECTORS = [
    '#block-system-main', "div[role='main']", 'main',
    '#main-content', '#content', '.region-content', 'article', 'body',
]
FOOTER_MARKERS = ['Contact IIIT', 'Plot No. 7, Sector 24', 'Sitemap Terms', 'Back to Top']


def clean_text(text):
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    for m in FOOTER_MARKERS:
        idx = text.find(m)
        if idx != -1:
            text = text[:idx]
    return text.strip()


def fetch_page(url):
    try:
        resp = requests.get(url, timeout=15, verify=False,
                            headers={'User-Agent': 'Mozilla/5.0 BotSetuCrawler/1.0'})
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code} — {url}")
            return None
        soup = BeautifulSoup(resp.text, 'lxml')
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()
        for tag in soup.find_all(NOISE_TAGS):
            tag.decompose()
        title = soup.find('title')
        title = re.sub(r'\s*\|\s*IIIT NAYA RAIPUR$', '', title.get_text(strip=True), flags=re.I).strip() if title else url
        for sel in NOISE_SELECTORS:
            for e in soup.select(sel):
                e.decompose()
        main = None
        for sel in MAIN_CONTENT_SELECTORS:
            main = soup.select_one(sel)
            if main:
                break
        if not main:
            return None
        for tag in main.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'div']):
            tag.insert_before('\n')
        content = clean_text(main.get_text(separator=' '))
        if len(content) < 80:
            return None
        return {'url': url, 'title': title, 'section': '', 'content': content, 'key_links': []}
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, start = [], 0
    text = text.strip()
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += size - overlap
    return chunks


def get_embedding(text):
    resp = requests.post(
        f'{OLLAMA_BASE_URL}/api/embeddings',
        json={'model': OLLAMA_MODEL, 'prompt': text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['embedding']


def build_chunks_from_pages(pages):
    all_chunks, all_sources = [], []
    for page in pages:
        # Prefix content with URL so the model can cite it
        header = f"[Source: {page['url']}]\n[Title: {page['title']}]\n\n"
        full_text = header + page['content']
        for chunk in chunk_text(full_text):
            if chunk.strip():
                all_chunks.append(chunk)
                all_sources.append(page['url'])
    return all_chunks, all_sources


def embed_all(chunks):
    print(f"Embedding {len(chunks)} chunks via Ollama ({OLLAMA_MODEL})...")
    embeddings = [None] * len(chunks)
    completed = [0]

    def _embed_one(idx, text):
        vec = get_embedding(text)
        return idx, vec

    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as executor:
        futures = {executor.submit(_embed_one, i, c): i for i, c in enumerate(chunks)}
        for future in as_completed(futures):
            idx, vec = future.result()
            embeddings[idx] = vec
            completed[0] += 1
            done = completed[0]
            if done % 100 == 0 or done == len(chunks):
                pct = round(done / len(chunks) * 100)
                print(f"  {done}/{len(chunks)} ({pct}%)")
    return embeddings


def write_to_chromadb(bot_id, chunks, embeddings, sources):
    import chromadb
    store_path = os.path.join(VECTOR_STORE_ROOT, bot_id)
    os.makedirs(store_path, exist_ok=True)
    client = chromadb.PersistentClient(path=store_path)
    try:
        client.delete_collection(KB_COLLECTION)
        print("Deleted existing collection.")
    except Exception:
        pass
    collection = client.create_collection(KB_COLLECTION, metadata={'hnsw:space': 'cosine'})
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{'source': s} for s in sources]
    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    print(f"Done: Written {len(chunks)} chunks to ChromaDB for bot {bot_id}")


def build_bm25_index(bot_id, chunks):
    """
    Build a BM25Okapi index from all chunk texts and save it alongside the vector store.
    Overwrites any existing index for this bot_id.
    Saved as: vector_stores/{bot_id}/bm25_index.pkl
    """
    import pickle
    from rank_bm25 import BM25Okapi

    def _tokenize(text):
        return re.findall(r'\w+', text.lower())

    print(f"Building BM25 index from {len(chunks)} chunks...")
    corpus  = [_tokenize(c) for c in chunks]
    bm25    = BM25Okapi(corpus)
    payload = {'bm25': bm25, 'chunks': chunks}

    store_path = os.path.join(VECTOR_STORE_ROOT, bot_id)
    os.makedirs(store_path, exist_ok=True)
    index_path = os.path.join(store_path, 'bm25_index.pkl')
    with open(index_path, 'wb') as f:
        pickle.dump(payload, f)
    print(f"BM25 index saved to {index_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bot-id', required=True, help='Bot businessId')
    parser.add_argument('--scraped-json', default=SCRAPED_JSON)
    args = parser.parse_args()

    # Load existing scraped data
    print(f"Loading {args.scraped_json}...")
    with open(args.scraped_json, encoding='utf-8') as f:
        pages = json.load(f)
    existing_urls = {p['url'] for p in pages}
    print(f"  {len(pages)} pages already in scraped JSON")

    # Fetch missing important URLs
    missing = [u for u in IMPORTANT_URLS if u not in existing_urls]
    if missing:
        print(f"\nFetching {len(missing)} missing pages...")
        for url in missing:
            print(f"  {url}")
            page = fetch_page(url)
            if page:
                pages.append(page)
                print(f"    OK {page['title']} ({len(page['content'])} chars)")
            else:
                print(f"    SKIP")
            time.sleep(0.5)
        # Save updated JSON
        with open(args.scraped_json, 'w', encoding='utf-8') as f:
            json.dump(pages, f, ensure_ascii=False, indent=2)
        print(f"\nUpdated {args.scraped_json} ({len(pages)} total pages)")
    else:
        print("All important URLs already in scraped JSON.")

    # Filter to only pages with real content
    pages = [p for p in pages if p.get('content') and len(p['content']) > 80]
    print(f"\nBuilding chunks from {len(pages)} pages...")
    chunks, sources = build_chunks_from_pages(pages)
    print(f"  {len(chunks)} chunks total")

    # Embed
    embeddings = embed_all(chunks)

    # Write to ChromaDB
    write_to_chromadb(args.bot_id, chunks, embeddings, sources)

    # Build BM25 index (must run AFTER ChromaDB write succeeds)
    build_bm25_index(args.bot_id, chunks)

    print("\nDone! Knowledge base updated.")


if __name__ == '__main__':
    main()

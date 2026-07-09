"""
routes/ai.py
------------
AI / Knowledge-Base management endpoints.

  GET  /api/ai/models                     -- list available Ollama models
  POST /api/ai/kb/<businessId>            -- upload a KB file (starts embed job)
  GET  /api/ai/kb/<businessId>            -- KB metadata (chunk count)
  DELETE /api/ai/kb/<businessId>          -- delete entire vector store
  GET  /api/ai/kb/progress/<jobId>        -- poll embed job progress
  POST /api/ai/generate-template          -- generate a bot template via LLM
"""

import json
import logging
import re

import requests
from flask import Blueprint, request, jsonify

import config
from services.rag import parse_kb_file, chunk_text, start_embed_job, get_job_status

import os
import shutil

log = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)


# ---------------------------------------------------------------------------
# Model list
# ---------------------------------------------------------------------------

@ai_bp.route('/api/ai/models', methods=['GET'])
def list_ai_models():
    """Return the names of all locally available Ollama models."""
    try:
        resp = requests.get(f'{config.OLLAMA_BASE_URL}/api/tags', timeout=5)
        resp.raise_for_status()
        models = [m['name'] for m in resp.json().get('models', [])]
    except Exception:
        models = [config.OLLAMA_CHAT_MODEL]
    return jsonify({'models': models, 'provider': 'ollama'})


# ---------------------------------------------------------------------------
# Knowledge-base management
# ---------------------------------------------------------------------------

@ai_bp.route('/api/ai/kb/<business_id>', methods=['POST'])
def upload_kb(business_id: str):
    """
    Ingest a KB file (TXT, JSON, CSV, MD) into the bot's ChromaDB vector store.

    Returns a jobId immediately; the embedding job runs in a background thread.
    Poll GET /api/ai/kb/progress/<jobId> for live progress updates.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided (field name must be "file")'}), 400

    file     = request.files['file']
    filename = file.filename or 'kb.txt'
    ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
    raw      = file.read().decode('utf-8', errors='replace')

    texts      = parse_kb_file(raw, ext)
    all_chunks = [c for text in texts for c in chunk_text(text) if c.strip()]

    if not all_chunks:
        return jsonify({'error': 'No usable content found in the uploaded file'}), 400

    job_id = start_embed_job(business_id, filename, all_chunks)
    log.info("[KB] Started embed job %s for bot %s (%d chunks)", job_id, business_id, len(all_chunks))

    return jsonify({
        'jobId':       job_id,
        'totalChunks': len(all_chunks),
        'message':     'Embedding started',
    })


@ai_bp.route('/api/ai/kb/progress/<job_id>', methods=['GET'])
def kb_job_progress(job_id: str):
    """Return the current status / progress of an embed job."""
    job = get_job_status(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@ai_bp.route('/api/ai/kb/<business_id>', methods=['GET'])
def get_kb_info(business_id: str):
    """Return metadata about the bot's vector store (exists + chunk count)."""
    store_path = os.path.join(config.VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        return jsonify({'exists': False, 'chunks': 0})
    try:
        import chromadb
        client     = chromadb.PersistentClient(path=store_path)
        collection = client.get_collection('knowledge_base')
        return jsonify({'exists': True, 'chunks': collection.count()})
    except Exception:
        return jsonify({'exists': True, 'chunks': -1})


@ai_bp.route('/api/ai/kb/<business_id>', methods=['DELETE'])
def delete_kb(business_id: str):
    """Delete the entire vector store for a bot."""
    store_path = os.path.join(config.VECTOR_STORE_ROOT, business_id)
    if os.path.exists(store_path):
        shutil.rmtree(store_path)
        log.info("[KB] Deleted vector store for bot %s", business_id)
    return jsonify({'message': 'Knowledge base deleted'})


# ---------------------------------------------------------------------------
# Template generation
# ---------------------------------------------------------------------------

@ai_bp.route('/api/ai/generate-template', methods=['POST'])
def generate_template():
    """
    Use the local Ollama LLM to generate a custom bot template from a
    natural-language description.

    Body: { "prompt": "I need a hospital appointment booking bot" }
    """
    body        = request.get_json(silent=True) or {}
    user_prompt = (body.get('prompt') or '').strip()

    if not user_prompt:
        return jsonify({'error': 'prompt is required'}), 400

    system = (
        "You are BotWeave, an AI that generates WhatsApp bot templates as structured JSON.\n"
        "Given a description, output ONLY a single valid JSON object with these exact fields:\n"
        "{\n"
        "  \"name\": \"short template name\",\n"
        "  \"icon\": \"single relevant emoji\",\n"
        "  \"useCases\": [\"use case 1\", \"use case 2\"],\n"
        "  \"intelligenceMode\": \"ai\" | \"kb\" | \"workflow\",\n"
        "  \"useCaseType\": \"faq\" | \"leads\" | \"booking\" | \"orders\" | \"custom\",\n"
        "  \"aiModel\": \"llama3\",\n"
        "  \"aiSystemPrompt\": \"system prompt for the AI\",\n"
        "  \"aiRagEnabled\": true | false,\n"
        "  \"welcomeMessage\": \"first message the bot sends\",\n"
        "  \"fallbackMessage\": \"message when bot does not understand\",\n"
        "  \"keywords\": [{\"keyword\": \"...\", \"response\": \"...\"}],\n"
        "  \"flow\": [{\"label\": \"Step Name\", \"type\": \"trigger|message|input|ai|condition|action\"}]\n"
        "}\n"
        "Rules:\n"
        "- Use intelligenceMode=ai for conversational bots, kb for document-based, workflow for rule-based\n"
        "- flow should reflect the logical steps in the bot (3-6 steps)\n"
        "- keywords should contain 3-6 relevant entries\n"
        "- Output ONLY the JSON object. No markdown fences, no explanation."
    )

    try:
        resp = requests.post(
            f'{config.OLLAMA_BASE_URL}/api/chat',
            json={
                'model':    config.OLLAMA_CHAT_MODEL,
                'stream':   False,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user',   'content': f'Generate a bot template for: {user_prompt}'},
                ],
                'options': {'temperature': 0.4},
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()['message']['content'].strip()
    except Exception as exc:
        log.error("[generate-template] Ollama error: %s", exc)
        return jsonify({
            'error': (
                'Ollama is not running or returned an error. '
                'Start it with: ollama serve'
            )
        }), 503

    # Strip markdown code fences that some models add even when told not to.
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$',          '', raw, flags=re.MULTILINE).strip()

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        template = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("[generate-template] JSON parse error: %s | raw=%r", exc, raw[:400])
        return jsonify({
            'error': 'Model did not return valid JSON. Try again or rephrase the description.',
            'raw':   raw[:300],
        }), 422

    template.setdefault('name',             'Custom Bot')
    template.setdefault('icon',             '')
    template.setdefault('useCases',         [])
    template.setdefault('intelligenceMode', 'workflow')
    template.setdefault('useCaseType',      'custom')
    template.setdefault('aiModel',          config.OLLAMA_CHAT_MODEL)
    template.setdefault('aiSystemPrompt',   '')
    template.setdefault('aiRagEnabled',     False)
    template.setdefault('welcomeMessage',   'Hi! How can I help you?')
    template.setdefault('fallbackMessage',  "I didn't understand that. Could you rephrase?")
    template.setdefault('keywords',         [])
    template.setdefault('flow',             [])
    template['generated']      = True
    template['generatedFrom']  = user_prompt

    return jsonify(template)

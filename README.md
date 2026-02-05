# Agentic Ops (Local DevOps AI Agents)

Local-first DevOps AI agents that triage incidents, retrieve runbooks via RAG, and produce safe remediation actions. Includes a deterministic evaluation harness with synthetic incidents.

## Highlights
- Local LLM + local vector store (Ollama + FAISS)
- Multi-agent flow (retrieve → diagnose → safety → scribe)
- Reproducible evaluation with labeled incidents

## Quickstart (Local)
1. Start Ollama and pull models:
   - `ollama serve`
   - `ollama pull llama3.1:8b`
   - `ollama pull nomic-embed-text`

2. Create venv + install:
   - `uv venv`
   - `uv pip install -e .`

3. Ingest the KB into FAISS:
   - `agentic-ops ingest`

4. Run a quick triage:
   - `agentic-ops triage --alert "5xx spike" --logs "connection refused"`

5. Evaluate on synthetic incidents:
   - `python scripts/evaluate.py`

6. Optional API:
   - `agentic-ops serve`
   - `POST http://127.0.0.1:8000/triage`

## Knowledge Base
- `kb/runbooks/` contains custom runbooks (org-specific knowledge).
- `kb/k8s/` contains curated Kubernetes troubleshooting notes.

## Metrics (Sample)
- Root-cause accuracy: 86–92% on synthetic incidents
- MTTR reduction: 35–40% vs baseline (simulated)

## Notes
- If you want deterministic evaluation without LLM, set `LLM_DISABLED=1`.
- Models can be swapped in `src/agentic_ops/config.py`.
- If you hit LangChain warnings on Python 3.14, try Python 3.13 for now.


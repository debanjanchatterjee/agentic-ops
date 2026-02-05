from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parents[2]
    kb_dir: Path = project_root / "kb"
    faiss_dir: Path = project_root / "data" / "faiss"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"
    llm_disabled_env: str = "LLM_DISABLED"
    top_k: int = 4


SETTINGS = Settings()

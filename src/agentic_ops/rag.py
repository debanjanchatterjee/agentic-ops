from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import SETTINGS


def _iter_markdown_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.md"):
        if path.is_file():
            yield path


def load_kb_documents(kb_dir: Path) -> List[Document]:
    docs: List[Document] = []
    for path in _iter_markdown_files(kb_dir):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": str(path)}))
    return docs


def build_vectorstore() -> FAISS:
    kb_dir = SETTINGS.kb_dir
    docs = load_kb_documents(kb_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(
        model=SETTINGS.embed_model,
        base_url=SETTINGS.ollama_base_url,
    )

    vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)
    vectorstore.save_local(str(SETTINGS.faiss_dir))
    return vectorstore


def load_vectorstore() -> FAISS:
    embeddings = OllamaEmbeddings(
        model=SETTINGS.embed_model,
        base_url=SETTINGS.ollama_base_url,
    )
    return FAISS.load_local(
        str(SETTINGS.faiss_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )

"""
文档摄入流水线
读取文件 → 选择分块策略 → Embedding → 写入 ChromaDB
"""
import os
import hashlib
from typing import List
from .splitter import split_code, split_markdown, TextSplitter
from .store import VectorStore, get_vector_store


class IngestPipeline:
    """文档摄入流水线"""

    def __init__(self, store: VectorStore = None):
        self._store = store or get_vector_store()

    def ingest_file(self, file_path: str, collection: str = None) -> int:
        """摄入单个文件 → 返回写入的块数"""
        if not os.path.isfile(file_path):
            return 0
        content = self._read_file(file_path)
        if not content:
            return 0

        ext = os.path.splitext(file_path)[1].lower()
        if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp"}:
            chunks = split_code(content, file_path)
        elif ext in {".md", ".mdx", ".rst"}:
            chunks = split_markdown(content, file_path)
        else:
            splitter = TextSplitter()
            chunks = [
                {"text": c, "metadata": {"source": file_path, "chunk_index": i}}
                for i, c in enumerate(splitter.split(content))
            ]

        if not chunks:
            return 0

        for c in chunks:
            c["metadata"]["content_hash"] = hashlib.md5(c["text"].encode()).hexdigest()

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        self._store.add(texts=texts, metadatas=metadatas, collection=collection)
        return len(texts)

    def ingest_directory(self, dir_path: str, collection: str = None,
                         extensions: List[str] = None,
                         exclude_patterns: List[str] = None) -> int:
        """摄入整个目录 → 返回总块数"""
        exclude_patterns = exclude_patterns or [
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", ".cache", "*.pyc", "*.db", "*.log"
        ]
        extensions = extensions or [
            ".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml",
            ".yml", ".toml", ".env", ".txt"
        ]

        total = 0
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs
                       if not any(p.replace("*", "") in d for p in exclude_patterns)]
            for fname in files:
                if os.path.splitext(fname)[1].lower() not in extensions:
                    continue
                fpath = os.path.join(root, fname)
                if self._is_binary(fpath):
                    continue
                try:
                    total += self.ingest_file(fpath, collection=collection)
                except Exception as e:
                    print(f"[vector_store] ingest failed: {fpath}: {e}")
        return total

    def _read_file(self, path: str) -> str:
        for enc in ["utf-8", "gbk", "latin-1"]:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""

    def _is_binary(self, path: str) -> bool:
        try:
            with open(path, "rb") as f:
                return b"\x00" in f.read(1024)
        except Exception:
            return True

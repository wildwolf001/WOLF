"""
文本分块策略
- split_code: 按函数/类定义边界切分
- split_markdown: 按 ## 标题切分
- TextSplitter: 固定大小 + 重叠
"""
from typing import List
import re


class TextSplitter:
    """通用固定大小分块"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
        return chunks


def split_code(content: str, file_path: str = "") -> List[dict]:
    """按函数/类定义边界切分代码"""
    lines = content.split("\n")
    pattern = re.compile(
        r"^\s*(def |class |async def |function |const |class |export |"
        r"func |pub fn |impl |public |private |protected )"
    )

    boundaries = []
    current_start = 0
    for i, line in enumerate(lines):
        if pattern.match(line) and i - current_start > 5:
            char_pos = len("\n".join(lines[current_start:i]))
            if char_pos > 100:
                boundaries.append((current_start, char_pos))
                current_start = i

    if not boundaries:
        return _split_by_lines(content, file_path)

    chunks = []
    for i, (start, end) in enumerate(boundaries):
        chunk_text = content[start:end]
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "metadata": {"source": file_path, "chunk_index": i,
                             "char_start": start, "char_end": end}
            })
    return chunks


def split_markdown(content: str, file_path: str = "") -> List[dict]:
    """按 ## 标题边界切分 Markdown"""
    sections = re.split(r"\n(?=## )", content)
    chunks = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        title_match = re.match(r"^#{1,4}\s+(.+)", section.strip())
        title = title_match.group(1) if title_match else ""
        chunks.append({
            "text": section.strip(),
            "metadata": {"source": file_path, "chunk_index": i, "section_title": title}
        })
    return chunks


def _split_by_lines(content: str, file_path: str) -> List[dict]:
    """按行数兜底切分"""
    lines = content.split("\n")
    chunks = []
    for i in range(0, len(lines), 45):
        chunk_text = "\n".join(lines[i:i + 50])
        chunks.append({
            "text": chunk_text,
            "metadata": {"source": file_path, "chunk_index": len(chunks),
                         "line_start": i + 1, "line_end": min(i + 50, len(lines))}
        })
    return chunks

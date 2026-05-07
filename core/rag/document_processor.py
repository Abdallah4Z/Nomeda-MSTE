import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

from pypdf import PdfReader
from .config import RAGConfig


@dataclass
class Chunk:
    text: str
    source: str
    page: int
    chunk_id: int
    n_tokens: int = 0

    def to_dict(self) -> dict:
        return {"text": self.text, "source": self.source, "page": self.page, "chunk_id": self.chunk_id}


class DocumentProcessor:
    def __init__(self, config: RAGConfig):
        self.config = config

    def load_pdfs(self, books_dir: Optional[str] = None) -> List[dict]:
        path = Path(books_dir or self.config.books_dir)
        docs = []
        pdf_files = sorted(path.glob("*.pdf"))
        if not pdf_files:
            print(f"[!] No PDFs found in {path}")
            return docs

        for pdf_path in pdf_files:
            print(f"  Loading: {pdf_path.name}")
            try:
                reader = PdfReader(str(pdf_path))
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        docs.append({
                            "text": text.strip(),
                            "source": pdf_path.name,
                            "page": page_num + 1,
                        })
            except Exception as e:
                print(f"  [!] Error loading {pdf_path.name}: {e}")

        print(f"[+] Loaded {len(docs)} pages from {len(pdf_files)} PDF(s)")
        return docs

    def chunk_documents(self, docs: List[dict]) -> List[Chunk]:
        chunks = []
        for doc in docs:
            doc_chunks = self._chunk_document(doc["text"], doc["source"], doc["page"])
            chunks.extend(doc_chunks)
        print(f"[+] Created {len(chunks)} chunks total")
        return chunks

    def _chunk_document(self, text: str, source: str, page: int) -> List[Chunk]:
        separators = self.config.chunk_separators
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        chunks = []
        if len(text) <= chunk_size:
            chunks.append(Chunk(text=text.strip(), source=source, page=page, chunk_id=0,
                                n_tokens=self._estimate_tokens(text)))
            return chunks

        segments = self._recursive_split(text, separators, chunk_size)
        merged = self._merge_segments(segments, chunk_size, overlap)

        for i, seg in enumerate(merged):
            chunks.append(Chunk(text=seg.strip(), source=source, page=page, chunk_id=i,
                                n_tokens=self._estimate_tokens(seg)))
        return chunks

    def _recursive_split(self, text: str, separators: List[str], max_size: int) -> List[str]:
        if len(text) <= max_size or not separators:
            return [text] if text.strip() else []

        sep = separators[0]
        parts = []
        if sep:
            raw = text.split(sep)
        else:
            raw = list(text)

        for part in raw:
            if len(part) > max_size:
                parts.extend(self._recursive_split(part, separators[1:], max_size))
            elif part.strip():
                parts.append(part.strip())
        return parts

    def _merge_segments(self, segments: List[str], max_size: int, overlap: int) -> List[str]:
        merged = []
        current = ""
        for seg in segments:
            if len(current) + len(seg) <= max_size:
                current = (current + " " + seg).strip()
            else:
                if current:
                    merged.append(current)
                current = seg
        if current:
            merged.append(current)

        if len(merged) > 1 and overlap > 0:
            final = [merged[0]]
            for i in range(1, len(merged)):
                prev = merged[i - 1]
                curr = merged[i]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                final.append((overlap_text + " " + curr).strip())
            merged = final

        return merged

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4 + 1

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\S\n]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

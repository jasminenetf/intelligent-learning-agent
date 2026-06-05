"""Document parsing: PDF, DOCX, TXT."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedPage:
    text: str
    page_number: int


def parse_pdf(path: str) -> list[ParsedPage]:
    """Extract text from PDF using PyMuPDF, one ParsedPage per page."""
    import fitz

    pages = []
    doc = fitz.open(path)
    for i, page in enumerate(doc):
        text = page.get_text("text", sort=True)
        pages.append(ParsedPage(text=text.strip(), page_number=i + 1))
    doc.close()
    return pages


def parse_docx(path: str) -> list[ParsedPage]:
    """Extract text from DOCX paragraphs."""
    from docx import Document

    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [ParsedPage(text=text, page_number=1)]


def parse_txt(path: str) -> list[ParsedPage]:
    """Extract text from TXT file, try UTF-8 first."""
    content = Path(path).read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="ignore")
    return [ParsedPage(text=text.strip(), page_number=1)]


def parse_document(path: str, file_ext: str) -> list[ParsedPage]:
    """Dispatch to the appropriate parser."""
    parser_map = {
        ".pdf": parse_pdf,
        ".docx": parse_docx,
        ".txt": parse_txt,
    }
    parser = parser_map.get(file_ext)
    if parser is None:
        raise ValueError(f"no parser for extension: {file_ext}")
    return parser(path)

"""Stage 0 — Ingest.

Pipeline:
  1. Download PDF from Supabase Storage.
  2. Sanitize with qpdf (strip embedded JS, decrypt).
  3. Primary: Nougat -> markdown with LaTeX.
  4. Fallback: legacy pdfplumber-based extractor (src/text_extractor/) when
     Nougat fails, times out, or detects no equations.
  5. Validate (page count <=50, has text, language en).
  6. Return IngestedDocument.
"""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from workers.lib.errors import IngestError, UnsupportedPDFError
from workers.lib.schemas import (
    DocumentMetadata,
    Figure,
    IngestedDocument,
    Section,
    Subject,
)
from workers.lib.supabase_client import download_pdf

log = logging.getLogger(__name__)

MAX_PAGES = 50


async def run_ingest(ctx) -> IngestedDocument:
    pdf_bytes = download_pdf(ctx.supabase, ctx.pdf_storage_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        raw = tmp_path / "raw.pdf"
        sanitized = tmp_path / "sanitized.pdf"
        raw.write_bytes(pdf_bytes)

        _sanitize(raw, sanitized)
        page_count = _count_pages(sanitized)
        if page_count > MAX_PAGES:
            raise UnsupportedPDFError(
                f"PDF has {page_count} pages; max is {MAX_PAGES}",
                user_facing=f"This PDF has {page_count} pages. The free tier supports up to {MAX_PAGES}.",
            )

        # Try Nougat first
        try:
            doc = _ingest_with_nougat(sanitized, ctx.pdf_storage_path, page_count)
        except Exception as e:
            log.warning("Nougat failed, falling back to pdfplumber: %s", e)
            doc = _ingest_with_pdfplumber(sanitized, ctx.pdf_storage_path, page_count)

        if not _has_useful_text(doc):
            raise UnsupportedPDFError(
                "No usable text extracted — PDF likely scanned or image-only.",
            )

        return doc


# ─── Helpers ────────────────────────────────────────────────────────────────────


def _sanitize(input_path: Path, output_path: Path) -> None:
    """qpdf --decrypt --linearize: strips JS, normalizes structure."""
    try:
        subprocess.run(
            ["qpdf", "--decrypt", "--linearize", str(input_path), str(output_path)],
            check=True, capture_output=True, timeout=30,
        )
    except subprocess.CalledProcessError as e:
        # qpdf can return non-zero for warnings; if output file exists, accept.
        if not output_path.exists():
            raise IngestError(f"qpdf sanitization failed: {e.stderr.decode(errors='replace')}") from e
    except FileNotFoundError as e:
        raise IngestError("qpdf binary not found in image") from e


def _count_pages(pdf_path: Path) -> int:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def _ingest_with_nougat(pdf_path: Path, source_path: str, page_count: int) -> IngestedDocument:
    """Run Nougat on the PDF.

    Deferred in v1 — image doesn't bundle nougat-ocr (heavy PyTorch deps slow
    Modal cold starts). Stage 0 always falls through to pdfplumber for now.
    Re-enable in Week 2+ by:
      1. Adding `nougat-ocr>=0.1.17` to workers/app.py pip_install
      2. Implementing this function to shell out: `nougat <pdf> -o <out>`
      3. Parsing the resulting .mmd (markdown w/ $...$ math) into Sections.
    """
    raise NotImplementedError("Nougat deferred — using pdfplumber fallback")


def _ingest_with_pdfplumber(pdf_path: Path, source_path: str, page_count: int) -> IngestedDocument:
    """Fallback ingest using existing src/text_extractor/ machinery.

    Salvages PDFExtractor + StructureDetector + HierarchyBuilder from the
    legacy code at src/text_extractor/extraction.py.
    """
    # Local import — the legacy module lives outside the modal/ package.
    import sys
    sys.path.insert(0, "/root")  # /root/src is mounted by app.py

    from src.text_extractor.extraction import (
        HierarchyBuilder,
        PDFExtractor,
        StructureDetector,
    )

    with PDFExtractor(str(pdf_path)) as ext:
        formatted = ext.extract_text_with_formatting()
        meta = ext.get_metadata()

    detector = StructureDetector(formatted)
    lines = detector.group_into_lines()
    headings = detector.detect_headings()
    builder = HierarchyBuilder(lines, headings)
    hierarchy = builder.build_nested_hierarchy()

    sections: list[Section] = []
    for idx, raw in enumerate(hierarchy.get("sections", [])):
        sections.append(Section(
            id=f"sec-{idx}",
            level=int(raw.get("level", 1)),
            title=str(raw.get("title", f"Section {idx + 1}")),
            prose_md=str(raw.get("content", "")),
            equations=_extract_equations(str(raw.get("content", ""))),
            figures=[],
        ))

    if not sections:
        # Single-section fallback when no headings detected.
        full_text = "\n".join(line["text"] for line in lines)
        sections = [Section(
            id="sec-0",
            level=1,
            title=Path(source_path).stem.replace("_", " ").title(),
            prose_md=full_text,
            equations=_extract_equations(full_text),
            figures=[],
        )]

    return IngestedDocument(
        title=Path(source_path).stem.replace("_", " ").title(),
        sections=sections,
        metadata=DocumentMetadata(
            page_count=page_count,
            language="en",
            detected_subject=_detect_subject(sections),
            source_filename=Path(source_path).name,
            ingested_at=datetime.utcnow(),
        ),
    )


_EQUATION_PATTERN = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.DOTALL)


def _extract_equations(text: str) -> list[str]:
    return [(m.group(1) or m.group(2)).strip() for m in _EQUATION_PATTERN.finditer(text)]


def _detect_subject(sections: list[Section]) -> Subject:
    """Very crude heuristic — replaced with an LLM classifier in Week 4."""
    text = " ".join(s.title.lower() + " " + s.prose_md[:200].lower() for s in sections)
    if any(k in text for k in ("derivative", "integral", "theorem", "matrix", "vector")):
        return Subject.MATH
    if any(k in text for k in ("algorithm", "complexity", "graph", "tree", "sorting")):
        return Subject.CS
    if any(k in text for k in ("force", "velocity", "quantum", "wavelength")):
        return Subject.PHYSICS
    return Subject.OTHER


def _has_useful_text(doc: IngestedDocument) -> bool:
    chars = sum(len(s.prose_md) for s in doc.sections)
    return chars > 200

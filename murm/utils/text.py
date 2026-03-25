"""
murm.utils.text – shared text-extraction helpers.

Both the CLI (murm.cli) and the API graph routes (murm.api.routes.graph)
import from here so the extraction logic lives in a single place.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_path(path: Path) -> str:
    """Return the plain-text content of a file.

    Supported formats
    ---------
    - ``.txt``  – read directly as UTF-8
    - ``.pdf``  – extracted via *pypdf* (optional dependency)
    - ``.docx`` / ``.doc`` – extracted via *python-docx* (optional dependency)

    Any other format returns an empty string and logs a warning.
    """
    suffix = path.suffix.lower()
    try:
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".pdf":
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix in (".docx", ".doc"):
            import docx
            doc = docx.Document(str(path))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as exc:
        logger.warning("Text extraction failed for %s: %s", path.name, exc)
        return ""

    logger.warning("Unsupported file type for text extraction: %s", suffix)
    return ""

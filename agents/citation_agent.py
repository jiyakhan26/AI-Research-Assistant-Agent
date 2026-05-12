"""
Citation Extraction Agent - Extracts and parses references from PDF files.
Uses PyMuPDF for text extraction and regex patterns for reference parsing.
"""

import re
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        raise ValueError(f"Could not read PDF: {str(e)}")
    return text


def find_references_section(text: str) -> str:
    """
    Locate the References/Bibliography section in extracted text.
    Agent heuristic: look for common section headers.
    """
    patterns = [
        r'(?i)\n\s*references\s*\n',
        r'(?i)\n\s*bibliography\s*\n',
        r'(?i)\n\s*works cited\s*\n',
        r'(?i)\n\s*literature cited\s*\n',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return text[match.start():]

    # Fallback: last 30% of the document likely contains references
    cutoff = int(len(text) * 0.70)
    return text[cutoff:]


def split_into_references(ref_section: str) -> list:
    """
    Split the references section into individual reference strings.
    Uses numbered references [1], (1), or line-break heuristics.
    """
    # Try numbered pattern [1], [2], ...
    numbered = re.split(r'\n\s*\[\d+\]', ref_section)
    if len(numbered) > 3:
        return [r.strip() for r in numbered if len(r.strip()) > 20]

    # Try numbered pattern 1. 2. 3.
    numbered2 = re.split(r'\n\s*\d+\.\s+', ref_section)
    if len(numbered2) > 3:
        return [r.strip() for r in numbered2 if len(r.strip()) > 20]

    # Fallback: split on blank lines
    by_blank = [r.strip() for r in re.split(r'\n\s*\n', ref_section) if len(r.strip()) > 30]
    return by_blank


def parse_single_reference(ref_text: str) -> dict:
    """
    Parse a raw reference string into structured fields.
    Uses regex heuristics to identify authors, year, title, journal.
    """
    result = {
        'raw_text': ref_text.strip(),
        'authors': '',
        'title': '',
        'year': '',
        'journal': ''
    }

    # Extract year (4-digit number between 1900-2099)
    year_match = re.search(r'\b(19|20)\d{2}\b', ref_text)
    if year_match:
        result['year'] = year_match.group()

    # Extract title: text in quotes or after year
    title_match = re.search(r'"([^"]{10,200})"', ref_text)
    if title_match:
        result['title'] = title_match.group(1)
    else:
        # Try to find title as the longest capitalized phrase
        parts = ref_text.split('.')
        for part in parts:
            if len(part.strip()) > 20 and part.strip()[0].isupper():
                result['title'] = part.strip()
                break

    # Extract authors: text before the year (first ~100 chars)
    if year_match:
        before_year = ref_text[:year_match.start()].strip().rstrip(',').rstrip('(')
        result['authors'] = before_year[:150]

    # Extract journal: often italicized or comes after title
    journal_match = re.search(
        r'(?:In|Journal of|Proceedings of|Conference on)\s+([A-Z][^,\.]{5,80})',
        ref_text, re.IGNORECASE
    )
    if journal_match:
        result['journal'] = journal_match.group(0)[:120]

    return result


def extract_citations_from_pdf(pdf_path: str) -> list:
    """
    Main agent function: extracts and parses all citations from a PDF.
    Returns a list of parsed citation dicts.
    """
    text = extract_text_from_pdf(pdf_path)
    ref_section = find_references_section(text)
    raw_refs = split_into_references(ref_section)

    parsed = []
    for raw in raw_refs[:50]:  # Cap at 50 references
        if len(raw) > 15:
            parsed.append(parse_single_reference(raw))

    return parsed


def extract_citations_from_text(text: str) -> list:
    """Extract citations from pasted text (no PDF)."""
    ref_section = find_references_section(text)
    raw_refs = split_into_references(ref_section)
    parsed = []
    for raw in raw_refs[:50]:
        if len(raw) > 15:
            parsed.append(parse_single_reference(raw))
    return parsed
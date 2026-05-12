"""
Related Work Agent - Extracts text from uploaded PDF and finds related research papers.
Primary source: OpenAlex (mirrors search agent). Fallback: Semantic Scholar.
"""

import re
import fitz  # PyMuPDF
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
import math
from datetime import datetime


OPENALEX_BASE = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

HEADERS = {
    "User-Agent": "AI-Research-Assistant/1.0 (mailto:research@example.com)"
}


# ─────────────────────────────────────────────
# PDF EXTRACTION
# ─────────────────────────────────────────────

def extract_text_from_pdf(filepath: str) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def extract_title_and_abstract(text: str) -> dict:
    """Try to extract title and abstract from paper text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    title = lines[0] if lines else "Unknown Title"

    abstract = ""
    text_lower = text.lower()
    abs_idx = text_lower.find('abstract')
    if abs_idx != -1:
        intro_idx = text_lower.find('introduction', abs_idx)
        if intro_idx != -1:
            abstract = text[abs_idx + 8:intro_idx].strip()
        else:
            abstract = text[abs_idx + 8:abs_idx + 1500].strip()

    return {
        'title': title[:200],
        'abstract': abstract[:500] if abstract else text[:500]
    }


def extract_keywords(text: str, top_n: int = 10) -> list:
    """Extract top keywords from text using TF-IDF."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text.lower())

    sentences = [s.strip() for s in text.split('.') if len(s.strip().split()) > 3]
    if not sentences:
        sentences = [text]

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=200,
            min_df=1
        )
        tfidf_matrix = vectorizer.fit_transform(sentences)
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1
        top_indices = scores.argsort()[::-1][:top_n]
        return [feature_names[i] for i in top_indices]
    except Exception:
        words = text.split()
        freq = {}
        for w in words:
            if len(w) > 4:
                freq[w] = freq.get(w, 0) + 1
        return sorted(freq, key=freq.get, reverse=True)[:top_n]


# ─────────────────────────────────────────────
# SCORING (same logic as search_agent)
# ─────────────────────────────────────────────

def compute_score(paper: dict) -> dict:
    current_year = datetime.now().year

    raw_relevance = paper.get('_raw_relevance', 0) or 0
    relevance_pts = min(raw_relevance / 50, 1.0) * 40

    citations = paper.get('citation_count', 0) or 0
    citation_pts = min(math.log10(citations + 1) / math.log10(5001), 1.0) * 35 if citations > 0 else 0

    year = paper.get('year', 0) or 0
    age = max(current_year - year, 0) if year else 10
    recency_pts = max(0, 15 - age * 1.5)

    pdf_pts = 5 if paper.get('pdf_url') else 0

    abstract = paper.get('abstract', '') or ''
    abstract_pts = 5 if len(abstract) > 80 else (2 if abstract else 0)

    score = min(round(relevance_pts + citation_pts + recency_pts + pdf_pts + abstract_pts), 100)

    if score >= 75:
        level, label = 'top',  'Highly Recommended'
    elif score >= 50:
        level, label = 'good', 'Good Match'
    elif score >= 30:
        level, label = 'fair', 'Fair Match'
    else:
        level, label = 'low',  'Low Relevance'

    paper['score'] = score
    paper['recommendation_level'] = level
    paper['recommendation_label'] = label
    paper.pop('_raw_relevance', None)
    return paper


# ─────────────────────────────────────────────
# OPENALEX (PRIMARY)
# ─────────────────────────────────────────────

def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ''
    try:
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        text = ' '.join(w for _, w in word_positions)
        return text[:600] + '...' if len(text) > 600 else text
    except Exception:
        return ''


def search_openalex_related(query: str, max_results: int = 10) -> list:
    """Search OpenAlex for related papers — primary source."""
    params = {
        'search': query,
        'per-page': max_results,
        'select': (
            'id,title,authorships,abstract_inverted_index,'
            'publication_year,cited_by_count,primary_location,'
            'open_access,concepts,relevance_score,doi'
        ),
        'sort': 'relevance_score:desc',
    }
    try:
        r = requests.get(OPENALEX_BASE, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    papers = []
    for item in data.get('results', []):
        try:
            title = item.get('title') or 'Untitled'

            authorships = item.get('authorships', [])
            author_names = [
                a.get('author', {}).get('display_name', '')
                for a in authorships[:3]
                if a.get('author', {}).get('display_name')
            ]
            author_str = ', '.join(author_names)
            if len(authorships) > 3:
                author_str += ' et al.'

            abstract = _reconstruct_abstract(item.get('abstract_inverted_index'))

            doi = item.get('doi') or ''
            oa = item.get('open_access', {})
            pdf_url = oa.get('oa_url') or ''
            location = item.get('primary_location') or {}
            landing = location.get('landing_page_url') or ''
            url = landing or (f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else '')

            source_info = location.get('source') or {}
            venue = source_info.get('display_name', '')

            concepts = [
                c.get('display_name', '')
                for c in (item.get('concepts') or [])[:5]
                if c.get('score', 0) > 0.3
            ]

            papers.append({
                'title': title,
                'authors': author_str or 'Unknown authors',
                'abstract': abstract,
                'year': item.get('publication_year') or 0,
                'source': 'OpenAlex',
                'source_badge': 'openalex',
                'url': url,
                'pdf_url': pdf_url,
                'citation_count': item.get('cited_by_count') or 0,
                'venue': venue,
                'concepts': concepts,
                'is_open_access': oa.get('is_oa', False),
                '_raw_relevance': item.get('relevance_score') or 0,
            })
        except Exception:
            continue

    return papers


# ─────────────────────────────────────────────
# SEMANTIC SCHOLAR (FALLBACK)
# ─────────────────────────────────────────────

def search_semantic_related(query: str, max_results: int = 8) -> list:
    """Search Semantic Scholar for related papers — fallback/enrichment."""
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,authors,abstract,year,citationCount,url,openAccessPdf'
    }
    try:
        r = requests.get(SEMANTIC_SCHOLAR_BASE, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    papers = []
    for item in data.get('data', []):
        try:
            authors_list = [a.get('name', '') for a in item.get('authors', [])]
            author_str = ', '.join(authors_list[:3])
            if len(authors_list) > 3:
                author_str += ' et al.'
            abstract = item.get('abstract') or ''
            oa_pdf = item.get('openAccessPdf') or {}
            papers.append({
                'title': item.get('title', 'Unknown Title'),
                'authors': author_str or 'Unknown authors',
                'abstract': abstract[:600] + '...' if len(abstract) > 600 else abstract,
                'year': item.get('year') or 0,
                'source': 'Semantic Scholar',
                'source_badge': 'semantic',
                'url': item.get('url', ''),
                'pdf_url': oa_pdf.get('url', ''),
                'citation_count': item.get('citationCount') or 0,
                'venue': '',
                'concepts': [],
                'is_open_access': bool(oa_pdf.get('url')),
                '_raw_relevance': 0,
            })
        except Exception:
            continue

    return papers


# ─────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────

def deduplicate(papers: list) -> list:
    seen = {}
    for paper in papers:
        key = re.sub(r'\W+', '', (paper.get('title') or '').lower())[:60]
        if key not in seen:
            seen[key] = paper
        elif paper.get('citation_count', 0) > seen[key].get('citation_count', 0):
            seen[key] = paper
    return list(seen.values())


# ─────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────

def find_related_work(filepath: str) -> dict:
    """
    Main agent function:
    1. Extract full text from PDF
    2. Extract keywords using TF-IDF
    3. Search OpenAlex (primary) + Semantic Scholar (fallback)
    4. Deduplicate, score, and rank results
    """
    # Step 1: Extract text
    full_text = extract_text_from_pdf(filepath)
    if not full_text:
        return {'error': 'Could not extract text from PDF'}

    # Step 2: Get title/abstract
    meta = extract_title_and_abstract(full_text)

    # Step 3: Extract keywords
    keywords = extract_keywords(full_text, top_n=8)
    query = ' '.join(keywords[:6])

    # Step 4: Search — OpenAlex primary, Semantic Scholar fallback
    openalex_results  = search_openalex_related(query, max_results=10)
    semantic_results  = search_semantic_related(query, max_results=8) if len(openalex_results) < 5 else []

    # Step 5: Merge, deduplicate, score
    all_results = deduplicate(openalex_results + semantic_results)
    scored = [compute_score(p) for p in all_results]
    scored.sort(key=lambda p: p['score'], reverse=True)

    return {
        'extracted_title':    meta['title'],
        'extracted_abstract': meta['abstract'],
        'keywords_used':      keywords,
        'query_used':         query,
        'papers':             scored[:15],
        'total_found':        len(scored)
    }
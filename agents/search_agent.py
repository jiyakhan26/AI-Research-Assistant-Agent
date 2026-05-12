"""
Search Agent - AI Research Assistant
Primary: OpenAlex API (250M+ works, built-in relevance scores, no key needed)
Fallback: Semantic Scholar (citation data enrichment)
No more manual API selection — the agent decides automatically.
"""

import requests
import math
from datetime import datetime

OPENALEX_BASE = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

HEADERS = {
    "User-Agent": "AI-Research-Assistant/1.0 (mailto:research@example.com)"
}


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def compute_score(paper: dict) -> dict:
    """
    Compute a 0–100 relevance + quality score.
    Factors:
      - OpenAlex relevance_score  (up to 40 pts)
      - Citation count            (up to 35 pts, log-scaled)
      - Recency                   (up to 15 pts)
      - Open Access PDF available (up to 5 pts)
      - Has abstract              (up to 5 pts)
    Returns paper dict with 'score', 'score_breakdown', 'recommendation_level' added.
    """
    current_year = datetime.now().year

    # 1. Relevance (from OpenAlex, already normalised 0–1 approx)
    raw_relevance = paper.get('_raw_relevance', 0) or 0
    relevance_pts = min(raw_relevance / 50, 1.0) * 40  # scale to 40

    # 2. Citations (log scale so 1 citation != 0 pts)
    citations = paper.get('citation_count', 0) or 0
    if citations > 0:
        citation_pts = min(math.log10(citations + 1) / math.log10(5001), 1.0) * 35
    else:
        citation_pts = 0

    # 3. Recency (papers from last 2 years get full points, older decay)
    year = paper.get('year', 0) or 0
    age = max(current_year - year, 0) if year else 10
    recency_pts = max(0, 15 - age * 1.5)

    # 4. Open access PDF
    pdf_pts = 5 if paper.get('pdf_url') else 0

    # 5. Abstract quality
    abstract = paper.get('abstract', '') or ''
    abstract_pts = 5 if len(abstract) > 80 else (2 if abstract else 0)

    total = relevance_pts + citation_pts + recency_pts + pdf_pts + abstract_pts
    score = min(round(total), 100)

    # Recommendation level
    if score >= 75:
        level = 'top'
        label = 'Highly Recommended'
    elif score >= 50:
        level = 'good'
        label = 'Good Match'
    elif score >= 30:
        level = 'fair'
        label = 'Fair Match'
    else:
        level = 'low'
        label = 'Low Relevance'

    paper['score'] = score
    paper['recommendation_level'] = level
    paper['recommendation_label'] = label
    paper['score_breakdown'] = {
        'relevance': round(relevance_pts),
        'citations': round(citation_pts),
        'recency': round(recency_pts),
        'open_access': round(pdf_pts),
        'abstract': round(abstract_pts),
    }
    return paper


# ─────────────────────────────────────────────
# OPENALEX (PRIMARY)
# ─────────────────────────────────────────────

def search_openalex(query: str, max_results: int = 15) -> list:
    """
    Search OpenAlex — primary source.
    Returns structured paper dicts with relevance scores.
    """
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
        response = requests.get(OPENALEX_BASE, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []

    papers = []
    for item in data.get('results', []):
        try:
            title = item.get('title') or 'Untitled'

            # Authors
            authorships = item.get('authorships', [])
            author_names = [
                a.get('author', {}).get('display_name', '')
                for a in authorships[:3]
                if a.get('author', {}).get('display_name')
            ]
            author_str = ', '.join(author_names)
            if len(authorships) > 3:
                author_str += ' et al.'

            # Abstract (OpenAlex stores as inverted index — reconstruct)
            abstract = _reconstruct_abstract(item.get('abstract_inverted_index'))

            # URLs
            doi = item.get('doi') or ''
            oa = item.get('open_access', {})
            pdf_url = oa.get('oa_url') or ''
            location = item.get('primary_location') or {}
            landing = location.get('landing_page_url') or ''
            url = landing or (f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else '')

            # Source journal/venue
            source_info = location.get('source') or {}
            venue = source_info.get('display_name', '')

            # Concepts/topics
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
                'paper_id': item.get('id', '').replace('https://openalex.org/', ''),
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


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
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


# ─────────────────────────────────────────────
# SEMANTIC SCHOLAR (ENRICHMENT / FALLBACK)
# ─────────────────────────────────────────────

def search_semantic_scholar(query: str, max_results: int = 8) -> list:
    """
    Semantic Scholar — used as fallback/enrichment.
    Good for citation counts and extra coverage.
    """
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,authors,abstract,year,citationCount,externalIds,url,openAccessPdf'
    }

    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_BASE, params=params,
            headers={'Accept': 'application/json'}, timeout=15
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
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
                'paper_id': item.get('paperId', ''),
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
    """
    Remove duplicate papers by matching normalised titles.
    When duplicates exist, keep the one with higher citation count.
    """
    seen = {}
    for paper in papers:
        key = _normalise_title(paper.get('title', ''))
        if key not in seen:
            seen[key] = paper
        else:
            # Keep whichever has more citations
            if paper.get('citation_count', 0) > seen[key].get('citation_count', 0):
                # Merge: prefer OpenAlex metadata but take higher citation count
                seen[key] = paper
    return list(seen.values())


def _normalise_title(title: str) -> str:
    import re
    return re.sub(r'\W+', '', title.lower())[:60]


# ─────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────

def search_papers(query: str, source: str = 'auto', max_results: int = 10) -> list:
    """
    Main agent function.
    'source' param is accepted for backward compat but IGNORED —
    the agent always queries OpenAlex first, Semantic Scholar as fallback,
    then deduplicates and scores everything automatically.
    """
    if not query or not query.strip():
        return []

    # Step 1: Primary — OpenAlex
    openalex_results = search_openalex(query, max_results=max(max_results, 12))

    # Step 2: If OpenAlex returns < 5 results, enrich with Semantic Scholar
    ss_results = []
    if len(openalex_results) < 5:
        ss_results = search_semantic_scholar(query, max_results=max_results)

    # Step 3: Merge & deduplicate
    all_results = openalex_results + ss_results
    unique = deduplicate(all_results)

    # Step 4: Score every paper
    scored = [compute_score(p) for p in unique]

    # Step 5: Sort by score descending
    scored.sort(key=lambda p: p['score'], reverse=True)

    # Step 6: Clean internal fields before returning
    for p in scored:
        p.pop('_raw_relevance', None)

    return scored[:max_results]


# ─────────────────────────────────────────────
# RELATED PAPERS
# ─────────────────────────────────────────────

def get_related_papers(title: str, abstract: str = '', max_results: int = 6) -> list:
    """
    Find related papers using the title + first words of abstract as query.
    Returns scored results.
    """
    keywords = ' '.join(title.split()[:6])
    if abstract:
        # Pull a few key words from abstract too
        keywords += ' ' + ' '.join(abstract.split()[:10])
    return search_papers(keywords, max_results=max_results)
"""
Plagiarism Detection Agent - Enhanced multi-source checking.
Now includes OpenAlex as a primary corpus source (mirrors the search agent).
"""

import difflib
import re
import requests
import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


HEADERS = {
    "User-Agent": "AI-Research-Assistant/1.0 (mailto:research@example.com)"
}


def preprocess_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text.strip()


# ─────────────────────────────────────────────
# SOURCES
# ─────────────────────────────────────────────

def fetch_openalex(query: str, max_results: int = 10) -> list:
    """
    Fetch abstracts from OpenAlex — mirrors the primary search agent source.
    This ensures papers found via search are also matched in plagiarism checks.
    """
    try:
        params = {
            'search': query,
            'per-page': max_results,
            'select': 'title,abstract_inverted_index,primary_location,doi,id',
        }
        r = requests.get(
            'https://api.openalex.org/works',
            params=params, headers=HEADERS, timeout=12
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get('results', []):
            title = item.get('title') or 'OpenAlex Paper'
            abstract = _reconstruct_abstract(item.get('abstract_inverted_index'))
            if not abstract or len(abstract.split()) < 15:
                continue

            doi = item.get('doi') or ''
            location = item.get('primary_location') or {}
            landing = location.get('landing_page_url') or ''
            url = landing or (f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else
                              item.get('id', 'https://openalex.org'))

            results.append({
                'text': abstract,
                'source_name': title,
                'url': url
            })
        return results
    except Exception:
        return []


def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ''
    try:
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return ' '.join(w for _, w in word_positions)
    except Exception:
        return ''


def fetch_arxiv(query: str, max_results: int = 6) -> list:
    """Fetch abstracts from arXiv."""
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results={max_results}"
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        results = []
        for entry in root.findall('atom:entry', ns):
            summary = entry.find('atom:summary', ns)
            title   = entry.find('atom:title', ns)
            link    = entry.find('atom:id', ns)
            if summary is not None and summary.text and len(summary.text.split()) > 15:
                results.append({
                    'text': summary.text.strip(),
                    'source_name': title.text.strip() if title is not None else 'arXiv Paper',
                    'url': link.text.strip() if link is not None else 'https://arxiv.org'
                })
        return results
    except Exception:
        return []


def fetch_semantic_scholar(query: str, max_results: int = 5) -> list:
    """Fetch abstracts from Semantic Scholar."""
    try:
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,abstract,url'
        }
        r = requests.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params=params, timeout=10
        )
        data = r.json()
        results = []
        for paper in data.get('data', []):
            abstract = paper.get('abstract')
            if abstract and len(abstract.split()) > 15:
                results.append({
                    'text': abstract.strip(),
                    'source_name': paper.get('title', 'Semantic Scholar Paper'),
                    'url': paper.get('url', 'https://semanticscholar.org')
                })
        return results
    except Exception:
        return []


def fetch_wikipedia(query: str) -> list:
    try:
        headers = {'User-Agent': 'ResearchAgent/1.0 (Student CEP Project; contact@example.com)'}
        url = "https://en.wikipedia.org/w/api.php"
        params = {'action': 'query', 'list': 'search', 'srsearch': query, 'srlimit': 3, 'format': 'json'}
        r = requests.get(url, params=params, timeout=10, headers=headers)
        search_results = r.json().get('query', {}).get('search', [])
        results = []
        for item in search_results:
            extract_params = {
                'action': 'query', 'pageids': item['pageid'],
                'prop': 'extracts', 'exintro': True, 'explaintext': True, 'format': 'json'
            }
            er = requests.get(url, params=extract_params, timeout=10, headers=headers)
            pages = er.json().get('query', {}).get('pages', {})
            for page in pages.values():
                extract = page.get('extract', '')
                if extract and len(extract.split()) > 20:
                    results.append({
                        'text': extract[:1000],
                        'source_name': page.get('title', 'Wikipedia'),
                        'url': f"https://en.wikipedia.org/wiki/{page.get('title','').replace(' ','_')}"
                    })
        return results
    except Exception:
        return []


def fetch_crossref(query: str, max_results: int = 5) -> list:
    """Fetch paper abstracts from CrossRef."""
    try:
        params = {'query': query, 'rows': max_results, 'select': 'title,abstract,URL'}
        r = requests.get('https://api.crossref.org/works', params=params, timeout=10)
        items = r.json().get('message', {}).get('items', [])
        results = []
        for item in items:
            abstract = re.sub(r'<[^>]+>', '', item.get('abstract', '')).strip()
            if abstract and len(abstract.split()) > 15:
                title = item.get('title', ['CrossRef Paper'])
                results.append({
                    'text': abstract,
                    'source_name': title[0] if title else 'CrossRef Paper',
                    'url': item.get('URL', 'https://crossref.org')
                })
        return results
    except Exception:
        return []


# ─────────────────────────────────────────────
# MATCHING
# ─────────────────────────────────────────────

def get_matching_blocks(text1: str, text2: str) -> list:
    words1 = text1.lower().split()
    words2 = text2.lower().split()
    matcher = difflib.SequenceMatcher(None, words1, words2)
    blocks = []
    for block in matcher.get_matching_blocks():
        if block.size >= 5:
            matched = ' '.join(words1[block.a:block.a + block.size])
            blocks.append(matched)
    return blocks[:10]


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def check_plagiarism(input_text: str) -> dict:
    """
    Main plagiarism check against multiple real sources.
    OpenAlex is queried first as it mirrors the search agent's primary source.
    """
    # Use first 8 keywords for corpus search
    keywords = ' '.join(input_text.split()[:8])

    # Fetch from all sources — OpenAlex first so its papers rank highest
    all_sources = []
    all_sources.extend(fetch_openalex(keywords, max_results=10))      # PRIMARY — same as search
    all_sources.extend(fetch_arxiv(keywords, max_results=6))
    all_sources.extend(fetch_semantic_scholar(keywords, max_results=5))
    all_sources.extend(fetch_wikipedia(keywords))
    all_sources.extend(fetch_crossref(keywords, max_results=5))

    if not all_sources:
        return {
            'overall_score': 0,
            'risk_level': 'Low',
            'risk_class': 'success',
            'word_count': len(input_text.split()),
            'top_matches': [],
            'matching_phrases': [],
            'sources_checked': 0,
            'input_preview': input_text[:200]
        }

    corpus_texts = [s['text'] for s in all_sources]
    processed_input  = preprocess_text(input_text)
    processed_corpus = [preprocess_text(t) for t in corpus_texts]

    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', min_df=1)
        tfidf_matrix = vectorizer.fit_transform([processed_input] + processed_corpus)
        similarities = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1:])[0]
    except Exception:
        similarities = [0.0] * len(corpus_texts)

    # Build scored results
    scored = []
    for i, score in enumerate(similarities):
        scored.append({
            'score':      float(score),
            'percentage': round(float(score) * 100, 2),
            'source':     all_sources[i]['source_name'],
            'url':        all_sources[i]['url'],
            'snippet':    all_sources[i]['text'][:200] + '...'
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    max_score = scored[0]['score'] if scored else 0.0

    # Matching phrases from top result
    top_idx = int(similarities.argmax()) if len(similarities) > 0 else 0
    matching_phrases = get_matching_blocks(input_text, corpus_texts[top_idx]) if corpus_texts else []

    if max_score >= 0.7:
        risk, risk_class = 'High',   'danger'
    elif max_score >= 0.4:
        risk, risk_class = 'Medium', 'warning'
    else:
        risk, risk_class = 'Low',    'success'

    return {
        'overall_score':    round(max_score * 100, 2),
        'risk_level':       risk,
        'risk_class':       risk_class,
        'word_count':       len(input_text.split()),
        'top_matches':      scored[:5],
        'matching_phrases': matching_phrases,
        'sources_checked':  len(all_sources),
        'input_preview':    input_text[:200] + '...' if len(input_text) > 200 else input_text
    }
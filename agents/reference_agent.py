"""
Reference Formatting Agent - Converts raw citation data into APA and IEEE formats.
Agent autonomously parses incomplete data and fills in best-effort formatting.
"""

import re


def clean_authors(authors_str: str) -> list:
    """Split author string into list of individual author names."""
    if not authors_str:
        return []
    # Split by common delimiters
    authors = re.split(r'[,;](?!\s*Jr)', authors_str)
    cleaned = []
    for a in authors:
        a = a.strip().strip('.')
        if len(a) > 2 and a not in ['et al', 'and']:
            cleaned.append(a)
    return cleaned[:6]  # APA limits to 6 then et al.


def format_apa(authors: str, year: str, title: str, journal: str = '', url: str = '') -> str:
    """
    Format citation in APA 7th edition style.
    Author, A. A., & Author, B. B. (Year). Title of article. Journal Name. URL
    """
    author_list = clean_authors(authors)

    # Format authors: Last, F. M.
    formatted_authors = []
    for author in author_list:
        parts = author.strip().split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = '. '.join([p[0] for p in parts[:-1] if p]) + '.'
            formatted_authors.append(f"{last}, {initials}")
        else:
            formatted_authors.append(author)

    if len(formatted_authors) > 6:
        author_str = ', '.join(formatted_authors[:6]) + ', ... ' + formatted_authors[-1]
    elif len(formatted_authors) == 1:
        author_str = formatted_authors[0]
    elif formatted_authors:
        author_str = ', '.join(formatted_authors[:-1]) + ', & ' + formatted_authors[-1]
    else:
        author_str = 'Unknown Author'

    year_str = f"({year})" if year else '(n.d.)'
    title_str = title.strip() if title else 'Untitled'
    journal_str = f"*{journal.strip()}*. " if journal else ''
    url_str = f"{url}" if url else ''

    apa = f"{author_str} {year_str}. {title_str}. {journal_str}{url_str}"
    return apa.strip()


def format_ieee(authors: str, title: str, journal: str = '', year: str = '', url: str = '', index: int = 1) -> str:
    """
    Format citation in IEEE style.
    [N] A. Author, "Title," Journal, year. [Online]. URL
    """
    author_list = clean_authors(authors)

    # IEEE: F. M. Last
    formatted_authors = []
    for author in author_list:
        parts = author.strip().split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = '. '.join([p[0] for p in parts[:-1] if p]) + '.'
            formatted_authors.append(f"{initials} {last}")
        else:
            formatted_authors.append(author)

    if len(formatted_authors) > 3:
        author_str = formatted_authors[0] + ' et al.'
    elif formatted_authors:
        author_str = ', '.join(formatted_authors)
    else:
        author_str = 'Unknown'

    title_str = f'"{title.strip()}"' if title else '"Untitled"'
    journal_str = f" *{journal.strip()}*," if journal else ''
    year_str = f" {year}." if year else ''
    url_str = f" [Online]. Available: {url}" if url else ''

    ieee = f"[{index}] {author_str}, {title_str},{journal_str}{year_str}{url_str}"
    return ieee.strip()


def format_mla(authors: str, title: str, journal: str = '', year: str = '', url: str = '') -> str:
    """
    Format citation in MLA 9th edition style.
    Last, First. "Title." Journal, Year, URL.
    """
    author_list = clean_authors(authors)
    if author_list:
        first_author = author_list[0]
        parts = first_author.strip().split()
        if len(parts) >= 2:
            mla_author = f"{parts[-1]}, {' '.join(parts[:-1])}"
        else:
            mla_author = first_author
        if len(author_list) > 1:
            mla_author += ', et al.'
    else:
        mla_author = 'Unknown Author'

    title_str = f'"{title.strip()}"' if title else '"Untitled"'
    journal_str = f" *{journal.strip()}*," if journal else ''
    year_str = f" {year}," if year else ''
    url_str = f" {url}." if url else '.'

    mla = f"{mla_author}. {title_str}.{journal_str}{year_str}{url_str}"
    return mla.strip()


def format_citation(raw_data: dict, style: str = 'apa', index: int = 1) -> str:
    """
    Main agent function: formats a citation dict into the requested style.
    """
    authors = raw_data.get('authors', '')
    title = raw_data.get('title', '')
    year = raw_data.get('year', '')
    journal = raw_data.get('journal', '')
    url = raw_data.get('url', '')

    if style == 'apa':
        return format_apa(authors, year, title, journal, url)
    elif style == 'ieee':
        return format_ieee(authors, title, journal, year, url, index)
    elif style == 'mla':
        return format_mla(authors, title, journal, year, url)
    else:
        return format_apa(authors, year, title, journal, url)


def batch_format(citations: list, style: str = 'apa') -> list:
    """Format a list of citations in the given style."""
    formatted = []
    for i, citation in enumerate(citations, start=1):
        formatted.append({
            'original': citation,
            'formatted': format_citation(citation, style, index=i)
        })
    return formatted
from flask import Blueprint, render_template, request, jsonify
from agents.search_agent import search_papers, get_related_papers
from extensions import db
from models import Paper, SearchHistory

search_bp = Blueprint('search', __name__)

# Columns that actually exist in the Paper model
PAPER_DB_FIELDS = {'title', 'authors', 'year', 'source', 'paper_id', 'url', 'pdf_url', 'citation_count'}


@search_bp.route('/')
def search_page():
    return render_template('search.html')


@search_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    query_str = data.get('query', '').strip()
    source = data.get('source', 'auto')
    max_results = int(data.get('max_results', 10))

    if not query_str:
        return jsonify({'error': 'Query cannot be empty'}), 400

    history = SearchHistory(query=query_str, source=source)
    db.session.add(history)

    try:
        results = search_papers(query_str, source=source, max_results=max_results)

        # Save to DB — only pass fields the model knows about
        for paper_data in results[:5]:
            if not paper_data.get('paper_id'):
                continue
            exists = db.session.execute(
                db.select(Paper).filter_by(paper_id=paper_data['paper_id'])
            ).scalar_one_or_none()
            if not exists:
                clean = {k: v for k, v in paper_data.items() if k in PAPER_DB_FIELDS}
                db.session.add(Paper(**clean))

        history.results_count = len(results)
        db.session.commit()
        return jsonify({'papers': results, 'count': len(results)})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@search_bp.route('/related', methods=['POST'])
def related():
    data = request.get_json()
    title = data.get('title', '')
    abstract = data.get('abstract', '')
    papers = get_related_papers(title, abstract)
    return jsonify({'papers': papers})
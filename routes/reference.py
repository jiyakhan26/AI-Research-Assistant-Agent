from flask import Blueprint, render_template, request, jsonify
from agents.reference_agent import format_citation, batch_format

reference_bp = Blueprint('reference', __name__)


@reference_bp.route('/')
def reference_page():
    return render_template('reference.html')


@reference_bp.route('/format', methods=['POST'])
def format_ref():
    data = request.get_json()
    citation_data = {
        'authors': data.get('authors', ''),
        'title': data.get('title', ''),
        'year': data.get('year', ''),
        'journal': data.get('journal', ''),
        'url': data.get('url', '')
    }
    style = data.get('style', 'apa')

    apa = format_citation(citation_data, 'apa')
    ieee = format_citation(citation_data, 'ieee')
    mla = format_citation(citation_data, 'mla')

    return jsonify({
        'apa': apa,
        'ieee': ieee,
        'mla': mla,
        'selected': format_citation(citation_data, style)
    })


@reference_bp.route('/batch', methods=['POST'])
def batch():
    data = request.get_json()
    citations = data.get('citations', [])
    style = data.get('style', 'apa')

    if not citations:
        return jsonify({'error': 'No citations provided'}), 400

    results = batch_format(citations, style)
    return jsonify({'formatted': results})
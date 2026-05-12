import os
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from agents.citation_agent import extract_citations_from_pdf, extract_citations_from_text
from agents.reference_agent import format_citation
from app import db
from models import Citation

citation_bp = Blueprint('citation', __name__)

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@citation_bp.route('/')
def citation_page():
    return render_template('citation.html')


@citation_bp.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    try:
        citations = extract_citations_from_pdf(upload_path)

        # Format and save to DB
        results = []
        for cit in citations[:30]:
            apa = format_citation(cit, 'apa')
            ieee = format_citation(cit, 'ieee')
            cit['apa_format'] = apa
            cit['ieee_format'] = ieee

            db_cit = Citation(
                raw_text=cit['raw_text'],
                authors=cit.get('authors', ''),
                title=cit.get('title', ''),
                year=cit.get('year', ''),
                journal=cit.get('journal', ''),
                apa_format=apa,
                ieee_format=ieee
            )
            db.session.add(db_cit)
            results.append(cit)

        db.session.commit()
        return jsonify({'citations': results, 'count': len(results), 'filename': filename})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


@citation_bp.route('/from-text', methods=['POST'])
def from_text():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    citations = extract_citations_from_text(text)
    for cit in citations:
        cit['apa_format'] = format_citation(cit, 'apa')
        cit['ieee_format'] = format_citation(cit, 'ieee')

    return jsonify({'citations': citations, 'count': len(citations)})
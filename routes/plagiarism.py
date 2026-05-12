import json
from flask import Blueprint, render_template, request, jsonify
from agents.plagiarism_agent import check_plagiarism
from extensions import db
from models import PlagiarismReport

plagiarism_bp = Blueprint('plagiarism', __name__)


@plagiarism_bp.route('/')
def plagiarism_page():
    return render_template('plagiarism.html')


@plagiarism_bp.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'No text provided'}), 400
    if len(text.split()) < 10:
        return jsonify({'error': 'Text must be at least 10 words'}), 400

    try:
        result = check_plagiarism(text)

        # Save report
        report = PlagiarismReport(
            text_snippet=text[:300],
            similarity_score=result['overall_score'],
            matched_source=result['top_matches'][0]['source'] if result['top_matches'] else '',
            report_data=json.dumps(result)
        )
        db.session.add(report)
        db.session.commit()

        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


from sqlalchemy import select

@plagiarism_bp.route('/history')
def history():
    reports = db.session.execute(
        select(PlagiarismReport).order_by(PlagiarismReport.created_at.desc()).limit(10)
    ).scalars().all()
    return jsonify({'reports': [r.to_dict() for r in reports]})
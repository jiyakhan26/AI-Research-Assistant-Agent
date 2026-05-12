from flask import Blueprint, render_template
from extensions import db
from models import Paper, Citation, PlagiarismReport, SearchHistory
from sqlalchemy import select, func

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    stats = {
        'papers': db.session.execute(select(func.count()).select_from(Paper)).scalar(),
        'citations': db.session.execute(select(func.count()).select_from(Citation)).scalar(),
        'reports': db.session.execute(select(func.count()).select_from(PlagiarismReport)).scalar(),
        'searches': db.session.execute(select(func.count()).select_from(SearchHistory)).scalar(),
    }
    recent_searches = db.session.execute(
        select(SearchHistory).order_by(SearchHistory.created_at.desc()).limit(5)
    ).scalars().all()
    recent_papers = db.session.execute(
        select(Paper).order_by(Paper.created_at.desc()).limit(5)
    ).scalars().all()

    return render_template('dashboard.html', stats=stats, recent_searches=recent_searches, recent_papers=recent_papers)
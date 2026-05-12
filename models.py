"""
Database Models - SQLAlchemy ORM Models for Research Agent
"""

from extensions import db
from datetime import datetime


class Paper(db.Model):
    """Represents a research paper fetched from APIs or uploaded."""
    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.String(500))
    abstract = db.Column(db.Text)
    year = db.Column(db.Integer)
    source = db.Column(db.String(100))         # 'arxiv' or 'semantic_scholar'
    paper_id = db.Column(db.String(200))        # External API ID
    url = db.Column(db.String(500))
    pdf_url = db.Column(db.String(500))
    citation_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    citations = db.relationship('Citation', backref='paper', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'year': self.year,
            'source': self.source,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'citation_count': self.citation_count
        }


class Citation(db.Model):
    """Represents a citation extracted from a paper."""
    __tablename__ = 'citations'

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=True)
    raw_text = db.Column(db.Text, nullable=False)
    authors = db.Column(db.String(500))
    title = db.Column(db.String(500))
    year = db.Column(db.String(10))
    journal = db.Column(db.String(300))
    apa_format = db.Column(db.Text)
    ieee_format = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'raw_text': self.raw_text,
            'authors': self.authors,
            'title': self.title,
            'year': self.year,
            'journal': self.journal,
            'apa_format': self.apa_format,
            'ieee_format': self.ieee_format
        }


class PlagiarismReport(db.Model):
    """Stores plagiarism detection results."""
    __tablename__ = 'plagiarism_reports'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    text_snippet = db.Column(db.Text)
    similarity_score = db.Column(db.Float)
    matched_source = db.Column(db.String(500))
    report_data = db.Column(db.Text)             # JSON string of full results
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'similarity_score': self.similarity_score,
            'matched_source': self.matched_source,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class SearchHistory(db.Model):
    """Logs user search queries."""
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False)
    source = db.Column(db.String(50))
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
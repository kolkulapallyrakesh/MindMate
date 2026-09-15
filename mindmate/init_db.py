"""Run once to (re)create the SQLite database schema: python init_db.py"""
from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print("Database initialized at instance/mindmate.db")

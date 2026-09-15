from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # streak tracking
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_active_date = db.Column(db.Date, nullable=True)

    mood_entries = db.relationship("MoodEntry", backref="user", lazy=True, cascade="all, delete-orphan")
    journal_entries = db.relationship("JournalEntry", backref="user", lazy=True, cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def update_streak(self):
        """Call whenever the user meaningfully engages (chat / mood / journal)."""
        today = date.today()
        if self.last_active_date == today:
            return  # already counted today
        if self.last_active_date == today - timedelta(days=1):
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_active_date = today
        if self.current_streak > (self.longest_streak or 0):
            self.longest_streak = self.current_streak


class MoodEntry(db.Model):
    __tablename__ = "mood_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)  # explicit self-rating 1 (low) - 5 (great)
    note = db.Column(db.String(500))
    source = db.Column(db.String(20), default="manual")  # manual | chat | journal
    sentiment_compound = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class JournalEntry(db.Model):
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150))
    content = db.Column(db.Text, nullable=False)
    sentiment_label = db.Column(db.String(20))       # Positive / Neutral / Negative
    sentiment_compound = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)   # 'user' | 'bot'
    message = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50))
    sentiment_compound = db.Column(db.Float, default=0.0)
    is_crisis = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from config import Config
from models import db, User, MoodEntry, JournalEntry, ChatMessage
import chatbot_engine as bot


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()

    # ------------------------------------------------------------------ #
    # Public pages
    # ------------------------------------------------------------------ #
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("All fields are required.", "danger")
                return redirect(url_for("register"))

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "danger")
                return redirect(url_for("register"))

            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    @app.route("/dashboard")
    @login_required
    def dashboard():
        recent_moods = (
            MoodEntry.query.filter_by(user_id=current_user.id)
            .order_by(MoodEntry.created_at.desc())
            .limit(14)
            .all()
        )
        recent_journals = (
            JournalEntry.query.filter_by(user_id=current_user.id)
            .order_by(JournalEntry.created_at.desc())
            .limit(5)
            .all()
        )
        total_chats = ChatMessage.query.filter_by(user_id=current_user.id, sender="user").count()

        mood_labels = [m.created_at.strftime("%d %b") for m in reversed(recent_moods)]
        mood_values = [m.mood_score for m in reversed(recent_moods)]

        return render_template(
            "dashboard.html",
            recent_journals=recent_journals,
            total_chats=total_chats,
            mood_labels=mood_labels,
            mood_values=mood_values,
        )

    # ------------------------------------------------------------------ #
    # Chat
    # ------------------------------------------------------------------ #
    @app.route("/chat")
    @login_required
    def chat_page():
        history = (
            ChatMessage.query.filter_by(user_id=current_user.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(50)
            .all()
        )
        return render_template("chat.html", history=history)

    @app.route("/api/chat", methods=["POST"])
    @login_required
    def api_chat():
        payload = request.get_json(force=True) or {}
        user_text = (payload.get("message") or "").strip()
        if not user_text:
            return jsonify({"error": "Empty message"}), 400

        result = bot.generate_reply(user_text)
        compound = result["sentiment"]["compound"]

        user_msg = ChatMessage(
            user_id=current_user.id, sender="user", message=user_text,
            intent=result["intent"], sentiment_compound=compound,
            is_crisis=result["is_crisis"],
        )
        bot_msg = ChatMessage(
            user_id=current_user.id, sender="bot", message=result["reply"],
            intent=result["intent"], sentiment_compound=compound,
            is_crisis=result["is_crisis"],
        )
        db.session.add_all([user_msg, bot_msg])

        # Passively log an implicit mood point from the chat sentiment
        implicit_score = round((compound + 1) * 2 + 1)  # maps [-1,1] -> [1,5]
        implicit_score = max(1, min(5, implicit_score))
        db.session.add(MoodEntry(
            user_id=current_user.id, mood_score=implicit_score,
            note=None, source="chat", sentiment_compound=compound,
        ))

        current_user.update_streak()
        db.session.commit()

        return jsonify({
            "reply": result["reply"],
            "intent": result["intent"],
            "is_crisis": result["is_crisis"],
            "tip": result["tip"],
            "crisis_resources": result["crisis_resources"],
            "sentiment": result["sentiment"],
        })

    # ------------------------------------------------------------------ #
    # Mood tracker
    # ------------------------------------------------------------------ #
    @app.route("/mood", methods=["GET", "POST"])
    @login_required
    def mood_page():
        if request.method == "POST":
            score = int(request.form.get("mood_score", 3))
            note = request.form.get("note", "").strip()
            sentiment = bot.analyze_sentiment(note) if note else {"compound": 0.0}
            entry = MoodEntry(
                user_id=current_user.id, mood_score=score, note=note or None,
                source="manual", sentiment_compound=sentiment["compound"],
            )
            db.session.add(entry)
            current_user.update_streak()
            db.session.commit()
            flash("Mood logged. Thanks for checking in with yourself today!", "success")
            return redirect(url_for("mood_page"))

        entries = (
            MoodEntry.query.filter_by(user_id=current_user.id)
            .order_by(MoodEntry.created_at.desc())
            .limit(30)
            .all()
        )
        chart_labels = [m.created_at.strftime("%d %b %H:%M") for m in reversed(entries)]
        chart_values = [m.mood_score for m in reversed(entries)]
        return render_template(
            "mood.html", entries=entries,
            chart_labels=chart_labels, chart_values=chart_values,
        )

    # ------------------------------------------------------------------ #
    # Journal
    # ------------------------------------------------------------------ #
    @app.route("/journal", methods=["GET", "POST"])
    @login_required
    def journal_page():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            if not content:
                flash("Journal entry can't be empty.", "danger")
                return redirect(url_for("journal_page"))

            sentiment = bot.analyze_sentiment(content)
            label = bot.sentiment_label(sentiment["compound"])
            entry = JournalEntry(
                user_id=current_user.id, title=title or "Untitled",
                content=content, sentiment_label=label,
                sentiment_compound=sentiment["compound"],
            )
            db.session.add(entry)
            current_user.update_streak()
            db.session.commit()
            flash(f"Entry saved. Detected mood: {label}", "success")
            return redirect(url_for("journal_page"))

        entries = (
            JournalEntry.query.filter_by(user_id=current_user.id)
            .order_by(JournalEntry.created_at.desc())
            .all()
        )
        return render_template("journal.html", entries=entries)

    @app.route("/journal/<int:entry_id>/delete", methods=["POST"])
    @login_required
    def delete_journal(entry_id):
        entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
        db.session.delete(entry)
        db.session.commit()
        return redirect(url_for("journal_page"))

    # ------------------------------------------------------------------ #
    # Resources (static self-help + crisis info)
    # ------------------------------------------------------------------ #
    @app.route("/resources")
    def resources_page():
        return render_template("resources.html", crisis=bot.CRISIS_RESOURCES)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

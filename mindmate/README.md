# MindMate — A Mental Health Support & Self-Care Chatbot

A full-stack Flask web application for a college mini-project: an offline,
rule-based mental health support chatbot with mood tracking, journaling,
sentiment analysis, streaks, and a curated resources/crisis-helpline page.

> ⚠️ **Scope disclaimer**: This is a self-reflection and support tool built
> for an academic project. It is **not** a diagnostic tool and **not** a
> replacement for a licensed mental health professional. Say this explicitly
> in your presentation — evaluators respond well to responsible framing.

---

## 1. Features

| Feature | Description |
|---|---|
| **Auth** | Email/password signup & login (hashed passwords via Werkzeug, sessions via Flask-Login) |
| **Chatbot** | Rule-based intent detection (regex/keyword matching) + VADER sentiment analysis, fully offline |
| **Crisis detection** | Dedicated keyword layer that overrides normal chat and surfaces verified helpline numbers |
| **Mood tracker** | Manual 1–5 mood check-ins with optional notes, plus automatic passive mood logging from chat sentiment; trend chart via Chart.js |
| **Journal** | Free-text journaling; each entry auto-tagged Positive/Neutral/Negative via sentiment score |
| **Streaks** | Daily engagement streak counter (current + longest) to encourage consistent check-ins |
| **Dashboard** | At-a-glance stats: streak, chat count, mood trend chart, recent journal entries |
| **Resources page** | Categorized self-help tips + crisis helpline numbers (India + international) |

---

## 2. Tech Stack

- **Backend**: Python 3, Flask, Flask-SQLAlchemy, Flask-Login
- **Database**: SQLite (zero-config, file-based — easy to demo)
- **NLP**: [VADER Sentiment](https://github.com/cjhutto/vaderSentiment) — lexicon & rule-based sentiment scoring, no internet/API call required
- **Frontend**: Server-rendered Jinja2 templates + vanilla JS (fetch API) for the chat AJAX interaction, Chart.js (via CDN) for graphs
- **Auth/security**: Werkzeug password hashing, Flask-Login session management

### Why rule-based instead of an LLM API?
This keeps the project **fully offline, free to run, deterministic, and easy
to explain line-by-line in a viva** — a common ask from evaluators ("what is
actually happening inside your chatbot?"). The intent-matching and sentiment
logic in `chatbot_engine.py` is short and transparent enough to walk through
on a whiteboard.

---

## 3. Project Structure

```
mindmate/
├── app.py                 # Flask app factory + all routes
├── config.py               # Configuration (secret key, DB URI, thresholds)
├── models.py                # SQLAlchemy models: User, MoodEntry, JournalEntry, ChatMessage
├── chatbot_engine.py        # Rule-based NLP: intent detection, sentiment, crisis detection
├── init_db.py                # One-off DB initialization script
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── js/chat.js
├── templates/
│   ├── base.html, index.html, login.html, register.html
│   ├── dashboard.html, chat.html, mood.html, journal.html, resources.html
└── instance/
    └── mindmate.db          # created automatically on first run
```

---

## 4. Setup & Run

```bash
# 1. Clone / unzip the project, then cd into it
cd mindmate

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) set a real secret key
export SECRET_KEY="change-this-in-production"     # Windows: set SECRET_KEY=...

# 5. Run the app
python app.py
```

Open **http://localhost:5000** in your browser. The SQLite database is
created automatically on first run inside `instance/mindmate.db`.

To reset the database at any point:
```bash
rm instance/mindmate.db   # Windows: del instance\mindmate.db
python init_db.py
```

---

## 5. How the chatbot works (for your report / viva)

1. **User sends a message** → POST to `/api/chat`.
2. **Crisis check first** (`chatbot_engine._matches_crisis`): a small set of
   regex patterns (e.g. self-harm, suicidal ideation phrases) is checked
   *before* anything else. If matched, the bot always responds with an
   empathetic message + a fixed list of verified helpline numbers — it
   never tries to be clever here, by design.
3. **Sentiment scoring** (`analyze_sentiment`): VADER returns a compound
   score from -1 (very negative) to +1 (very positive). This score is
   stored with every chat message, mood entry, and journal entry, and
   drives the dashboard trend charts.
4. **Intent detection** (`detect_intent`): each intent (anxious, sad, angry,
   sleep, lonely, motivation, happy, greeting, etc.) has a list of regex
   keyword patterns. The intent with the most pattern matches wins; ties
   default to `fallback`.
5. **Response generation**: a random response is chosen from that intent's
   response pool (keeps the conversation from feeling robotic on repeat
   visits), plus an optional coping "tip" specific to that intent.
6. **Passive mood logging**: every chat message's sentiment score is mapped
   from `[-1, 1]` onto a `[1, 5]` mood scale and logged automatically, so
   the mood chart reflects both explicit check-ins and conversational tone.
7. **Streaks**: `User.update_streak()` runs on every meaningful action
   (chat, mood log, or journal entry) and increments/resets a daily streak
   counter based on `last_active_date`.

---

## 6. Suggested demo flow (for judging)

1. Register a new account → show the clean signup/login flow.
2. Go to **Chat**, type something like *"I'm really stressed about my
   exams"* → show the detected intent + coping tip in the browser dev tools
   network tab (proves it's a real API call, not canned text).
3. Type a crisis-style message (e.g. *"I don't want to live anymore"*) in a
   **safe, controlled test environment** → show the escalation UI with
   helpline numbers. (Mention responsibly during demo that this is a
   simulated example for demonstration purposes.)
4. Go to **Mood Tracker** → log a mood, show the note gets sentiment-scored.
5. Go to **Journal** → write an entry, show the auto-tagged sentiment pill.
6. Go to **Dashboard** → show the mood trend chart updating live and the
   streak counter.
7. Go to **Resources** → show the curated self-help content and helpline
   numbers.

---

## 7. Possible extensions (mention these as "future scope" in your report)

- Swap/augment the rule-based engine with a fine-tuned transformer model
  or an LLM API for more natural conversation (trade-off: needs internet +
  API cost + less predictable safety behavior).
- Add a counselor/admin dashboard with aggregated (anonymized) analytics.
- Add push/email reminders for daily check-ins.
- Deploy with PostgreSQL + Docker for production use.
- Add multi-language support for regional accessibility.

---

## 8. Credits & Data

- Sentiment analysis: VADER (Hutto & Gilbert, 2014) — MIT licensed.
- Crisis helpline numbers (India): KIRAN (Govt. of India), Vandrevala
  Foundation, iCall (TISS) — publicly listed helplines, verify current
  numbers before presenting/publishing.

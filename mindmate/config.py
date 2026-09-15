import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'mindmate.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # App-level thresholds
    CRISIS_SENTIMENT_THRESHOLD = -0.6  # VADER compound score below this + crisis keywords -> escalate
    STREAK_RESET_HOURS = 48  # if user doesn't check in within this window, streak resets

"""
chatbot_engine.py
------------------
A fully offline, rule-based conversational engine for the MindMate mental
health support chatbot. No external LLM API calls are made — intent is
detected via keyword/pattern matching and sentiment is scored using VADER
(a lexicon + rule based sentiment tool that ships its own lexicon, so it
needs no internet access or corpus download at runtime).

Design notes (useful for your project report / viva):
1. Intent detection: simple, transparent keyword scoring. Easy to explain
   to evaluators and to extend with more patterns.
2. Sentiment scoring: VADER compound score in [-1, 1]. Used to (a) tag
   mood automatically from free text, (b) decide response tone, and
   (c) trigger crisis escalation.
3. Crisis detection: a dedicated, HIGHEST-PRIORITY keyword layer that
   overrides normal intent routing whenever self-harm / suicide language
   is detected. It always returns supportive, non-judgemental language
   plus real crisis helpline numbers — it never gives step-by-step
   guidance of any kind, only redirects to human help.
4. This is a *support and self-reflection tool*, not a replacement for a
   licensed therapist. That disclaimer is shown in the UI (see
   templates/chat.html) and should be repeated in your presentation.
"""

import random
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# ---------------------------------------------------------------------------
# Crisis keywords — kept intentionally short & non-explicit. Detection is
# purposely broad (better to over-trigger supportive resources than miss one).
# ---------------------------------------------------------------------------
CRISIS_PATTERNS = [
    r"\bsuicid\w*\b",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bno reason to live\b",
    r"\bself[-\s]?harm\w*\b",
    r"\bhurt myself\b",
    r"\bcan'?t go on\b",
    r"\bgive up on life\b",
]

CRISIS_RESOURCES = {
    "india": [
        {"name": "KIRAN Mental Health Helpline (Govt. of India)", "phone": "1800-599-0019"},
        {"name": "Vandrevala Foundation Helpline", "phone": "1860-2662-345 / 1800-2333-330"},
        {"name": "iCall (TISS)", "phone": "9152987821"},
    ],
    "international": [
        {"name": "International Association for Suicide Prevention — crisis center finder", "phone": "https://www.iasp.info/resources/Crisis_Centres/"},
    ],
}

CRISIS_RESPONSE_TEMPLATES = [
    "I'm really glad you told me this, and I want you to know you don't have "
    "to go through it alone. What you're feeling matters, and there are people "
    "trained to help you through this right now.",
    "Thank you for trusting me with something this heavy. I'm concerned about "
    "your safety, and I'd really like you to reach out to someone who can "
    "support you directly — right now, if you can.",
]

# ---------------------------------------------------------------------------
# Intents: each has trigger keywords/patterns and a pool of responses.
# Order matters only for tie-breaking; scoring picks the best keyword match.
# ---------------------------------------------------------------------------
INTENTS = {
    "greeting": {
        "patterns": [r"\bhi\b", r"\bhello\b", r"\bhey\b", r"\bgood (morning|afternoon|evening)\b"],
        "responses": [
            "Hi there! I'm MindMate. How are you feeling today?",
            "Hello! I'm glad you're here. What's on your mind?",
            "Hey! How has your day been so far?",
        ],
    },
    "goodbye": {
        "patterns": [r"\bbye\b", r"\bgoodbye\b", r"\bsee you\b", r"\btalk later\b"],
        "responses": [
            "Take care of yourself. I'm here whenever you need to talk again.",
            "Goodbye for now — remember to be kind to yourself today.",
        ],
    },
    "thanks": {
        "patterns": [r"\bthank\w*\b", r"\bappreciate\b"],
        "responses": [
            "You're very welcome. I'm always here for you.",
            "Anytime — that's what I'm here for.",
        ],
    },
    "how_are_you": {
        "patterns": [r"how are you", r"how'?s it going"],
        "responses": [
            "I'm just a program, but I'm fully here for you! More importantly — how are *you* doing?",
        ],
    },
    "sad": {
        "patterns": [r"\bsad\b", r"\bdown\b", r"\bdepress\w*\b", r"\bhopeless\b", r"\bempty\b", r"\bcry\w*\b", r"\bmiserable\b"],
        "responses": [
            "I'm sorry you're feeling this way. It's okay to feel sad sometimes — would you like to talk about what's weighing on you?",
            "That sounds really hard. Sadness can feel heavy — I'm here to listen, no judgment at all.",
        ],
        "tip": "Try writing about it in your Journal — putting feelings into words can lighten the load a little. You could also try a short 4-7-8 breathing exercise: inhale 4s, hold 7s, exhale 8s.",
    },
    "anxious": {
        "patterns": [r"\banxi\w*\b", r"\bstress\w*\b", r"\boverwhelm\w*\b", r"\bworried?\b", r"\bpanic\w*\b", r"\bnervous\b"],
        "responses": [
            "It sounds like you're carrying a lot right now. Anxiety can feel really overwhelming — you're not alone in this.",
            "Stress has a way of piling up fast. Let's slow down for a second — what's the biggest thing on your mind?",
        ],
        "tip": "Grounding technique: name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste. It helps bring your mind back to the present.",
    },
    "angry": {
        "patterns": [r"\bangry\b", r"\bfrustrat\w*\b", r"\bmad\b", r"\birritat\w*\b", r"\bfurious\b"],
        "responses": [
            "That frustration sounds valid. Do you want to talk through what triggered it?",
            "It's okay to feel angry — it usually means something important to you was affected. I'm listening.",
        ],
        "tip": "Try stepping away for a few minutes and taking slow, deep breaths before responding to whatever triggered this.",
    },
    "sleep": {
        "patterns": [r"\bcan'?t sleep\b", r"\binsomnia\b", r"\btired\b", r"\bexhaust\w*\b", r"\bno sleep\b", r"\bfatigue\b"],
        "responses": [
            "Sleep struggles can really wear you down, both mentally and physically. How many nights has this been going on?",
        ],
        "tip": "A consistent wind-down routine helps: dim the lights, avoid screens 30 min before bed, and try slow breathing or light stretching.",
    },
    "lonely": {
        "patterns": [r"\blonely\b", r"\bisolat\w*\b", r"\bno friends\b", r"\bnobody\b", r"\balone\b"],
        "responses": [
            "Feeling lonely is genuinely painful, and I'm glad you shared it instead of holding it in.",
            "You reaching out here matters — loneliness is tough, but you don't have to carry it silently.",
        ],
        "tip": "Even a small step — texting one person, joining a club, or a short walk in a public space — can ease isolation over time.",
    },
    "motivation": {
        "patterns": [r"\bunmotivat\w*\b", r"\blazy\b", r"\bno energy\b", r"\bstuck\b", r"\bprocrastinat\w*\b", r"\bburnt?[ -]?out\b"],
        "responses": [
            "Low motivation happens to everyone, especially when you're mentally tired. What's one tiny task you could do in the next 10 minutes?",
        ],
        "tip": "Try the '2-minute rule': commit to just 2 minutes of the task. Often starting is the hardest part.",
    },
    "happy": {
        "patterns": [r"\bhappy\b", r"\bgreat\b", r"\bgood\b", r"\bexcited\b", r"\bawesome\b", r"\bgrateful\b"],
        "responses": [
            "That's wonderful to hear! What's contributing to the good mood?",
            "Love that energy! Want to log this moment in your journal so you can look back on it later?",
        ],
    },
}

FALLBACK_RESPONSES = [
    "I hear you. Can you tell me a bit more about that?",
    "Thanks for sharing that with me. How is it affecting you?",
    "I'm listening — go on, what else is on your mind?",
]


def _matches_crisis(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in CRISIS_PATTERNS)


def analyze_sentiment(text: str) -> dict:
    """Returns VADER scores dict with keys: neg, neu, pos, compound."""
    return _analyzer.polarity_scores(text)


def sentiment_label(compound: float) -> str:
    if compound >= 0.3:
        return "Positive"
    if compound <= -0.3:
        return "Negative"
    return "Neutral"


def detect_intent(text: str) -> str:
    text_lower = text.lower()
    best_intent, best_score = "fallback", 0
    for intent, data in INTENTS.items():
        score = sum(1 for p in data["patterns"] if re.search(p, text_lower))
        if score > best_score:
            best_intent, best_score = intent, score
    return best_intent


def generate_reply(text: str) -> dict:
    """
    Main entry point. Returns a dict:
    {
        reply: str,
        intent: str,
        sentiment: {neg, neu, pos, compound},
        is_crisis: bool,
        tip: str | None,
        crisis_resources: list | None
    }
    """
    sentiment = analyze_sentiment(text)
    compound = sentiment["compound"]

    if _matches_crisis(text):
        reply = random.choice(CRISIS_RESPONSE_TEMPLATES)
        return {
            "reply": reply,
            "intent": "crisis",
            "sentiment": sentiment,
            "is_crisis": True,
            "tip": None,
            "crisis_resources": CRISIS_RESOURCES,
        }

    intent = detect_intent(text)

    if intent == "fallback":
        # Fall back to sentiment-driven generic empathy if no keyword intent matched
        if compound <= -0.4:
            reply = "That sounds tough. I'm here with you — do you want to share more?"
            tip = "Sometimes writing it down first (in the Journal tab) helps organize the thoughts."
        elif compound >= 0.4:
            reply = "That's great to hear! Tell me more."
            tip = None
        else:
            reply = random.choice(FALLBACK_RESPONSES)
            tip = None
        return {
            "reply": reply,
            "intent": "fallback",
            "sentiment": sentiment,
            "is_crisis": False,
            "tip": tip,
            "crisis_resources": None,
        }

    data = INTENTS[intent]
    reply = random.choice(data["responses"])
    tip = data.get("tip")
    return {
        "reply": reply,
        "intent": intent,
        "sentiment": sentiment,
        "is_crisis": False,
        "tip": tip,
        "crisis_resources": None,
    }

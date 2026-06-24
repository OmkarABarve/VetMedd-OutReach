"""
sentiment.py - Detect the tone of a contact's free-text reply (Responses column).

Used only for the "engaged" scenario, to pick warmer/softer phrasing. Returns one
of: "positive", "neutral", "negative". Defaults to "neutral" when the model is
unavailable or the text is empty.

The transformers pipeline is loaded lazily and cached.
"""

import config


_sentiment_pipeline = None
_pipeline_failed = False

# Map various model label formats to our three buckets.
_LABEL_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "label_0": "negative",
    "label_1": "neutral",
    "label_2": "positive",
}

# Lightweight keyword fallback when the model isn't available.
_POSITIVE_WORDS = ["great", "interested", "love", "yes", "thanks", "awesome", "good", "sure"]
_NEGATIVE_WORDS = ["not interested", "no thanks", "stop", "unsubscribe", "bad", "never", "annoying"]


def _get_pipeline():
    """Lazily build and cache the sentiment-analysis pipeline."""
    global _sentiment_pipeline, _pipeline_failed
    if _sentiment_pipeline is not None or _pipeline_failed:
        return _sentiment_pipeline
    try:
        from transformers import pipeline

        _sentiment_pipeline = pipeline("sentiment-analysis", model=config.SENTIMENT_MODEL)
    except Exception as exc:
        print(f"[sentiment] model unavailable, using keyword fallback: {exc}")
        _pipeline_failed = True
    return _sentiment_pipeline


def _keyword_sentiment(text: str) -> str:
    low = text.lower()
    if any(w in low for w in _NEGATIVE_WORDS):
        return "negative"
    if any(w in low for w in _POSITIVE_WORDS):
        return "positive"
    return "neutral"


def detect_sentiment(text) -> str:
    """Return 'positive' | 'neutral' | 'negative' for the given reply text."""
    if text is None:
        return "neutral"
    text = str(text).strip()
    if not text:
        return "neutral"

    pipe = _get_pipeline()
    if pipe is not None:
        try:
            result = pipe(text[:512])[0]  # truncate to model max length
            label = str(result["label"]).lower()
            return _LABEL_MAP.get(label, "neutral")
        except Exception as exc:
            print(f"[sentiment] inference error, using keyword fallback: {exc}")

    return _keyword_sentiment(text)

"""
classifier.py - Infer a missing Classification for a contact.

Strategy (keyword-first for speed + determinism):
  1. Cheap keyword match on the company name (config.CLASSIFICATION_KEYWORDS).
     If EXACTLY ONE category matches, use it -> the heavy model never loads.
  2. If keywords are ambiguous (>1 match) or find nothing (0), fall back to the
     zero-shot NLP model (HuggingFace transformers) over config.CLASSIFICATION_LABELS.
  3. If the model is unavailable / low-confidence, take the first keyword match if
     any, else return "" (unknown) so message_builder uses the fallback template.

The transformers pipeline is loaded lazily and cached, so the heavy model only
loads once per process AND only when keywords couldn't decide on their own.
"""

import config


_classifier_pipeline = None
_pipeline_failed = False


def _get_pipeline():
    """Lazily build and cache the zero-shot classification pipeline."""
    global _classifier_pipeline, _pipeline_failed
    if _classifier_pipeline is not None or _pipeline_failed:
        return _classifier_pipeline
    try:
        from transformers import pipeline

        _classifier_pipeline = pipeline(
            "zero-shot-classification", model=config.ZERO_SHOT_MODEL
        )
    except Exception as exc:
        # transformers/torch not installed or model download failed.
        print(f"[classifier] zero-shot model unavailable, using keyword fallback: {exc}")
        _pipeline_failed = True
    return _classifier_pipeline


def _keyword_matches(text: str) -> list[str]:
    """Return all labels whose keywords appear in the text (case-insensitive)."""
    low = text.lower()
    return [
        label
        for label, keywords in config.CLASSIFICATION_KEYWORDS.items()
        if any(kw in low for kw in keywords)
    ]


def classify(company_name: str) -> tuple[str, float]:
    """Infer a classification label for a company. Keyword-first, model fallback.

    Returns (label, confidence). label is "" when unknown.
    """
    text = (company_name or "").strip()
    if not text:
        return "", 0.0

    # 1) Cheap, deterministic keyword pass FIRST. Trust it only when it's
    #    unambiguous (exactly one category matches) -> avoids loading the model.
    matches = _keyword_matches(text)
    if len(matches) == 1:
        return matches[0], 1.0

    # 2) Ambiguous (>1) or no keyword hit (0) -> ask the zero-shot model.
    pipe = _get_pipeline()
    if pipe is not None:
        try:
            result = pipe(text, config.CLASSIFICATION_LABELS)
            top_label = result["labels"][0]
            top_score = float(result["scores"][0])
            if top_score >= config.NLP_CONFIDENCE_THRESHOLD:
                return top_label, top_score
        except Exception as exc:
            print(f"[classifier] inference error, using keyword fallback: {exc}")

    # 3) Model unavailable / low-confidence: take the first keyword match if any.
    return (matches[0], 0.5) if matches else ("", 0.0)
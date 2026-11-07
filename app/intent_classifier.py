from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "intent_model.joblib"

# Confidence is se kam ho to "pata nahi" maanenge aur user se poochenge
CONFIDENCE_THRESHOLD = 0.40

_model = None  # ek baar load hoga, phir yaad rahega


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_intent(text):
    """
    Message ka intent batata hai.
    Return: {"intent": "...", "confidence": 0.0-1.0, "confident": True/False}
    """
    model = _load_model()
    text = (text or "").lower().strip()
    if not text:
        return {"intent": "other", "confidence": 0.0, "confident": False}

    probs = model.predict_proba([text])[0]
    best = probs.argmax()
    confidence = float(probs[best])
    return {
        "intent": str(model.classes_[best]),
        "confidence": round(confidence, 3),
        "confident": confidence >= CONFIDENCE_THRESHOLD,
    }
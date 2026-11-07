from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline

BASE = Path(__file__).resolve().parent.parent
DATA_PATH = BASE / "data" / "intents.csv"
MODEL_PATH = BASE / "models" / "intent_model.joblib"
CM_PATH = BASE / "models" / "confusion_matrix.png"


def build_model():
    features = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2))),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=1000, C=10)),
    ])


def main():
    df = pd.read_csv(DATA_PATH)
    df["text"] = df["text"].str.lower().str.strip()
    print("Total examples:", len(df))

    # ---- A. 5-fold cross-validation (zyada bharosemand score) ----
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(build_model(), df["text"], df["intent"], cv=cv, scoring="accuracy")
    print("\n5-fold CV accuracy per fold:", [round(s, 3) for s in scores])
    print("CV accuracy mean: %.3f (+/- %.3f)" % (scores.mean(), scores.std()))

    # ---- B. Single 80/20 split (detailed report + confusion matrix) ----
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["intent"],
        test_size=0.2, random_state=42, stratify=df["intent"],
    )
    print("\nTrain:", len(X_train), "| Test:", len(X_test))

    model = build_model()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("\nHold-out accuracy:", round(accuracy_score(y_test, y_pred), 3))
    print("\nClassification report (precision, recall, F1):\n")
    print(classification_report(y_test, y_pred, zero_division=0))

    labels = sorted(df["intent"].unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay(cm, display_labels=labels).plot(
        ax=ax, xticks_rotation=45, colorbar=False
    )
    plt.tight_layout()
    plt.savefig(CM_PATH, dpi=150)
    print("Confusion matrix saved:", CM_PATH)

    # ---- C. Final model poore data par train karke save ----
    final_model = build_model()
    final_model.fit(df["text"], df["intent"])
    joblib.dump(final_model, MODEL_PATH)
    print("Model saved:", MODEL_PATH)


if __name__ == "__main__":
    main()
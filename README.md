# LeaveMate AI

Agentic AI assistant for university leave and request management (demo project).
Understands English and Hinglish. Uses **fictional students and fictional data only**.

## Features
- Chat assistant: create RMS requests, apply for leave, check status, view history, cancel pending requests, ask about the process
- Intent classifier (scikit-learn: TF-IDF + Logistic Regression) for English/Hinglish messages
- LLM (Gemini) extracts details such as dates, reason and category; asks follow-up questions when something is missing
- LangGraph workflows for the leave agent and the RMS agent
- Confirmation before every submission
- Student dashboard, request history, status tracking, and a demo admin page
- Rule-based fallback when the LLM quota is exhausted or the server is busy

## Safety design
- The LLM never touches the database. All reads and writes go through controlled Python functions.
- Validation, duplicate/overlap checks and ownership checks happen inside those functions.
- A request is reported as submitted only after it is saved successfully.
- API keys live in `.env` (not committed).

## Tech stack
Python, Streamlit, SQLite, LangGraph, Google Gemini API, scikit-learn

## Setup
```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Copy `.env.example` to `.env` and add your own Gemini API key.

Train the intent model (creates `models/intent_model.joblib`):
```
python -m app.train_intent
```

Run the app:
```
python -m streamlit run main.py
```
The database is created automatically on first run.

## Intent classifier evaluation
- Dataset: 216 labelled messages, 7 intents (English + Hinglish)
- 5-fold cross-validation accuracy: 85.7% (+/- 4.2%)
- Metrics: accuracy, precision, recall, F1, confusion matrix (see `models/`)
- These are classifier metrics only. They are not end-to-end agent performance.

## Testing results
- Intent routing sanity check (20 unseen messages): 19/20 correct. The one miss was a casual English greeting.
- Agent flows and security (22 automated tests, LLM disabled so fallback mode is exercised): 22/22 passed.
- Covered: confirmation required before save, duplicate and overlap blocking, past-date and 7-day-limit rejection, ownership checks, invalid input rejection, SQL-injection-style text.
- Run with: `python -m tests.test_e2e` (uses a temporary database, your real data is untouched).
- Results table: `tests/e2e_results.csv`
- The 20-message routing check is a sanity check, not a benchmark. The main classifier metric is the 5-fold cross-validation accuracy above.
## Limitations
- Small dataset; results are indicative only
- Leave rules are demo rules, not real university rules
- No integration with the real university portal. Any future integration must use authorized access only.
- Fallback mode is simple keyword-based and less accurate than the LLM

## Project structure
```
app/     database, tools, agents, classifier, LLM helper
pages/   Dashboard and Admin pages
data/    intents.csv
tests/   test scripts
main.py  chat interface
```
from app.intent_classifier import predict_intent

messages = [
    "Meri attendance galat mark hui hai, RMS raise karna hai.",
    "I want to apply for leave tomorrow.",
    "Check my RMS status.",
    "I want to cancel my pending request.",
    "Mere pichle applications dikhao",
    "Leave ke liye kya documents lagte hain?",
    "Hello bhai",
    "Aaj ka match kaun jeeta?",
]

for m in messages:
    result = predict_intent(m)
    print(f"{result['intent']:<16} conf={result['confidence']:<6} confident={result['confident']}  <- {m}")
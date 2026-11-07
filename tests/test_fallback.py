from datetime import date

from app.fallback import fallback_leave, fallback_rms

today = date(2026, 11, 8)

print("--- LEAVE ---")
for m in [
    "Kal se 2 din ki leave chahiye, bukhar hai",
    "Mujhe parso shaadi ke liye leave chahiye",
    "leave from 2026-11-20",
    "I need leave next Monday",
]:
    print(m)
    print("  ->", fallback_leave(m, today))

print("\n--- RMS ---")
for m in [
    "Meri attendance galat mark hui hai",
    "UMS portal login nahi ho raha",
    "Mujhe bonafide certificate chahiye",
    "Mere marks galat aaye hain",
    "RMS raise karna hai",
]:
    print(m)
    print("  ->", fallback_rms(m))
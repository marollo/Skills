#!/usr/bin/env python3
"""Score the closed question types (mcq, multi, tf) of a submitted exam.

Usage:
    python3 grade_closed.py answer_key.json submission.json [--out result.json]

answer_key.json  {"1": {"type": "mcq", "points": 2, "correct": "B"},
                  "15": {"type": "multi", "points": 3, "correct": ["A", "C"]},
                  "23": {"type": "tf", "points": 1, "correct": "T"},
                  "9": {"type": "short", "points": 4}}          # open types are listed, not scored
submission.json  the payload the exam page produced. A document read from the
                 page database ({"payload": {...}}) is accepted as well.

Scoring rules (same as SKILL.md section 5):
  mcq / tf : full points if the answer matches, otherwise 0
  multi    : +1 per correct option ticked, -1 per wrong option ticked,
             points = max(0, net / number_of_correct_options) * question points
  open     : not scored here; returned under "needs_manual_grading"
"""
import argparse
import json
import sys
from pathlib import Path

GRADE_TABLE = [(95, 1.0), (90, 1.3), (85, 1.7), (80, 2.0), (75, 2.3), (70, 2.7),
               (65, 3.0), (60, 3.3), (55, 3.7), (50, 4.0)]


def grade_de(percent):
    for floor, grade in GRADE_TABLE:
        if percent >= floor:
            return grade
    return 5.0


def score_question(spec, given):
    pts = float(spec["points"])
    t = spec["type"]
    if given in (None, "", []):
        return 0.0, "unanswered"
    if t in ("mcq", "tf"):
        ok = str(given).strip().upper() == str(spec["correct"]).strip().upper()
        return (pts if ok else 0.0), ("correct" if ok else "incorrect")
    if t == "multi":
        correct = {c.upper() for c in spec["correct"]}
        chosen = {c.upper() for c in (given if isinstance(given, list) else [given])}
        net = len(chosen & correct) - len(chosen - correct)
        earned = max(0.0, net / len(correct)) * pts
        if chosen == correct:
            return pts, "correct"
        return round(earned, 4), ("partial" if earned > 0 else "incorrect")
    raise ValueError(f"unsupported closed type {t!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("answer_key")
    ap.add_argument("submission")
    ap.add_argument("--out")
    args = ap.parse_args()

    key = json.loads(Path(args.answer_key).read_text(encoding="utf-8"))
    sub = json.loads(Path(args.submission).read_text(encoding="utf-8"))
    payload = sub.get("payload", sub)
    answers = payload.get("answers", {})

    rows, manual = [], []
    earned_total = possible_closed = possible_all = 0.0
    for qid in sorted(key, key=lambda x: (len(x), x)):
        spec = key[qid]
        possible_all += float(spec["points"])
        if spec["type"] not in ("mcq", "multi", "tf"):
            manual.append(qid)
            continue
        earned, result = score_question(spec, answers.get(qid))
        earned_total += earned
        possible_closed += float(spec["points"])
        rows.append({"id": int(qid) if qid.isdigit() else qid, "type": spec["type"], "points_possible": spec["points"],
                     "points_earned": round(earned, 2), "result": result, "given": answers.get(qid)})

    out = {"exam_id": payload.get("exam_id"), "elapsed_seconds": payload.get("elapsed_seconds"),
           "closed_points_earned": round(earned_total, 2), "closed_points_possible": possible_closed,
           "points_possible_total": possible_all, "needs_manual_grading": manual, "questions": rows}
    if not manual and possible_closed:
        pct = round(100 * earned_total / possible_closed, 1)
        out.update(percent=pct, grade_de=grade_de(pct), passed=pct >= 50)

    text = json.dumps(out, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())

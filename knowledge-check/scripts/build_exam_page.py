#!/usr/bin/env python3
"""Build the interactive exam page for the knowledge-check skill.

Usage:
    python3 build_exam_page.py exam.json out.html            # page content for the Artifact tool
    python3 build_exam_page.py exam.json out.html --standalone   # full HTML document for opening as a local file

exam.json holds the questions only. It must never contain the answer key: the
page is published and the person taking the exam could read its source. The
script refuses to build when it finds key-like fields. See
references/exam-page.md for the exam.json schema.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN_KEYS = {"answer", "answers", "correct", "correct_answer", "correct_options", "key",
                  "rubric", "explanation", "model_answer", "solution", "is_correct", "feedback"}
MIXED_TYPES = {"mcq", "short", "applied", "essay"}
CLOSED_TYPES = {"mcq", "multi", "tf"}
ALL_TYPES = MIXED_TYPES | CLOSED_TYPES
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "exam_template.html"


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def walk_for_forbidden(node, path="exam"):
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in FORBIDDEN_KEYS:
                fail(f"{path}.{k} looks like answer-key content. Keep the key in answer_key.json, not in the page data.")
            walk_for_forbidden(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_for_forbidden(v, f"{path}[{i}]")


def validate(exam):
    for field in ("title", "level", "format", "time_guide_min", "parts"):
        if field not in exam:
            fail(f"missing required field '{field}'")
    if exam["format"] not in ("mixed", "closed"):
        fail("format must be 'mixed' or 'closed'")
    allowed = CLOSED_TYPES if exam["format"] == "closed" else ALL_TYPES
    seen, total = set(), 0
    for part in exam["parts"]:
        if not part.get("title") or not part.get("questions"):
            fail("every part needs a title and at least one question")
        for q in part["questions"]:
            qid = q.get("id")
            if qid is None or qid in seen:
                fail(f"question id missing or duplicated: {qid!r}")
            seen.add(qid)
            if q.get("type") not in allowed:
                fail(f"question {qid}: type {q.get('type')!r} is not allowed in a {exam['format']} exam")
            if not q.get("text") or not isinstance(q.get("points"), (int, float)):
                fail(f"question {qid}: needs 'text' and numeric 'points'")
            if q["type"] in ("mcq", "multi"):
                want = 4 if q["type"] == "mcq" else 5
                opts = q.get("options") or {}
                if len(opts) != want:
                    fail(f"question {qid}: a {q['type']} question needs {want} options, found {len(opts)}")
            if q["type"] == "applied" and q.get("subparts"):
                labels = [sp.get("label") for sp in q["subparts"]]
                if None in labels or len(set(labels)) != len(labels):
                    fail(f"question {qid}: subparts need unique labels")
            total += q["points"]
    declared = exam.get("total_points")
    if declared is None:
        exam["total_points"] = total
    elif abs(declared - total) > 1e-9:
        fail(f"total_points is {declared} but the questions add up to {total}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam_json")
    ap.add_argument("out_html")
    ap.add_argument("--standalone", action="store_true",
                    help="wrap the page in a full HTML document (for opening as a local file)")
    args = ap.parse_args()

    exam = json.loads(Path(args.exam_json).read_text(encoding="utf-8"))
    walk_for_forbidden(exam)
    validate(exam)

    slug = re.sub(r"[^a-z0-9-]+", "-", str(exam.get("topic_slug") or exam["title"]).lower()).strip("-") or "exam"
    attempt = exam.get("attempt", 1)
    exam_id = exam.get("exam_id") or f"{exam.get('date', 'exam')}-{slug}-{int(attempt):02d}"
    exam["exam_id"] = re.sub(r"[^A-Za-z0-9-]+", "-", str(exam_id)).strip("-")
    exam.setdefault("topic_slug", slug)
    exam.setdefault("format_label", "Closed-form" if exam["format"] == "closed" else "Mixed")

    data = json.dumps(exam, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    html = TEMPLATE.read_text(encoding="utf-8")
    title = exam.get("page_title") or f"{exam.get('topic', exam['title'])} Exam"
    html = html.replace("__EXAM_TITLE__", re.sub(r"[<>&]", "", title)).replace("__EXAM_DATA__", data)

    if args.standalone:
        html = ('<!doctype html><html lang="%s"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                '</head><body>%s</body></html>') % (exam.get("language", "en"), html)
    Path(args.out_html).write_text(html, encoding="utf-8")
    n = sum(len(p["questions"]) for p in exam["parts"])
    print(f"Built {args.out_html}: {n} questions, {exam['total_points']} points, exam_id={exam['exam_id']}")


if __name__ == "__main__":
    main()

---
name: "knowledge-check"
description: "Use when the user wants to test what he or her learned from a source (PDF, web page, doc, slides, video transcript, notes) — builds a university-standard exam, grades it, and logs the result to the project to track progress. Also handles /knowledge-check help and progress."
---

# Knowledge Check — university-standard exam from a learning source

The user learns from many kinds of material and wants an honest, exam-grade check of what he actually retained. This skill runs the full cycle: **ingest the source → build an exam → The user answers → grade → save structured results → compare with earlier attempts**.

Also use this skill when the user only asks about his progress ("how am I doing on X?", "compare my last two tests") — in that case jump to §7.

## 0. Commands — check the arguments first

Look at the text passed with the skill (e.g. `/knowledge-check help`) before doing anything else:

| Invocation | What to do |
|---|---|
| `help`, `-h`, `--help`, `?`, or "how does this work / what is this for" | Show the help text below and stop. Don't read sources, ask questions or touch the log. |
| `progress` or `progress <topic>` | Go straight to §7. |
| Anything else (a file, a link, a topic, or nothing) | Normal flow from §1. With no source given, ask what he studied and how to share it. |

**Help text** — reply with this (in the language the user is writing in), filling in the log status line from a quick `project_read` of `claude/knowledge-checks.jsonl` if a project is attached (e.g. "3 tests saved across 2 topics"; skip the line if there's no project or no file):

```
KNOWLEDGE CHECK — test what you've really learned

What it does
Reads the material you studied, builds a university-standard exam on it,
grades your answers, and saves the result so you can track progress over time.

How to use it
1. Share what you studied: upload a PDF / Word / PowerPoint / image,
   paste a link or text, name a Google Drive file or project doc,
   or give a video transcript.
2. Confirm the settings (or just say "go"):
   • Level: Bachelor intro · Bachelor advanced (default) · Master
   • Length: Short ~30 min · Standard ~60 min (default) · Full ~90 min
3. Answer the whole exam in one reply, numbered by question ("1: B", "9: …").
   Closed book — hints are allowed but recorded.
4. Get your grade (% + German grade 1.0–5.0, pass at 50%), feedback per question
   with the model answer and where to re-read it, and study recommendations.

The exam
Multiple choice, short answers, applied cases and an essay, covering everything
from recall to analysis and critical evaluation. Retests avoid repeating
questions and can focus on your weak concepts.

Where results go
claude/knowledge-checks.jsonl in the current Claude Project — one record per
test. Keep tests on the same topic in the same project so they can be compared.

Commands
/knowledge-check                   start a new test
/knowledge-check <file|link>       start a test on that source
/knowledge-check progress          overview of all tested topics
/knowledge-check progress <topic>  history and trend for one topic
/knowledge-check help              show this help

<log status line>
```

## 1. Ingest the source

Read everything the user points to before writing any question. The exam may only test what the source teaches.

| Source | How to read it |
|---|---|
| PDF | `Read` with `pages` (≤20 pages per call; loop for longer docs). For scanned PDFs, use the `pdf` skill's OCR guidance. |
| Web page | `WebFetch`. If blocked, say so and ask the user to paste the text or upload a PDF — never work around the block. |
| Word / PowerPoint | `docx` / `pptx` skill extraction guidance. |
| Google Drive file | Google Drive `read_file_content`. |
| Project doc | `Projects` → `project_read`. |
| Video / podcast | Ask for the transcript (or a transcript URL); don't test from a title alone. |
| Images, handwritten notes | `Read` the image. |
| Pasted text | Use as is. |

Several sources together are fine — treat them as one syllabus.

Then build a private **content map** (write it to the scratchpad as `content_map.md`):

- 5–15 **learning objectives**, phrased as "the user can …" (e.g. "explain why X causes Y", "calculate Z from given data").
- Key **concepts**, each with a short slug (`crawl-budget`, `bayes-theorem`) and where it appears in the source (page, section, heading, timestamp). Slugs must stay the same across tests of the same topic, so reuse existing slugs from the log (§6) when the topic was tested before.
- A stable **topic slug** for the whole subject (e.g. `technical-seo-fundamentals`). Check the log for an existing slug first.

If the source is too thin for a meaningful exam (e.g. under ~1 page of substance), tell the user and suggest a short quiz or more material instead.

## 2. Confirm scope and settings (one short message)

Tell the user in 2–3 lines what you understood (topic, the main objectives), then confirm settings. Offer defaults so he can just say "go":

- **Level**: Bachelor introductory · Bachelor advanced (default) · Master
- **Length**: Short (~30 min, ~30 pts) · Standard (~60 min, ~60 pts, default) · Full (~90 min, ~90 pts)
- **Language**: same as the source unless the user asks otherwise
- **Focus** (only on retests): full coverage, or weighted toward the weak concepts from last time (default: ~50% weak concepts, the rest normal coverage)

Use `AskUserQuestion` when available.

## 3. Build the exam — university standards

Design it the way a careful university examiner would:

**Constructive alignment.** Every question maps to one learning objective and one concept. Every objective is covered by at least one question; heavier topics in the source get more points.

**Cognitive range (Bloom's taxonomy).** Target point distribution:

| Level | Intro | Advanced | Master |
|---|---|---|---|
| Remember / Understand | 45% | 30% | 15% |
| Apply / Analyze | 40% | 45% | 45% |
| Evaluate / Create | 15% | 25% | 40% |

**Mixed question types** (Standard length example: ~8 MCQ, ~4 short answer, ~2 applied problems/cases, 1 essay):

- *Multiple choice* — single best answer, 4 options, plausible distractors built from real misconceptions; no "all/none of the above", no giveaway grammar or length cues, answer position varied. 1–2 pts each.
- *Short answer* — 2–5 sentences; precise terminology expected. 3–5 pts.
- *Applied problem / case* — a new scenario not copied from the source, requiring the concepts to be used (calculation, diagnosis, design, decision). 6–10 pts, multi-part allowed.
- *Essay / critical discussion* — compare, evaluate, argue with justification. 10–15 pts.

**Quality rules.**
- Questions test understanding, not recall of trivial wording, page numbers, or author names — unless the author/date is itself central to the topic.
- Each question is unambiguous and answerable from the source (applied ones: from the source's concepts).
- No question gives away another question's answer.
- Retests: don't repeat previous questions verbatim (check `questions[].text` in the log); test the same concept with a new angle or scenario.

**Answer key first.** Before showing the exam, write to the scratchpad `answer_key.md`: for each question, the model answer, an analytic rubric (what earns each point, what earns partial credit), and the source reference. This keeps grading consistent and must not be shown to the user before he submits.

## 4. Present the exam (whole exam at once)

Format like a real exam paper:

```
EXAM — <Topic>
Level: <level> · Time guide: <n> min · Total: <n> points · Pass mark: 50%
Instructions: closed book; answer all questions; show your reasoning in problems;
reply with your answers numbered by question (e.g. "1: B", "9: …").

Part A — Multiple choice (<n> pts)
1. [2 pts] …
   A) …  B) …  C) …  D) …
Part B — Short answer (<n> pts)
…
Part C — Applied problems (<n> pts)
…
Part D — Essay (<n> pts)
…
```

For long exams, publish it as a doc or file only if the user asks; by default present it in the chat.

Exam integrity: while the exam is open, don't reveal answers or hint at them. If the user asks for a hint or a clarification, clarify the *question's wording* only, and note in the record that a hint was given. If he stops midway, grade what he submitted and mark unanswered questions as 0 with `"answered": false`.

## 5. Grade and give feedback

Grade strictly against `answer_key.md` — same rigor a university examiner would use: credit correct substance even if phrased differently, give partial credit per the rubric, deduct for factual errors even inside an otherwise good answer, and don't reward length.

**Grade scale.** Report percentage plus German university grade:

| % | ≥95 | ≥90 | ≥85 | ≥80 | ≥75 | ≥70 | ≥65 | ≥60 | ≥55 | ≥50 | <50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grade | 1.0 | 1.3 | 1.7 | 2.0 | 2.3 | 2.7 | 3.0 | 3.3 | 3.7 | 4.0 | 5.0 (fail) |

**Feedback report** (in the chat):

1. Headline: points, %, grade, pass/fail, and — if there's a previous attempt on this topic — the change (e.g. "+12 pts vs 2026-09-02").
2. Per-question table: #, points earned/possible, short verdict.
3. For every question not fully correct: what was missing or wrong, the model answer (condensed), and the source reference so the user can re-read it.
4. Mastery by concept and by Bloom level (where he's solid, where he isn't).
5. 3–5 concrete study recommendations tied to specific source sections, plus a suggested retest date (≈3–7 days for weak areas).

Be honest and specific; a 2.7 is a 2.7.

## 6. Save the result as structured data

Results live in the **attached Claude Project** as `claude/knowledge-checks.jsonl` — one JSON object per line, one line per exam.

1. `project_read` the file fresh (it may not exist yet — then start empty). If no project is attached to the session, tell the user and offer the record as a downloadable `.json` file instead.
2. Parse it with Python (`json.loads` per line) in the scratchpad; never edit it by hand.
3. Append the new record, validate that every line parses, and `project_write` the **whole** file back to the same path (the write replaces it).
4. Confirm in one line that the result was saved.

Record schema (`schema_version: 1`):

```json
{
  "schema_version": 1,
  "test_id": "2026-09-23-technical-seo-fundamentals-01",
  "date": "2026-09-23",
  "topic": "Technical SEO fundamentals",
  "topic_slug": "technical-seo-fundamentals",
  "attempt_number": 1,
  "previous_test_id": null,
  "sources": [
    {"type": "pdf", "title": "SEO Starter Guide", "locator": "SEO_Guide.pdf, pp. 1-42"},
    {"type": "web", "title": "Crawl budget explained", "locator": "https://…"}
  ],
  "settings": {"level": "bachelor_advanced", "length": "standard", "language": "en", "focus": "full"},
  "score": {"points_earned": 44.5, "points_possible": 60, "percent": 74.2, "grade_de": 2.7, "passed": true},
  "by_bloom": {
    "remember_understand": {"earned": 16, "possible": 18},
    "apply_analyze": {"earned": 20, "possible": 27},
    "evaluate_create": {"earned": 8.5, "possible": 15}
  },
  "by_concept": [
    {"concept": "crawl-budget", "objective": "Explain what limits crawl budget", "earned": 4, "possible": 7, "mastery": "partial"}
  ],
  "questions": [
    {
      "id": 1,
      "type": "mcq",
      "bloom": "understand",
      "concept": "crawl-budget",
      "text": "Which factor most directly reduces …?",
      "points_possible": 2,
      "points_earned": 2,
      "answered": true,
      "result": "correct",
      "feedback": "",
      "source_ref": "p. 12"
    }
  ],
  "hints_used": 0,
  "strengths": ["…"],
  "gaps": ["…"],
  "recommendations": ["Re-read pp. 12-15 on …"],
  "next_review": "2026-09-28"
}
```

Field rules: `result` ∈ `correct | partial | incorrect | unanswered`; `mastery` ∈ `strong` (≥80%) `| partial` (50–79%) `| weak` (<50%); `level` ∈ `bachelor_intro | bachelor_advanced | master`; `attempt_number` counts prior records with the same `topic_slug` + 1; `previous_test_id` is the latest earlier record with that slug. Store the question text (for no-repeat checks) but not the user's full answer text — a one-line gist in `feedback` is enough.

## 7. Progress and comparisons

When a topic has earlier attempts, or the user asks about progress:

- Load the log (§6 steps 1–2) and filter by `topic_slug` (or list all topics if he asks generally).
- Show a compact table: date, level, %, grade, and the concepts that moved (weak → strong, or regressions).
- Only compare like with like: flag when levels or source sets differ between attempts, because the scores aren't directly comparable.
- If a `next_review` date has passed for a topic, mention it when the user asks what to review.
- For 3+ attempts on a topic, offer a small chart (use the `dataviz` skill) of % over time and per-concept mastery.
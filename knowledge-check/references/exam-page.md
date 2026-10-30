# Interactive exam page — reference

Read this when you reach §4 (present the exam) or §4b (collect the answers) of SKILL.md.
It covers the exam data file, the build and publish steps, the answers payload, and the fallbacks.

## Why the page works this way

the user answers on a web page instead of typing "1: B, 9: …" into the chat. The page shows the
questions, takes the answers with proper inputs, keeps a clock, and hands the answers back as data.
Claude still does all the grading, because open questions need judgement and because the answer
key must never be inside the page. The page is published, so anyone who can open it can read its
source, and so can the user while the exam is running.

That gives one hard rule: **the page data holds questions only.** The answer key, rubrics and
explanations stay in the scratchpad (`answer_key.md`, `answer_key.json`). `build_exam_page.py`
refuses to build when the exam file contains fields such as `correct`, `answer`, `rubric`,
`explanation`, so a slip cannot leak the key.

## exam.json

Write it to the scratchpad. All text fields accept a small subset of Markdown: `**bold**`,
`` `code` ``, blank-line paragraphs, `- ` bullet lists and ``` fenced code blocks. No math
typesetting: write formulas in plain text or Unicode (x², √, ≥).

```json
{
  "title": "Technical SEO Fundamentals",
  "topic": "Technical SEO fundamentals",
  "topic_slug": "technical-seo-fundamentals",
  "date": "2026-10-30",
  "attempt": 1,
  "level": "Bachelor advanced",
  "format": "mixed",
  "time_guide_min": 60,
  "pass_mark_percent": 50,
  "language": "en",
  "instructions": "Closed book. Answer all questions. Show your reasoning in problems.",
  "parts": [
    {
      "title": "Part A — Multiple choice",
      "instructions": "One correct answer per question.",
      "questions": [
        {"id": 1, "type": "mcq", "points": 2, "context": "optional scenario text",
         "text": "Question stem",
         "options": {"A": "…", "B": "…", "C": "…", "D": "…"}}
      ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `format` | `mixed` or `closed`. Decides which question types the builder accepts. |
| `exam_id` | Optional. Default is `<date>-<topic_slug>-<attempt, 2 digits>`; this is also the database document id, so it must stay unique per attempt. |
| `total_points` | Optional. The builder sums the questions; if you give a total that disagrees, the build fails. |
| `ui` | Optional object that overrides the page's interface texts (see below) for a non-English exam. |
| `page_title` | Optional. Default `<topic> Exam`. |

Question types and their fields:

| `type` | Used in | Fields |
|---|---|---|
| `mcq` | both | `options` with exactly 4 keys (A–D) |
| `multi` | closed | `options` with exactly 5 keys (A–E); the stem says "select all that apply" |
| `tf` | closed | none beyond `text` |
| `short` | mixed | optional `lines` (textarea height, default 5) |
| `applied` | mixed | optional `subparts`: `[{"label": "a", "text": "…", "points": 3, "lines": 6}]`; without subparts it is one text box |
| `essay` | mixed | optional `lines` (default 16) |

Ids are unique integers in the order the user sees them. For an `applied` question with subparts the
answer keys are `"<id><label>"`, for example `"3a"` and `"3b"`.

### Interface texts for other languages

The page's own labels (buttons, hints, the clock) are English by default. When the exam is in
another language, add a `ui` object with the same keys translated. Missing keys fall back to
English. Keys: `kicker, level, format, time, points, pass, minutes, pts, pt, answered, map,
closeMap, mapKey, flag, clear, words, mcq, multi, tf, short, applied, essay, t, f, placeholder,
submitTitle, submitHint, reviewBtn, reviewTitle, allAnswered, unanswered, flagged, unansweredWarn,
note, submit, back, doneTitle, savedOk, savedFail, copy, copied, copyFail, save, payloadSummary,
overtime`.

## Build and publish

```bash
python3 scripts/build_exam_page.py exam.json exam_page.html
```

This produces the page content in the form the Artifact tool wants (no `<html>` wrapper).

1. Load the `artifact-capabilities` skill if you have not in this session; the page uses `db` and
   `downloads`.
2. Publish `exam_page.html` with the Artifact tool, declaring
   `capabilities: {db: {}, downloads: true}`. Pass a short generic `icon` such as `"quiz"` and a
   one-sentence `description`. The `<title>` is already set by the builder.
3. Tell the user in one or two lines what to do: open the page, take the exam, press **Submit**, then
   come back and say he is done. Do not paste the link; the card in the conversation carries it.
4. Do not preview or tweak the page after publishing; the template is already checked. Keep the
   artifact `url`, since reading the submission needs it. The one check for a page with capabilities
   is a single `list` of `submissions` through `ArtifactData`, which is expected to be empty; the
   submit write can only be exercised when the user presses Submit. Only re-publish if he reports
   something broken.

If no Artifact tool is available (for example in a terminal session), build with `--standalone`,
write the file next to the project files, and tell the user to open it in his browser. The page then
has no database, so after submitting he copies the answers text and pastes it into the chat.

If the page cannot be used at all, fall back to the chat layout in SKILL.md §4.

## What the page does

- Questions in one column, grouped by part, with real inputs: radio buttons, checkboxes,
  True/False buttons, text areas with a word count.
- A clock that starts with the first answer and counts up against the time guide. It is a guide,
  not a cut-off: the page never closes the exam by itself, and the payload records the elapsed time.
- A progress bar and a question map; any question can be flagged to revisit.
- Drafts are kept in the browser, so a reload does not lose answers.
- A review step before submitting lists unanswered and flagged questions and has an optional note
  field for the examiner (this replaces "asking for a hint": clarifications of question wording
  still happen in the chat).
- After **Submit** the inputs lock and the page writes the answers to its database at
  `submissions/<exam_id>`. If that fails, it says so and shows the answers as text to copy.
- It never shows scores, correct answers or feedback. Claude gives those in the chat (§5).

## The answers payload

```json
{
  "exam_id": "2026-10-30-technical-seo-fundamentals-01",
  "topic_slug": "technical-seo-fundamentals",
  "submitted_at": "2026-10-30T10:41:07.000Z",
  "elapsed_seconds": 3412,
  "time_guide_minutes": 60,
  "answers": {"1": "B", "4": ["A", "D"], "6": "T", "9": "free text…", "12a": "…", "12b": "…"},
  "unanswered": [3, 5],
  "flagged": [3],
  "note": "Q2 wording unclear"
}
```

- `mcq` is a letter, `multi` a sorted list of letters, `tf` is `"T"` or `"F"`, open types are text.
- A question that was not answered is absent from `answers` and listed in `unanswered`.

Where to read it from, in this order:

1. The page database: `ArtifactData` with the exam artifact's `url` (from the publish result), action
   `get`, collection `submissions`, document `exam_id` (load the tool with ToolSearch if it is not
   loaded). The payload is under the `payload` field.
2. A JSON text the user pasted into the chat (the page's "Show the answers as text" box) or a saved
   `answers-<exam_id>.json` file.
3. Answers typed in the chat in the old format ("1: B", "15: A, C", "27: T"); accept them as before.

If the document does not exist yet, the user has probably not pressed Submit. Ask him to submit
rather than grading a half-finished exam.

## Grading helpers

`scripts/grade_closed.py answer_key.json submission.json` scores `mcq`, `multi` and `tf` with the
exact rules of §5 and lists the open questions it did not score. The key file looks like:

```json
{"1": {"type": "mcq", "points": 2, "correct": "B"},
 "4": {"type": "multi", "points": 3, "correct": ["A", "C"]},
 "6": {"type": "tf", "points": 1, "correct": "T"},
 "9": {"type": "short", "points": 4}}
```

It accepts the payload itself or the database document that wraps it. For a Closed-form exam its
output already contains percent, German grade and pass/fail; for a Mixed exam, grade the open
questions by rubric, add their points to `closed_points_earned`, and compute the total yourself in
Python.

---
name: codex-visual-handoff
description: Division of labor for users who run both Claude and OpenAI Codex. Use whenever a task produces user-facing visuals — images, video frames, slide decks, rendered pages, thumbnails, covers, motion graphics. Claude owns facts, copy, approval flow, and substance QA; Codex owns everything visual, including writing the image/video prompts. Use this skill when the user asks to "make a reel/thumbnail/cover/deck", when a pipeline mixes text and rendered assets, or when deciding which model should handle a generation step.
---

# Codex Visual Handoff

One rule, strictly kept: **every rendered visual is Codex's job — including the prompt.**

## Why the prompt line matters

The tempting failure mode is "Claude writes a detailed image prompt, Codex just runs it."
Don't. A prompt is where visual judgment happens — composition, restraint, what to leave
out. If the orchestrator writes it, the output's visual ceiling is the orchestrator's, and
the bill arrives later: the render fails human taste review, gets rejected, and the whole
piece is remade. In a print-pipeline audit of 52 revision rounds, taste rejections were the
single largest rework cause (13 rounds, 9 of them repeats) — and every one arrived *after*
all mechanical checks had passed.

Hand the judgment to the model that's better at it, whole.

## The split

| Step | Owner | Notes |
|---|---|---|
| Facts, numbers, sources | **Claude** | Open the real data/code; never invent |
| Exact copy (user-facing text) | **Claude** | Read it aloud; would a person say this? |
| Image/video **prompt writing** | **Codex** | Claude never drafts it "to help" |
| Asset choice, composition, layout | **Codex** | |
| Rendering, motion, sound mux | **Codex** | |
| Approval flow, lineage hashes | **Claude** | Approved copy hash must match render input |
| Substance QA (facts, copy, gating) | **Claude** | Aesthetic QA goes to an independent reviewer |

## The handoff brief

Claude passes a **requirements brief**, never a design:

- The approved exact copy (verbatim, hashed)
- Facts and figures with sources
- Hard prohibitions (rights-unsafe assets, banned claims, brand invariants)
- Required disclosures
- The role of each deliverable (hook frame / evidence frame / CTA frame)

What the brief must NOT contain: image prompts, palette picks, composition sketches,
"maybe put X on the right". If you catch yourself describing pixels, you're doing
Codex's job with Claude's eyes.

## Rejection routing

- Copy is wrong or awkward → back to Claude.
- Visuals are rejected (alignment, clutter, taste) → **back to Codex.** Claude does not
  hot-patch a rendered asset; a local fix by the wrong model becomes the next rejection.
- Same cause rejected twice → stop adjusting at this level; go up one (copy or structure),
  or ask the user one interpretation question. Repeated-cause rounds were over half of all
  rework in the audit above.

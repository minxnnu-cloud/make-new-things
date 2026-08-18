---
name: rework-budget
description: Stop revision loops from eating the project. Use when a deliverable keeps cycling through revision rounds (r1, r2, ... r10+), when the same kind of defect keeps coming back, when every fix seems to trigger a full rebuild and re-audit, or when workspace documents are ballooning with receipts and re-audits. Encodes round budgets, minimal-successor rounds, escalation ladders, and identity gates mined from a 52-round revision-history audit.
---

# Rework Budget

Rules for pipelines where an artifact is built, reviewed, rejected, and rebuilt.
All of them were mined from a 52-round revision audit of a real production pipeline;
over half of all rounds were **repeats of a cause that had already appeared**.

## 1. Minimal successor — close open defects only

A successor round closes the previous round's open defects and does nothing else.
Everything unchanged is inherited by exact reference (path + hash), not regenerated,
not re-audited. The audit's cleanest rounds were labeled "minimal successor: closed 2/2
open defects"; the messiest regenerated a 90-page artifact to change two pages.

Specs revise the same way: as a **delta contract** naming which clauses it supersedes —
never a full rewrite. One full rejection triggered a 703KB spec rewrite; the delta that
actually mattered fit in a page.

## 2. Same cause twice = escalate

When the same cause category rejects a round twice, stop adjusting at that level and go up:

- render tweaks repeating → the spec is wrong, fix the spec
- spec fixes repeating → the direction is wrong, re-lock direction with the user
- direction flapping → you're guessing; ask the user one interpretation question

A third attempt at the same level was almost always waste in the audit.

## 3. A human rejection becomes a machine gate — same round

Mechanical checklists catch what's *wrong* (fonts, breaks, colors). They cannot catch
what's *lacking* — emptiness, density collapse, lost identity, underfill. Those arrive as
human rejections. The only way the next deliverable doesn't pay the same human round:
convert every human rejection into a quantitative gate (a number, a classifier, a grep)
and append it to the checklist **in the round where it happened**.

## 4. Identity gates — machine-check at build time

Three defect families that each burned multiple rounds, all machine-detectable:

- **Stale identity.** Artifact metadata (PDF Document Info, XMP — *including orphan
  objects via raw scan*) must match the current course/revision; zero tokens from other
  courses or past revisions. A fix that cut the catalog reference but left the raw string
  got re-rejected one round later.
- **Exact requirements.** The user's exact copy and contract numbers (minimum font sizes,
  required notices) live in a machine-comparable list, checked at build. Four audit
  findings in one round were all trivially automatable.
- **Single canonical mapping.** When two frozen inputs can disagree (a TOC's page numbers
  vs. rendered folios), name one canonical source in the binding input and machine-compare
  the other against it. Two "frozen" canons that silently disagreed cost an entire
  90-page candidate.

## 5. Lock only what deserves locking

Hash-lock tables belong on **frozen canonical inputs** — not on every document. In the
audited workspace the receipt ritual had spread to 130 of 148 documents (2.79M characters
total). When everything is locked, locks stop being signal.

# make-new-things

**Claude와 ChatGPT, 둘 다 구독하고 있다면 — 두 모델의 장점을 하나의 파이프라인으로.**

*For people who subscribe to both Claude and ChatGPT: division-of-labor skills that hand
each model what it does best, and the loop-control rules that stop revision rounds from
eating your project.*

## Why this exists

We surveyed the Claude Skills ecosystem before building this: **8,419 repos, 233,455
SKILL.md files, 155,219 distinct skills** after deduplication (full methodology and data
pipeline in [`survey/`](survey/)). Two findings shaped this pack:

1. **There are no empty categories left.** 91% of explicit "is there a skill for X" requests
   already have a matching skill. Coverage is solved; *quality* isn't — 44–94% of every
   category's supply comes from bulk-generated collections.
2. **Cross-model division of labor is the thin spot.** General Codex tooling: 635 authors.
   Pipelines that split roles between two models: **51 authors.**

So this pack doesn't add another wrapper. It encodes working patterns from a production
dual-model pipeline — every rule backed by a 52-round revision-history audit of real
rework, with the numbers kept in the skill text.

## The skills

| Skill | One line |
|---|---|
| [`codex-visual-handoff`](plugins/make-new-things/skills/codex-visual-handoff/) | Every rendered visual is Codex's job — **including the prompt**. Claude owns facts, copy, approvals |
| [`styleframe-first`](plugins/make-new-things/skills/styleframe-first/) | Approve 3–7 representative frames before any full render. Full-render cost drops from *per rejection* to *once per direction* |
| [`rework-budget`](plugins/make-new-things/skills/rework-budget/) | Minimal-successor rounds, same-cause-twice escalation, human rejections converted to machine gates |
| [`dual-tree-sync`](plugins/make-new-things/skills/dual-tree-sync/) | Keep `.claude/skills` and `.agents/skills` from silently forking. Ships the sync hook (PowerShell + bash) |

## Install

**Claude Code (marketplace):**

```bash
/plugin marketplace add minxnnu-cloud/make-new-things
/plugin install make-new-things
```

**Skills CLI:**

```bash
npx skills add minxnnu-cloud/make-new-things
```

Or copy any skill directory into your project's `.claude/skills/`.

## Where the numbers come from

The evidence lines inside each skill ("52 rounds", "13 taste rejections, 9 repeated",
"5 design rounds burned on a question asked too late") come from auditing a real
print-publication pipeline: 168 workspace revision documents, 2.79M characters, every
round-to-round transition classified by cause. The patterns that survived are the ones
that measurably deleted rounds.

## License

MIT

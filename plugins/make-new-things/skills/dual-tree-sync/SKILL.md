---
name: dual-tree-sync
description: Keep Claude Code and Codex skill trees from drifting apart. Use when a project maintains skills for both runtimes (.claude/skills for Claude Code, .agents/skills or .codex for Codex/other agents), when the two copies of a skill disagree, when an agent seems to follow outdated rules that were already fixed "somewhere", or when setting up a dual-runtime project. Ships a sync hook with per-tree token substitution and an intentional-exception list.
---

# Dual Tree Sync

Projects that run both Claude Code and Codex end up with two skill trees:
`.claude/skills/**` (what Claude Code loads) and `.agents/skills/**` (what Codex loads).
Edit them independently and they fork — silently.

## Why this is worse than it sounds

In one audited project, 6 of 7 shared skills had drifted — **in both directions**.
Claude Code was following an approval channel retired a month earlier; a direction-lock
phase existed only in the tree that didn't execute it; one skill's two copies shared *zero*
sections — a philosophy fork where one tree required human approval before rendering and
the other rendered first and asked later. Every one of those produced work that was later
rejected and redone. The drift didn't look like a bug; it looked like agents being bad at
their jobs.

## The model

1. **One tree is the editing source.** Pick it (say `.agents/skills`). The other is a mirror.
2. **A PostToolUse hook mirrors on every edit.** Write/Edit under the source tree → copy to
   the mirror. Editing the mirror directly → warn and point at the source.
3. **Per-tree tokens survive the mirror.** Some values *should* differ per tree — each tree
   names its own executor (`subagent_type:"Codex"` vs `"claude"`), its own loading file
   (`AGENTS.md` vs `CLAUDE.md`). These are substitution rules, applied on copy.
4. **Intentional exceptions are listed, not implied.** A skill whose two copies are
   deliberately different documents (e.g. producer-side vs orchestrator-side of the same
   pipeline) goes in an exclusion list, and the hook leaves it alone.

## Setup

Copy `scripts/skills-sync.ps1` (Windows) or `scripts/skills-sync.sh` (POSIX) into your
project's hook directory, edit `skills-sync.rules.json` next to it, and register:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{ "type": "command",
                  "command": "powershell -NoProfile -File \"$env:CLAUDE_PROJECT_DIR/hooks/skills-sync.ps1\"",
                  "timeout": 10 }]
    }]
  }
}
```

`skills-sync.rules.json`:

```json
{
  "excluded": ["my-producer-skill"],
  "perTree": [
    { "from": "subagent_type:\"Codex\"", "to": "subagent_type:\"claude\"" }
  ]
}
```

## Hard-won details (read before editing the scripts)

- **Rules live in a UTF-8 JSON sidecar, not in the .ps1.** Windows PowerShell 5.1 reads a
  BOM-less `.ps1` as ANSI; non-ASCII replacement literals get mangled and the rule silently
  never fires. This exact bug shipped in the first version of this hook.
- **Write the mirror without a BOM** (`UTF8Encoding($false)`), or every synced file grows a
  phantom first-line diff forever.
- **Keep substitution tokens exact and narrow.** A blanket `.agents/ → .claude/` rewrite
  will corrupt skills that name the other tree *on purpose* (e.g. "production canon lives
  in `.agents/skills/**`").
- **Fail open.** A sync failure must never block the user's edit.

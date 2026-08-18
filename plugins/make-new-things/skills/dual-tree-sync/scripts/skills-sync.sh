#!/usr/bin/env bash
# PostToolUse: keep .claude/skills in sync with .agents/skills (single source).
# POSIX counterpart of skills-sync.ps1 -- same contract, same rules sidecar.
# Requires: jq. Fail open: a sync failure must never block the user's edit.

set -u
payload=$(cat) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty') || exit 0
case "$tool" in Write|Edit|MultiEdit) ;; *) exit 0 ;; esac

path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')
[ -n "$path" ] || exit 0
root=${CLAUDE_PROJECT_DIR:-}
[ -n "$root" ] || exit 0

rules="$root/hooks/skills-sync.rules.json"
excluded=""
if [ -f "$rules" ]; then
  excluded=$(jq -r '.excluded[]?' "$rules" 2>/dev/null)
fi

is_excluded() {
  printf '%s\n' "$excluded" | grep -qx "$1"
}

norm=$(printf '%s' "$path" | tr '\\' '/')

# Editing the mirror directly is the drift we are trying to prevent.
if printf '%s' "$norm" | grep -q '/\.claude/skills/'; then
  name=$(printf '%s' "$norm" | sed -n 's|.*/\.claude/skills/\([^/]*\)/.*|\1|p')
  if [ -n "$name" ] && ! is_excluded "$name"; then
    printf '{"systemMessage":"[skills-sync] .claude/skills/%s is a mirror. Edit .agents/skills/%s instead."}\n' "$name" "$name"
  fi
  exit 0
fi

printf '%s' "$norm" | grep -q '/\.agents/skills/' || exit 0
name=$(printf '%s' "$norm" | sed -n 's|.*/\.agents/skills/\([^/]*\)/.*|\1|p')
[ -n "$name" ] || exit 0
is_excluded "$name" && exit 0

src="$root/.agents/skills/$name"
dst="$root/.claude/skills/$name"
[ -d "$src" ] || exit 0
[ -d "$dst" ] || exit 0   # skill not published to Claude Code; leave alone

copied=0
while IFS= read -r f; do
  rel=${f#"$src"/}
  target="$dst/$rel"
  mkdir -p "$(dirname "$target")" 2>/dev/null || continue
  case "$f" in
    *.md|*.json|*.txt|*.yaml|*.yml)
      tmp=$(mktemp) || continue
      cp "$f" "$tmp"
      # apply per-tree substitutions from the sidecar
      if [ -f "$rules" ]; then
        n=$(jq '.perTree | length' "$rules" 2>/dev/null || echo 0)
        i=0
        while [ "$i" -lt "$n" ]; do
          from=$(jq -r ".perTree[$i].from" "$rules")
          to=$(jq -r ".perTree[$i].to" "$rules")
          # literal fixed-string replacement via python if available, else sed-escape
          if command -v python3 >/dev/null 2>&1; then
            python3 - "$tmp" "$from" "$to" <<'PY'
import io, sys
p, f, t = sys.argv[1], sys.argv[2], sys.argv[3]
s = io.open(p, encoding="utf-8").read()
io.open(p, "w", encoding="utf-8", newline="").write(s.replace(f, t))
PY
          fi
          i=$((i + 1))
        done
      fi
      if ! cmp -s "$tmp" "$target" 2>/dev/null; then
        cp "$tmp" "$target" && copied=$((copied + 1))
      fi
      rm -f "$tmp"
      ;;
    *)
      if ! cmp -s "$f" "$target" 2>/dev/null; then
        cp "$f" "$target" && copied=$((copied + 1))
      fi
      ;;
  esac
done <<EOF
$(find "$src" -type f)
EOF

if [ "$copied" -gt 0 ]; then
  printf '{"systemMessage":"[skills-sync] %s : .agents -> .claude (%s file(s) mirrored)"}\n' "$name" "$copied"
fi
exit 0

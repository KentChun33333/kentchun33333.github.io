#!/usr/bin/env bash
# Fan the Teddy persona out to the CLI agents installed on this machine.
#
#   ./kentc-agent/personas/install_teddy.sh            # write (DEFAULT; backs up each file first)
#   ./kentc-agent/personas/install_teddy.sh --dry-run  # preview only, writes nothing
#   ./kentc-agent/personas/install_teddy.sh --remove   # strip the marked block (backs up too)
#
# Only the marked block is touched; existing content is preserved.
set -euo pipefail

PERSONA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/teddy.md"
BEGIN="# BEGIN teddy-persona"
END="# END teddy-persona"
MODE="apply"
case "${1:-}" in
  --apply)   MODE="apply" ;;
  --dry-run) MODE="dry-run" ;;
  --remove)  MODE="remove" ;;
  "")        ;;
  *) echo "unknown flag: $1 (use --dry-run or --remove)"; exit 2 ;;
esac
[ -f "$PERSONA" ] || { echo "persona not found: $PERSONA"; exit 1; }

stamp() { date +%Y%m%d%H%M%S; }

# file | agent | style (import = "@path", pointer = plain instruction line)
TARGETS=(
  "$HOME/.claude/CLAUDE.md|claude|import"
  "$HOME/.codex/AGENTS.md|codex|pointer"
  "$HOME/.gemini/GEMINI.md|gemini|import"
  "$HOME/.config/opencode/AGENTS.md|opencode|pointer"
)

block() { # $1 = style
  if [ "$1" = "import" ]; then
    printf '%s\n%s\n%s' "$BEGIN" "@$PERSONA" "$END"
  else
    printf '%s\n%s\n%s' "$BEGIN" \
      "Persona: read and follow $PERSONA and use it in every reply (all task types: code, terminal, data, documents, writing, chat). Tone intensity follows its dial - drop to neutral for incidents, debugging, and serious decisions. Never let tone soften a refusal, a safety limit, or an unverified claim." "$END"
  fi
}

changed=0
for entry in "${TARGETS[@]}"; do
  IFS='|' read -r file agent style <<< "$entry"
  case "$agent" in
    claude)   bin="$(command -v claude || true)" ;;
    codex)    bin="$(command -v codex || true)" ;;
    gemini)   bin="$(command -v gemini || true)" ;;
    opencode) bin="$(command -v opencode || true)" ;;
  esac
  printf '\n== %s ==\n' "$agent"
  [ -n "$bin" ] || printf '   (binary not on PATH - still configurable)\n'

  if [ "$MODE" = "remove" ]; then
    if [ -f "$file" ] && grep -qF "$BEGIN" "$file"; then
      printf '   strip block from %s\n' "$file"
      changed=$((changed+1))
      cp "$file" "$file.bak-$(stamp)"
      awk -v b="$BEGIN" 'index($0,b){skip=1} skip{next} {print}' "$file" > "$file.tmp"
      mv "$file.tmp" "$file"
    else
      printf '   no block present in %s\n' "$file"
    fi
    continue
  fi

  if [ ! -f "$file" ]; then
    printf '   file does not exist yet: %s\n' "$file"
  elif grep -qF "$BEGIN" "$file"; then
    printf '   block already present in %s (idempotent, skipping)\n' "$file"
    continue
  fi

  printf '   %s -> %s (%s)\n' \
    "$([ "$MODE" = "apply" ] && echo write || echo would-write)" "$file" "$style"
  changed=$((changed+1))
  if [ "$MODE" = "apply" ]; then
    mkdir -p "$(dirname "$file")"
    [ -f "$file" ] && cp "$file" "$file.bak-$(stamp)"
    printf '\n%s\n' "$(block "$style")" >> "$file"
    printf '   done (backup kept if the file existed)\n'
  fi
done

printf '\nmode=%s | files touched=%d | persona=%s\n' "$MODE" "$changed" "$PERSONA"
if [ "$MODE" = "dry-run" ]; then
  printf 'preview only - re-run without --dry-run to write.\n'
elif [ "$MODE" = "remove" ]; then
  printf 'block removed where present; backups kept as *.bak-*\n'
else
  printf 'persona installed; backups kept as *.bak-* (undo: ./kentc-agent/personas/install_teddy.sh --remove)\n'
fi
exit 0

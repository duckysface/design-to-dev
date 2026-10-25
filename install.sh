#!/usr/bin/env sh
# design-to-dev — installation sans npm ni clone.
#   curl -fsSL https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.sh | sh
#   curl -fsSL .../install.sh | sh -s -- --codex        (--claude, --codex, --all ; défaut : les deux)
# Avec Node 18+, délègue à bin/cli.js ; sinon copie la skill directement.
set -eu

REPO="duckysface/design-to-dev"
REF="${DESIGN_TO_DEV_REF:-main}"
NAME="design-to-dev"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM

echo "Téléchargement de $REPO ($REF)…"
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$REF" | tar -xz -C "$tmp"
src="$tmp/$NAME-$REF"
[ -f "$src/SKILL.md" ] || { echo "Archive inattendue : SKILL.md introuvable." >&2; exit 1; }

if command -v node >/dev/null 2>&1 && node -e 'process.exit(+process.versions.node.split(".")[0] < 18)'; then
  [ $# -gt 0 ] || set -- --all
  # stdin est le script lui-même quand on passe par un pipe : pas de question interactive
  exec node "$src/bin/cli.js" install -y "$@" </dev/null
fi

agents=""
for a in "$@"; do
  case "$a" in
    --claude) agents="$agents claude" ;;
    --codex) agents="$agents codex" ;;
    --all) agents="claude codex" ;;
    *) echo "Option inconnue : $a" >&2; exit 1 ;;
  esac
done
[ -n "$agents" ] || agents="claude codex"

for agent in $agents; do
  case "$agent" in
    claude) dst="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/$NAME" ;;
    codex) dst="$HOME/.agents/skills/$NAME" ;;
  esac
  if [ -e "$dst" ] && ! grep -qx "name: $NAME" "$dst/SKILL.md" 2>/dev/null; then
    echo "$dst existe et ne contient pas $NAME : ignoré." >&2
    continue
  fi
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst.tmp" && mkdir "$dst.tmp"
  for item in SKILL.md LICENSE README.md scripts references templates; do
    [ -e "$src/$item" ] && cp -R "$src/$item" "$dst.tmp/"
  done
  find "$dst.tmp" -name __pycache__ -type d -prune -exec rm -rf {} +
  echo "$REF" > "$dst.tmp/.version"
  rm -rf "$dst" && mv "$dst.tmp" "$dst"
  echo "  ✓ $agent : $dst"
done

command -v python3 >/dev/null 2>&1 || echo "⚠ Python 3.9+ introuvable : l'installer avant d'utiliser la skill."
echo "Redémarrer l'agent. Claude Code : /design-to-dev <dossier> — Codex : \$design-to-dev <dossier>"

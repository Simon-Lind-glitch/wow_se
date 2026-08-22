#!/usr/bin/env bash
# Runs once after the container is created. Idempotent — safe to re-run.
set -euo pipefail

echo "==> toolchain versions"
python --version
lua5.1 -v
luacheck --version
stylua --version
printf 'anthropic  %s\n' "$(python -c 'import anthropic; print(anthropic.__version__)')"

echo
echo "==> scaffolding directories (spec §4)"
# Build-time only, never shipped.
mkdir -p tools/{extract,translate,emit,cache,lua}
# The addon. This tree is what gets copied into Interface/AddOns.
mkdir -p addon/WoWsvSE/{hooks,locale,data,devtools}

# Keep empty dirs tracked so a clean checkout has the same shape.
for d in tools/cache addon/WoWsvSE/locale addon/WoWsvSE/data; do
  [ -e "$d/.gitkeep" ] || touch "$d/.gitkeep"
done

echo
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "==> ANTHROPIC_API_KEY: present"
else
  cat <<'MSG'
==> ANTHROPIC_API_KEY: NOT SET
    The extract/emit stages and all tests run without it. Only the translate
    stage needs it. To set it, export it on the HOST and rebuild the container:
      export ANTHROPIC_API_KEY=sk-ant-...
MSG
fi

echo
echo "==> plugins"
# .claude/settings.json (committed) DECLARES the marketplace and enables the
# plugin, but the marketplace clone lives in $HOME/.claude/plugins, which is
# container-local. The project-scope install record is also keyed to an absolute
# projectPath, and that path differs here from the host. So materialize both.
# All of this is public-repo git cloning — no credentials needed.
if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add Simon-Lind-glitch/ai-skills --scope project 2>/dev/null \
    || claude plugin marketplace update ai-skills 2>/dev/null \
    || echo "    (marketplace already present, or offline)"
  claude plugin install ai-skills@ai-skills --scope project -y 2>/dev/null \
    || echo "    (ai-skills already installed, or offline)"
  claude plugin list 2>/dev/null | sed 's/^/    /' || true
else
  echo "    claude CLI not on PATH — skipping plugin warmup"
fi

echo
echo "==> ready. 'make help' lists the build targets."
echo "    Run 'claude' and log in once; the ~/.claude volume persists it."

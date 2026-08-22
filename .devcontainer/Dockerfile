# Build-time toolchain image. Nothing in here ships to the game client.
#
# Two runtimes on purpose:
#   Python 3.12 — orchestration, Anthropic batch API, hashing, YAML glossary
#   Lua 5.1     — the SAME VM version WoW runs. Used to (a) load Questie's DB
#                 and GlobalStrings.lua as data instead of regex-parsing them,
#                 and (b) unit-test the addon's masking / round-trip logic.
ARG PYTHON_VARIANT=3.12-bookworm
FROM mcr.microsoft.com/devcontainers/python:${PYTHON_VARIANT}

ENV DEBIAN_FRONTEND=noninteractive

# lua5.1 + headers so luarocks can build C rocks against it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      lua5.1 \
      liblua5.1-0-dev \
      luarocks \
      make \
      unzip \
      jq \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Debian's luarocks defaults to the distro's newest Lua. Pin every invocation to
# 5.1 and install system-wide so both root and vscode see the rocks.
ARG LUAROCKS_ARGS="--lua-version=5.1 --lua-dir=/usr"
RUN luarocks ${LUAROCKS_ARGS} install luacheck \
 && luarocks ${LUAROCKS_ARGS} install busted \
 && luarocks ${LUAROCKS_ARGS} install dkjson

# StyLua ships prebuilt binaries only. Pin a version, but fall back to the
# current release rather than failing the whole image build on a dead tag.
ARG STYLUA_VERSION=2.0.2
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) STYLUA_ARCH=x86_64 ;; \
      arm64) STYLUA_ARCH=aarch64 ;; \
      *) echo "unsupported arch for stylua" >&2; exit 1 ;; \
    esac; \
    base=https://github.com/JohnnyMorganz/StyLua/releases; \
    url="${base}/download/v${STYLUA_VERSION}/stylua-linux-${STYLUA_ARCH}.zip"; \
    if ! curl -fsSL -o /tmp/stylua.zip "$url"; then \
      echo "pinned stylua v${STYLUA_VERSION} not found, resolving latest" >&2; \
      tag="$(curl -fsSL https://api.github.com/repos/JohnnyMorganz/StyLua/releases/latest | jq -r .tag_name)"; \
      echo "using stylua ${tag}" >&2; \
      curl -fsSL -o /tmp/stylua.zip \
        "${base}/download/${tag}/stylua-linux-${STYLUA_ARCH}.zip"; \
    fi; \
    unzip -o /tmp/stylua.zip -d /usr/local/bin stylua; \
    chmod 0755 /usr/local/bin/stylua; \
    rm /tmp/stylua.zip; \
    stylua --version

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# --- Claude Code -----------------------------------------------------------
# The agent works inside this container, so it needs the CLI here. Installed as
# the `vscode` user (native installer targets ~/.local/bin, not a system path).
# Auth is NOT baked in — the ~/.claude named volume in devcontainer.json holds
# credentials, so you log in once and it survives rebuilds.
USER vscode
RUN curl -fsSL https://claude.ai/install.sh | bash \
 && /home/vscode/.local/bin/claude --version
ENV PATH="/home/vscode/.local/bin:${PATH}"
USER root

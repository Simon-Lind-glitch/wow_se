# Offline build toolchain. Runs entirely inside the devcontainer.
# One command from a clean checkout (spec §9.3): make all
.DEFAULT_GOAL := help
.PHONY: help all extract translate emit verify guard lint fmt fmt-check test clean

ADDON := addon/WoWsvSE
# `tools/` is the import root: the stages are top-level modules (extract,
# translate, emit) so `python -m extract` reads the same from make and by hand.
PY    := PYTHONPATH=$(CURDIR)/tools python
LUA   := lua5.1

help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

all: extract translate emit verify ## Full pipeline: clean checkout -> shippable addon

extract: ## Pull source strings from client dumps + Questie into tools/cache/source
	$(PY) -m extract

translate: ## Batch-translate uncached strings (needs ANTHROPIC_API_KEY)
	@test -n "$$ANTHROPIC_API_KEY" \
	  || { echo "ANTHROPIC_API_KEY not set — export it on the host and rebuild"; exit 1; }
	$(PY) -m translate

emit: ## Write generated Lua tables into $(ADDON)
	$(PY) -m emit

verify: guard lint fmt-check test ## Everything that must pass before the addon goes near the game

# Spec §2 non-goals are enforced, not just documented. Chat translation is the
# one that could get an account actioned, so it fails the build outright.
guard: ## Assert no forbidden API surface crept into the addon
	@fail=0; \
	for pat in 'CHAT_MSG_' 'ChatFrame_AddMessageEventFilter' 'os\.execute' \
	           '\brequire\b' '\bio\.' 'LoadLibrary' 'SendChatMessage'; do \
	  if grep -rnE "$$pat" $(ADDON) 2>/dev/null; then \
	    echo "FORBIDDEN: /$$pat/ appears in $(ADDON) (spec §2/§3)"; fail=1; \
	  fi; \
	done; \
	if grep -rnE '^\s*(function\s+)?(QuestInfo|GameTooltip)[A-Za-z_]*\s*=\s*function' $(ADDON) 2>/dev/null; then \
	  echo "FORBIDDEN: outright replacement of a Blizzard function — use hooksecurefunc (spec §3)"; fail=1; \
	fi; \
	test $$fail -eq 0 && echo "guard: clean"

lint: ## luacheck the addon, ruff the toolchain
	luacheck $(ADDON)
	ruff check tools

fmt: ## Format hand-written Lua and Python in place
	stylua $(ADDON)
	ruff format tools

fmt-check: ## Fail if formatting is off (CI-safe)
	stylua --check $(ADDON)
	ruff format --check tools

test: ## Lua unit tests (masking/round-trip) + Python toolchain tests
	busted --lua=$(LUA) tests
	pytest -q tools

clean: ## Remove generated output. Does NOT touch tools/cache (committed).
	rm -rf $(ADDON)/data/*.lua $(ADDON)/locale/*.lua

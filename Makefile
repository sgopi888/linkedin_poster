.PHONY: install-skill install-discipline install-all init-memories check-drift venv deps test-draft

HERMES_BASE := $(HOME)/.hermes/skills
HERMES_SOCIAL := $(HERMES_BASE)/social-media
HERMES_PRODUCTIVITY := $(HERMES_BASE)/productivity
SKILL_NAME := linkedin

define SAFE_INSTALL
	@INSTALL_DIR="$(1)"; SRC="$(2)"; \
	if [ -d "$$INSTALL_DIR" ] && ! diff -rq "$$INSTALL_DIR/SKILL.md" "$$SRC/SKILL.md" >/dev/null 2>&1; then \
		BACKUP="$$INSTALL_DIR.backup.$$(date +%Y%m%d_%H%M%S)"; \
		echo "⚠  $$INSTALL_DIR/SKILL.md differs from $$SRC/SKILL.md"; \
		echo "   Hermes may have updated this skill. Backing up to:"; \
		echo "   $$BACKUP"; \
		cp -r "$$INSTALL_DIR" "$$BACKUP"; \
	fi; \
	mkdir -p "$$(dirname $$INSTALL_DIR)"; \
	rm -rf "$$INSTALL_DIR"; \
	cp -r "$$SRC" "$$INSTALL_DIR"
endef

install-skill:
	$(call SAFE_INSTALL,$(HERMES_SOCIAL)/$(SKILL_NAME),skills/linkedin-poster)
	@# Strip openclaw reference subfolders so Hermes doesn't see duplicate SKILL.md files
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/linkedin-post-writer-1.0.0
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/hermes-agent-1.0.0
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/hermes-agent-v2-2.1.1
	@# Also clean up any leftover symlinked install from earlier
	@rm -f $(HERMES_SOCIAL)/linkedin-poster
	@echo "Installed linkedin skill to $(HERMES_SOCIAL)/$(SKILL_NAME)"

install-discipline:
	$(call SAFE_INSTALL,$(HERMES_PRODUCTIVITY)/hermes-discipline,skills/hermes-discipline)
	@echo "Installed hermes-discipline skill to $(HERMES_PRODUCTIVITY)/hermes-discipline"

check-drift:
	@echo "=== linkedin skill drift check ==="
	@if [ -d $(HERMES_SOCIAL)/$(SKILL_NAME) ]; then \
		diff -rq skills/linkedin-poster/SKILL.md $(HERMES_SOCIAL)/$(SKILL_NAME)/SKILL.md 2>&1 || true; \
		diff -r skills/linkedin-poster/SKILL.md $(HERMES_SOCIAL)/$(SKILL_NAME)/SKILL.md 2>&1 | head -30 || true; \
	else echo "(not installed)"; fi
	@echo
	@echo "=== hermes-discipline drift check ==="
	@if [ -d $(HERMES_PRODUCTIVITY)/hermes-discipline ]; then \
		diff -rq skills/hermes-discipline/SKILL.md $(HERMES_PRODUCTIVITY)/hermes-discipline/SKILL.md 2>&1 || true; \
	else echo "(not installed)"; fi

init-memories:
	@mkdir -p $(HOME)/.hermes/memories/archive
	@touch $(HOME)/.hermes/memories/MEMORY.md
	@touch $(HOME)/.hermes/memories/REFLECTIONS.md
	@touch $(HOME)/.hermes/memories/PROMOTIONS.md
	@echo "Memory layout initialized in $(HOME)/.hermes/memories/"

install-all: install-skill install-discipline init-memories
	@echo
	@echo "All skills installed. Restart Hermes gateway:"
	@echo "  systemctl --user restart hermes-gateway.service"

venv:
	@if [ ! -d .venv ] && [ ! -d venv ]; then \
		python3 -m venv venv && venv/bin/pip install -r requirements.txt; \
	fi

deps: venv
	@if [ -d .venv ]; then .venv/bin/pip install -r requirements.txt; \
	else venv/bin/pip install -r requirements.txt; fi

test-draft:
	@./scripts/run.sh draft "smoke test from Makefile" --no-image

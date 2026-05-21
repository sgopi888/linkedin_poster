.PHONY: install-skill install-discipline install-all init-memories venv deps test-draft

HERMES_BASE := $(HOME)/.hermes/skills
HERMES_SOCIAL := $(HERMES_BASE)/social-media
HERMES_PRODUCTIVITY := $(HERMES_BASE)/productivity
SKILL_NAME := linkedin

install-skill:
	@mkdir -p $(HERMES_SOCIAL)
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME) $(HERMES_SOCIAL)/linkedin-poster
	@cp -r skills/linkedin-poster $(HERMES_SOCIAL)/$(SKILL_NAME)
	@# Strip the openclaw reference subfolders so Hermes doesn't see duplicate SKILL.md files
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/linkedin-post-writer-1.0.0
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/hermes-agent-1.0.0
	@rm -rf $(HERMES_SOCIAL)/$(SKILL_NAME)/hermes-agent-v2-2.1.1
	@echo "Installed linkedin skill to $(HERMES_SOCIAL)/$(SKILL_NAME)"

install-discipline:
	@mkdir -p $(HERMES_PRODUCTIVITY)
	@rm -rf $(HERMES_PRODUCTIVITY)/hermes-discipline
	@cp -r skills/hermes-discipline $(HERMES_PRODUCTIVITY)/hermes-discipline
	@echo "Installed hermes-discipline skill to $(HERMES_PRODUCTIVITY)/hermes-discipline"

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

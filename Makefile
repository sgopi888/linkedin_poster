.PHONY: install-skill venv deps test-draft

HERMES_SKILLS := $(HOME)/.hermes/skills/social-media
SKILL_NAME := linkedin

install-skill:
	@mkdir -p $(HERMES_SKILLS)
	@rm -rf $(HERMES_SKILLS)/$(SKILL_NAME) $(HERMES_SKILLS)/linkedin-poster
	@cp -r skills/linkedin-poster $(HERMES_SKILLS)/$(SKILL_NAME)
	@echo "Installed skill to $(HERMES_SKILLS)/$(SKILL_NAME)"
	@echo "Restart Hermes gateway to pick up changes:"
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

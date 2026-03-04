.PHONY: help setup build serve adapt scrape scrape-year analyze analyze-year deploy clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────

setup: ## Install Python dependencies (MkDocs)
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

setup-scraper: ## Install Telegram scraper dependencies
	cd telegram_scraper && python3 -m venv venv && venv/bin/pip install -r requirements.txt

# ── Content pipeline ───────────────────────────────────────

adapt: ## Convert research/ -> docs/ (run after editing research files)
	.venv/bin/python adapt_docs.py

build: adapt ## Build MkDocs site (includes adapt step)
	.venv/bin/mkdocs build

serve: ## Local dev server (http://localhost:8000)
	.venv/bin/mkdocs serve

# ── Telegram scraper ──────────────────────────────────────

scrape: ## Scrape Telegram channels (last 30 days)
	cd telegram_scraper && source .env 2>/dev/null; venv/bin/python scraper.py --days 30

scrape-year: ## Scrape Telegram channels (365 days)
	cd telegram_scraper && source .env 2>/dev/null; venv/bin/python scrape_year.py

analyze: ## Analyze short-term Telegram data
	cd telegram_scraper && venv/bin/python analyze.py

analyze-year: ## Analyze yearly Telegram data
	cd telegram_scraper && venv/bin/python analyze_year.py

# ── Deploy ─────────────────────────────────────────────────

deploy: build ## Full pipeline: adapt + build + commit prompt
	@echo ""
	@echo "Site built. To deploy:"
	@echo "  git add docs/ && git commit -m 'Update content' && git push"
	@echo ""
	@echo "Or trigger manually:"
	@echo "  gh workflow run 'Deploy VR Research'"

# ── Utility ────────────────────────────────────────────────

clean: ## Remove build artifacts
	rm -rf site/

epub: ## Build EPUB book from research
	cd research && bash build_epub.sh

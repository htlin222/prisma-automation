# Makefile for PRISMA workflow automation project

# Variables
OUTPUT_DIR = output
VENV_DIR = .venv
SEARCH_TERMS_DIR = search_terms

# Default target
.PHONY: all
all: help

# Run PubMed search
.PHONY: pubmed
pubmed:
	@echo "Running PubMed search..."
	@if [ ! -f $(SEARCH_TERMS_DIR)/pubmed_search_term.txt ]; then \
		echo "Error: PubMed search term file not found!"; \
		exit 1; \
	fi
	@source $(VENV_DIR)/bin/activate && python prisma.py search --databases pubmed
	@echo "PubMed search completed. Results saved to $(OUTPUT_DIR)/pubmed_results.bib"

# Run Scopus search
.PHONY: scopus
scopus:
	@echo "Running Scopus search..."
	@if [ ! -f $(SEARCH_TERMS_DIR)/scopus_search_term.txt ]; then \
		echo "Error: Scopus search term file not found!"; \
		exit 1; \
	fi
	@source $(VENV_DIR)/bin/activate && python prisma.py search --databases scopus
	@echo "Scopus search completed. Results saved to $(OUTPUT_DIR)/scopus_results.bib"

# Run deduplication on all result files
.PHONY: deduplicate
deduplicate:
	@echo "Running deduplication on all result files..."
	@if [ ! -d $(OUTPUT_DIR) ]; then \
		echo "Error: Output directory not found!"; \
		exit 1; \
	fi
	@chmod +x scripts/deduplicate.py
	@source $(VENV_DIR)/bin/activate && python scripts/deduplicate.py \
		--input-dir $(OUTPUT_DIR) \
		--output-file $(OUTPUT_DIR)/deduplicated.bib \
		--report-file $(OUTPUT_DIR)/duplicates_report.csv
	@echo "Deduplication completed. Results saved to $(OUTPUT_DIR)/deduplicated.bib"
	@echo "Duplicates report saved to $(OUTPUT_DIR)/duplicates_report.csv"

# Run automatic first-pass screening
.PHONY: screen
screen:
	@echo "Running automatic first-pass screening..."
	@if [ ! -f $(OUTPUT_DIR)/deduplicated.bib ]; then \
		echo "Error: Deduplicated BibTeX file not found! Run 'make deduplicate' first."; \
		exit 1; \
	fi
	@mkdir -p $(OUTPUT_DIR)/screening
	@mkdir -p models
	@chmod +x scripts/screening.py
	@source $(VENV_DIR)/bin/activate && python scripts/screening.py \
		--input-file $(OUTPUT_DIR)/deduplicated.bib \
		--output-dir $(OUTPUT_DIR)/screening \
		--config-path config.json \
		--seed $(SEARCH_TERMS_DIR)/seed_labels/seed_labels.csv \
		--model-path models/screening_model.pkl
	@echo "Screening completed. Results saved to $(OUTPUT_DIR)/screening/"
	@echo "  - screening_results.csv: Combined screening results"
	@echo "  - included_articles.bib: Articles to include"
	@echo "  - excluded_articles.bib: Articles to exclude"
	@echo "  - uncertain_articles.bib: Articles requiring manual review"
	@echo "  - active_learning_samples.csv: Priority articles for labeling"

# Run enhanced ML screening
.PHONY: ml-screen
ml-screen:
	@echo "Running enhanced ML screening with robust techniques..."
	@if [ ! -f $(OUTPUT_DIR)/deduplicated.bib ]; then \
		echo "Error: Deduplicated BibTeX file not found! Run 'make deduplicate' first."; \
		exit 1; \
	fi
	@mkdir -p $(OUTPUT_DIR)/ml_screening
	@mkdir -p models
	@source $(VENV_DIR)/bin/activate && python src/python/ml_screening.py \
		--input-file $(OUTPUT_DIR)/deduplicated.bib \
		--output-dir $(OUTPUT_DIR)/ml_screening \
		--config-path config.json \
		--seed-file $(SEARCH_TERMS_DIR)/seed_labels/seed_labels.csv \
		--model-path models/ml_screening_model.pkl \
		--model-type random_forest \
		--use-ensemble \
		--handle-imbalance \
		--active-learning uncertainty
	@echo "Enhanced ML screening completed. Results saved to $(OUTPUT_DIR)/ml_screening/"
	@echo "  - screening_results.csv: Combined screening results"
	@echo "  - included_articles.bib: Articles to include"
	@echo "  - excluded_articles.bib: Articles to exclude"
	@echo "  - active_learning_samples.csv: Priority articles for labeling"

# Check search terms
.PHONY: checkup
checkup:
	@echo "Checking search term files..."
	@mkdir -p $(SEARCH_TERMS_DIR)
	@echo "Checking PubMed search term..."
	@if [ ! -f $(SEARCH_TERMS_DIR)/pubmed_search_term.txt ]; then \
		echo "  - PubMed search term file not found!"; \
	else \
		if [ ! -s $(SEARCH_TERMS_DIR)/pubmed_search_term.txt ]; then \
			echo "  - PubMed search term file is empty!"; \
		else \
			echo "  - PubMed search term file exists and is not empty."; \
		fi; \
	fi
	@echo "Checking Scopus search term..."
	@if [ ! -f $(SEARCH_TERMS_DIR)/scopus_search_term.txt ]; then \
		echo "  - Scopus search term file not found!"; \
	else \
		if [ ! -s $(SEARCH_TERMS_DIR)/scopus_search_term.txt ]; then \
			echo "  - Scopus search term file is empty!"; \
		else \
			echo "  - Scopus search term file exists and is not empty."; \
		fi; \
	fi
	@echo "Checking Embase search term..."
	@if [ ! -f $(SEARCH_TERMS_DIR)/embase_search_term.txt ]; then \
		echo "  - Embase search term file not found!"; \
	else \
		if [ ! -s $(SEARCH_TERMS_DIR)/embase_search_term.txt ]; then \
			echo "  - Embase search term file is empty!"; \
		else \
			echo "  - Embase search term file exists and is not empty."; \
		fi; \
	fi
	@echo "Search term check completed."

# Check environment
.PHONY: env
env:
	@echo "Checking Python environment..."
	@if [ ! -d $(VENV_DIR) ]; then \
		echo "Virtual environment not found! Creating with uv..."; \
		uv venv || { echo "Failed to create virtual environment with uv. Is uv installed?"; exit 1; }; \
	else \
		echo "Virtual environment exists."; \
	fi
	@echo "Checking required packages..."
	@chmod +x scripts/check_packages.py
	@source $(VENV_DIR)/bin/activate && python scripts/check_packages.py || \
	(source $(VENV_DIR)/bin/activate && uv pip install requests pandas pybtex python-dotenv biopython)
	@echo "Environment check completed."

# Clean up output directory
.PHONY: clean
clean:
	@echo "Cleaning output directory..."
	@rm -rf $(OUTPUT_DIR)/*.bib
	@rm -rf $(OUTPUT_DIR)/*.csv
	@rm -rf $(OUTPUT_DIR)/*.xlsx
	@rm -rf $(OUTPUT_DIR)/screening
	@echo "Output directory cleaned."

# Clean and recreate output directory
.PHONY: clean-all
clean-all:
	@echo "Removing and recreating output directory..."
	@rm -rf $(OUTPUT_DIR)
	@mkdir -p $(OUTPUT_DIR)
	@echo "Output directory recreated."

# Run tests
.PHONY: test
test:
	@echo "Running tests..."
	@source $(VENV_DIR)/bin/activate && python -m tests.test_search_terms
	@echo "Tests completed."

# Run Scopus test
.PHONY: test-scopus
test-scopus:
	@echo "Running Scopus API test..."
	@source $(VENV_DIR)/bin/activate && python -m tests.test_scopus
	@echo "Scopus test completed."

# Help
.PHONY: help
help:
	@echo "PRISMA Workflow Automation Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  clean       - Remove all files from output directory"
	@echo "  clean-all   - Remove and recreate output directory"
	@echo "  test        - Run all tests"
	@echo "  test-scopus - Run Scopus API test"
	@echo "  help        - Show this help message"
	@echo "  pubmed      - Run PubMed search"
	@echo "  scopus      - Run Scopus search"
	@echo "  checkup     - Check search term files"
	@echo "  env         - Check Python environment"
	@echo "  deduplicate - Run deduplication on all result files"
	@echo "  screen      - Run automatic first-pass screening"
	@echo "  ml-screen   - Run enhanced ML screening"

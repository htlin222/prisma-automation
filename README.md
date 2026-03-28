![GitHub stars](https://img.shields.io/github/stars/htlin222/prisma-automation?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/htlin222/prisma-automation?style=flat-square)
![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

# PRISMA Workflow Automation

This project automates the PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) workflow using Python and R.

## Project Structure

- `src/python/`: Python modules for API calls to Pubmed, Cochrane, Scopus, and Embase
- `src/r/`: R scripts for PRISMA visualization using the PRISMA2020 package
- `data/`: Directory for storing input data
- `output/`: Directory for storing output data and visualizations
- `docs/`: Documentation for various components of the project

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Project Overview](./docs/README.md): General information about the project structure and components
- [Scopus API Integration](./docs/SCOPUS_API_README.md): Documentation for the Scopus API module
- [API Integration Guide](./docs/API_INTEGRATION.md): Overview of all API integrations in the project
- [Configuration Guide](./docs/CONFIGURATION.md): Detailed explanation of the `config.json` file structure and options

## Quick Start Guide

This guide will help you get started with the PRISMA workflow automation tool quickly.

### Prerequisites

- Python 3.8 or higher
- R (for visualization features)
- API keys for the databases you want to search (PubMed, Scopus, Embase)

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/prisma-automation.git
   cd prisma-automation
   ```

2. Set up your Python environment:

   ```bash
   # Create and activate a virtual environment
   uv venv
   source .venv/bin/activate

   # Install dependencies
   uv pip install -e .
   ```

3. Configure your API keys:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file to add your API keys:

   ```makefile
   PUBMED_EMAIL=your.email@example.com
   PUBMED_API_KEY=your_pubmed_api_key
   SCOPUS_API_KEY=your_scopus_api_key
   EMBASE_API_KEY=your_embase_api_key
   ```

### Basic Usage

The `prisma.py` script is the main entry point for the tool. You can run it with various commands:

#### Searching Databases

Search PubMed, Scopus, and Embase using the configured search terms:

```bash
python prisma.py search
```

Search specific databases:

```bash
python prisma.py search --databases pubmed scopus
```

Search with a custom query:

```bash
python prisma.py search --databases pubmed --query "lung cancer AND clinical trial"
```

Limit the number of results:

```bash
python prisma.py search --max-results 100
```

Combine results from all databases into a single BibTeX file:

```bash
python prisma.py search --combine
```

#### Exporting Results

Export search results to different formats:

```bash
python prisma.py export --input output/pubmed_results.bib --format excel
```

Available formats: `csv`, `excel`, `json`

#### Managing Configuration

View the current configuration:

```bash
python prisma.py config --show
```

Open the configuration file in your default editor:

```bash
python prisma.py config --edit
```

### Customizing Search Terms

Search terms for each database are stored in separate files in the `search_terms/` directory:

- `search_terms/pubmed_search_term.txt`: PubMed-specific search syntax
- `search_terms/scopus_search_term.txt`: Scopus-specific search syntax
- `search_terms/embase_search_term.txt`: Embase-specific search syntax

Edit these files to customize your search terms for each database.

### Search Terms Setup

The project requires properly formatted search terms for each database in the `search_terms/` directory:

1. Create database-specific search term files:
   - `search_terms/pubmed_search_term.txt` - For PubMed searches
   - `search_terms/scopus_search_term.txt` - For Scopus searches
   - `search_terms/embase_search_term.txt` - For Embase searches

2. Format your search terms according to each database's syntax:
   - **PubMed**: Use proper MeSH terms and field tags ([PubMed Search Tips](https://browse.welch.jhmi.edu/searching/pubmed-search-tips))
   - **Scopus**: Use field codes and boolean operators ([Scopus Search Guide](https://elsevier.libguides.com/Scopus/topical-search))

Example PubMed search term:
```
(lung cancer[MeSH Terms] OR lung neoplasms[MeSH Terms]) AND (therapy[Subheading] OR treatment[Title/Abstract])
```

Example Scopus search term:
```
TITLE-ABS-KEY("lung cancer" OR "lung neoplasm*") AND TITLE-ABS-KEY(therap* OR treat*)
```

3. Verify your search terms using the checkup command:
```bash
make checkup
```

### Configuration

The `config.json` file contains the configuration for your systematic review:

- Project metadata (title, description, authors)
- Database-specific settings (fields, date range, languages, max results)
- Screening criteria (inclusion/exclusion for title/abstract and full-text)
- Data extraction fields
- Output settings

See the [Configuration Guide](./docs/CONFIGURATION.md) for detailed information.

### Workflow Example

A typical PRISMA workflow using this tool:

1. Configure your search strategy in `config.json` and the search term files
2. Search multiple databases:

   ```bash
   python prisma.py search --databases pubmed scopus embase --combine
   ```

3. Import the combined results into Zotero for screening
4. Export the screening results
5. Generate PRISMA flow diagram using the R scripts in `src/r/`

## Setup

### Python Environment

This project uses `uv` for Python environment management.

```bash
# Create and activate a virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .
```

### Environment Variables

Copy the `.env.example` file to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

## Usage

Documentation on usage will be added as the project develops.

## Using the Makefile

The project includes a Makefile that provides convenient commands for common tasks. Here's how to use the available make commands:

### Basic Commands

```bash
# Clean the output directory (removes all generated files)
make clean

# Run environment check to ensure all dependencies are installed
make env

# Check the search term files for proper formatting
make checkup
```

### Database Search Commands

```bash
# Search PubMed using the configured search terms
make pubmed

# Search Scopus using the configured search terms
make scopus

# Search Embase using the configured search terms
make embase
```

### Data Processing Commands

```bash
# Run the deduplication process on search results
make deduplicate

# Run the automatic first-pass screening
make screen

# Run the enhanced ML screening with robust techniques
make ml-screen

# Run the entire workflow (search, deduplicate, screen)
make all
```

### Advanced Usage

You can pass additional parameters to customize the commands:

```bash
# Specify a custom seed file for screening
make screen SEED_FILE=search_terms/seed_labels/custom_seed_labels.csv

# Specify a custom output directory
make all OUTPUT_DIR=custom_output
```

### Makefile Variables

The Makefile uses the following variables that you can override:

- `OUTPUT_DIR`: Directory for output files (default: `output`)
- `SEARCH_TERMS_DIR`: Directory for search term files (default: `search_terms`)
- `VENV_DIR`: Directory for the virtual environment (default: `.venv`)

Example:
```bash
make all OUTPUT_DIR=my_results SEARCH_TERMS_DIR=my_search_terms
```

## Enhanced ML Screening

The project includes an enhanced machine learning screening system with robust techniques for more accurate article selection:

### Features

- **Multiple ML Algorithms**: Random Forest and ensemble methods with optimized parameters
- **Cross-validation**: Ensures model reliability even with limited training data
- **Feature Engineering**: Domain-specific text features for medical literature
- **Class Imbalance Handling**: Uses SMOTE and other techniques to address imbalanced datasets
- **Active Learning**: Prioritizes the most informative articles for manual review
- **Ensemble Methods**: Combines multiple models for improved decision-making

### Using ML Screening

To use the enhanced ML screening:

```bash
# Run with default settings
make ml-screen

# Specify a custom seed file
make ml-screen SEED_FILE=search_terms/seed_labels/custom_seed_labels.csv
```

### Seed Labels

The ML screening system requires seed labels to train the model. These are manually classified examples that provide initial training data.

Seed labels are stored in `search_terms/seed_labels/` directory as CSV files with the following format:

```csv
entry_id,label,reason
pubmed_12345678,1,Relevant randomized controlled trial
pubmed_87654321,0,Animal study not meeting inclusion criteria
```

See the [Seed Labels README](./search_terms/seed_labels/README.md) for detailed instructions on creating effective seed labels.

## License

[MIT](LICENSE)

# PRISMA Workflow Automation Documentation

This directory contains documentation for the PRISMA workflow automation project.

## Overview

The PRISMA workflow automation project is designed to automate the systematic review process following the PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) guidelines. It provides tools for searching multiple databases, extracting data, and generating reports.

## Documentation Files

- [Scopus API Integration](./SCOPUS_API_README.md): Documentation for the Scopus API module, including usage, query syntax, and troubleshooting.
- [API Integration Guide](./API_INTEGRATION.md): Overview of all API integrations in the project.
- [Configuration Guide](./CONFIGURATION.md): Detailed explanation of the `config.json` file structure and options.

## Project Structure

The project is organized as follows:

- `src/python/`: Python source code
  - `scopus_api.py`: Scopus API integration
  - `cli.py`: Command-line interface
  - `config_loader.py`: Configuration loading utilities

- `test_*.py`: Test scripts for various modules

- `config.json`: Configuration file for search strategies

## Configuration

The project uses a `config.json` file to define the search strategy, including:

1. Project metadata (title, description, authors)
2. Search terms organized by PICO framework (Population, Intervention, Comparison, Outcome)
3. Database-specific parameters for PubMed, Cochrane, Scopus, and Embase
4. Output settings (format, deduplication, export path)

## Command-Line Interface

The project provides a command-line interface with three main commands:

1. `search`: Search multiple databases simultaneously
2. `export`: Convert BibTeX files to CSV, Excel, or JSON formats
3. `config`: View and edit the configuration file

## API Integrations

The project integrates with multiple academic databases:

- Scopus
- PubMed
- Embase
- Cochrane

Each database has its own API module with specific search capabilities and data extraction methods.

## Getting Started

1. Clone the repository
2. Create a `.env` file with your API keys
3. Install dependencies
4. Run the CLI with `python -m src.python.cli`

## Contributing

When contributing to the project, please follow these guidelines:

1. Create a feature branch for your changes
2. Write tests for new functionality
3. Update documentation as needed
4. Submit a pull request for review

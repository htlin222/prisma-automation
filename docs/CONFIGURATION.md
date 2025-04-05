# Configuration Guide

This document explains how to configure the PRISMA workflow automation project using the `config.json` file.

## Overview

The `config.json` file is the central configuration for the PRISMA workflow automation project. It defines the search strategy, database settings, and output preferences.

## Configuration Structure

The configuration file has the following main sections:

```json
{
  "project": { ... },
  "search_terms": { ... },
  "boolean_operators": { ... },
  "database_defaults": { ... },
  "databases": {
    "pubmed": { ... },
    "scopus": { ... },
    "embase": { ... },
    "cochrane": { ... }
  },
  "screening": { ... },
  "data_extraction": { ... },
  "output": { ... }
}
```

## Project Section

The `project` section contains metadata about the systematic review:

```json
"project": {
  "title": "Example Systematic Review",
  "description": "A systematic review of lung cancer treatments",
  "authors": ["Researcher A", "Researcher B"],
  "date": "2025-04-01"
}
```

## Search Terms

The `search_terms` section follows the PICO framework:

```json
"search_terms": {
  "population": ["lung cancer", "NSCLC", "non-small cell lung cancer"],
  "intervention": ["immunotherapy", "pembrolizumab", "nivolumab"],
  "comparison": ["chemotherapy", "radiation therapy"],
  "outcome": ["survival", "progression-free survival"],
  "study_design": ["randomized controlled trial", "systematic review"]
}
```

## Boolean Operators

The `boolean_operators` section defines how search terms are combined:

```json
"boolean_operators": {
  "within_category": "OR",
  "between_categories": "AND"
}
```

## Database Defaults

The `database_defaults` section contains settings that apply to all databases by default:

```json
"database_defaults": {
  "enabled": true,
  "fields": ["title", "abstract", "keywords"],
  "date_range": {
    "start_year": 2000,
    "end_year": 2025
  },
  "languages": ["english"],
  "max_results": 1000
}
```

## Database-Specific Settings

Each database has its own section with specific settings that override the defaults:

```json
"databases": {
  "scopus": {
    "enabled": true,
    "fields": ["title", "abstract", "keywords"],
    "subject_areas": ["medicine", "health sciences"],
    "document_types": ["article", "review"]
  }
}
```

## Screening Criteria

The `screening` section defines inclusion and exclusion criteria:

```json
"screening": {
  "title_abstract": {
    "inclusion": ["human studies", "adult patients"],
    "exclusion": ["case reports", "animal studies"]
  },
  "full_text": {
    "inclusion": ["sample size > 100", "follow-up > 1 year"],
    "exclusion": ["non-English full text", "conference abstracts"]
  }
}
```

## Data Extraction

The `data_extraction` section defines fields to extract from included studies:

```json
"data_extraction": {
  "fields": [
    "study_design",
    "sample_size",
    "intervention_details",
    "outcome_measures",
    "results",
    "conclusions"
  ]
}
```

## Output Settings

The `output` section defines how results are exported:

```json
"output": {
  "format": "bibtex",
  "deduplicate": true,
  "export_path": "output/results"
}
```

## Example Configuration

See the project's `config.json` file for a complete example configuration.

## Modifying the Configuration

You can modify the configuration in several ways:

1. Directly edit the `config.json` file
2. Use the CLI command: `python -m src.python.cli config edit`
3. Programmatically via the `ConfigLoader` class

## Configuration Validation

The `ConfigLoader` class validates the configuration when loading it. If there are errors, it will raise exceptions with helpful error messages.

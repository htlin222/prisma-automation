# Scopus API Integration

This document provides information about the Scopus API integration in the PRISMA workflow automation project.

## Overview

The Scopus API module allows searching for academic articles in the Scopus database. It provides functionality to:

1. Search for articles using simple or complex queries
2. Extract article metadata (title, authors, journal, etc.)
3. Export results to BibTeX format

## API Key

The Scopus API requires an API key for authentication. The key should be stored in a `.env` file in the project root directory:

```shell
SCOPUS_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```python
from src.python.scopus_api import ScopusAPI

# Initialize the API
scopus = ScopusAPI()

# Simple search
results = scopus.search("TITLE-ABS-KEY(lung cancer)", max_results=10)

# Export to BibTeX
scopus.to_bibtex("output/results.bib")
```

### Advanced Usage

The module can build complex queries based on the configuration in `config.json`:

```python
# Build query from configuration
query = scopus.build_query()

# Search with the complex query
results = scopus.search(query, max_results=100)
```

## Query Syntax

### Simple Queries

Simple queries use the Scopus search syntax:

- `TITLE-ABS-KEY(term)`: Search in title, abstract, and keywords
- `TITLE(term)`: Search only in title
- `AUTH(name)`: Search by author name
- `PUBYEAR > 2020`: Filter by publication year

### Complex Queries

Complex queries can be built from the configuration using the `build_query()` method. The query structure follows the PICO framework:

- Population terms (e.g., "lung cancer")
- Intervention terms
- Comparison terms
- Outcome terms
- Study design filters (e.g., "randomized controlled trial")

## Testing

Two test scripts are provided:

1. `test_scopus.py`: Tests the full Scopus API functionality
2. `simple_scopus_test.py`: Tests basic API connectivity with a simple query

Run the tests with:

```bash
python test_scopus.py
python simple_scopus_test.py
```

## Known Issues and Limitations

1. **Complex Queries**: The complex query builder may generate queries that are too restrictive, resulting in no matches. For testing purposes, it's recommended to use simple queries like `TITLE-ABS-KEY(lung cancer)`.

2. **API View Options**: The Scopus API supports different view options:
   - `STANDARD`: Basic metadata (default)
   - `COMPLETE`: Full metadata including abstracts and keywords

3. **Author Parsing**: Author names are parsed from the `dc:creator` field, which may be a string or a list. The current implementation handles both formats.

4. **BibTeX Export**: The BibTeX export functionality has been enhanced to handle missing fields gracefully.

## Troubleshooting

If you encounter issues with the Scopus API:

1. Check your API key and permissions
2. Try a simple query first to verify API connectivity
3. Examine the raw API response using the `test_direct_api_call()` function
4. Check for rate limiting in the API response headers

## Next Steps

1. Improve complex query building to ensure queries return results
2. Add support for additional Scopus API features (e.g., citation analysis)
3. Enhance error handling and logging
4. Add unit tests for the Scopus API methods

## References

- [Scopus API Documentation](https://dev.elsevier.com/scopus.html)
- [Scopus Search API Guide](https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl)

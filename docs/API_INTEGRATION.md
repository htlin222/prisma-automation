# API Integration Guide

This document provides an overview of all API integrations in the PRISMA workflow automation project.

## Supported Databases

The project currently integrates with the following academic databases:

1. **Scopus** - [Documentation](./SCOPUS_API_README.md)
2. **PubMed**
3. **Embase**
4. **Cochrane**

## Common API Structure

All API modules follow a similar structure:

1. **Initialization**: Create an instance with configuration
2. **Search**: Execute a search query
3. **Data Extraction**: Extract article metadata
4. **Export**: Export results to various formats

## API Keys and Authentication

Each database requires specific API keys or authentication methods:

| Database | Environment Variable | Authentication Method |
|----------|---------------------|----------------------|
| Scopus   | SCOPUS_API_KEY      | API Key in header    |
| PubMed   | PUBMED_API_KEY      | API Key in query     |
| Embase   | EMBASE_API_KEY      | API Key in header    |
| Cochrane | COCHRANE_API_KEY    | API Key in header    |

Store these keys in a `.env` file in the project root directory.

## Query Building

Each API module provides a `build_query()` method that constructs a database-specific query from the common configuration in `config.json`.

The query building process follows these steps:

1. Extract search terms from configuration
2. Apply database-specific syntax
3. Add filters (date range, language, etc.)
4. Combine with boolean operators

## Error Handling

API modules include error handling for common issues:

- Connection errors
- Authentication failures
- Rate limiting
- Malformed queries

## Testing

Each API module has a corresponding test script:

- `test_scopus.py`
- `test_pubmed.py`
- `test_embase.py`
- `test_cochrane.py`

These scripts verify API connectivity and functionality.

## Future Improvements

Planned improvements for API integrations:

1. Unified error handling across all APIs
2. Caching of API responses
3. Retry mechanisms for failed requests
4. Comprehensive logging

#!/usr/bin/env python
"""
Test script for Scopus API with a simplified query.

This script tests the Scopus API module with a simple query that we know works.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.python.scopus_api import ScopusAPI

def main():
    """Run a test search for lung cancer using Scopus API with a simplified query."""
    # Load environment variables
    load_dotenv()
    
    # Print environment variables for debugging
    print(f"SCOPUS_API_KEY: {'*' * len(os.getenv('SCOPUS_API_KEY', ''))} (hidden for security)")
    
    # Initialize Scopus API
    scopus = ScopusAPI()
    
    # Use a simple query that we know works
    query = "TITLE-ABS-KEY(lung cancer)"
    print(f"Query: {query}")
    
    # Set max results to a small number for testing
    max_results = 5
    print(f"Max results: {max_results}")
    
    # Search Scopus with STANDARD view
    print("\nSearching Scopus...")
    results = scopus.search(query, max_results, view="STANDARD")
    
    if not results:
        print("No results found")
        return
    
    print(f"Found {len(results)} results")
    
    # Print results
    print("\nResults:")
    for i, article in enumerate(results):
        print(f"\n{i+1}. {article.get('title', 'No title')}")
        print(f"   Authors: {article.get('authors_str', 'N/A')}")
        print(f"   Journal: {article.get('journal', 'N/A')}, {article.get('year', 'N/A')}")
        print(f"   DOI: {article.get('doi', 'N/A')}")
    
    # Export to BibTeX
    output_path = "output/scopus_simple_results.bib"
    print(f"\nExporting to BibTeX: {output_path}")
    scopus.to_bibtex(output_path)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()

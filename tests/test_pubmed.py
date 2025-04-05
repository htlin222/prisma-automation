#!/usr/bin/env python
"""
Test script for PubMed API.

This script tests the PubMed API functionality with a simple "lung cancer" search.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.python.pubmed_api import PubMedAPI
from src.python.config_loader import get_config

def main():
    """Run a test search for lung cancer using PubMed API."""
    # Load environment variables
    load_dotenv()
    
    # Print environment variables for debugging
    print(f"PUBMED_API_KEY: {'*' * len(os.getenv('PUBMED_API_KEY', ''))} (hidden for security)")
    print(f"PUBMED_EMAIL: {os.getenv('PUBMED_EMAIL', 'Not set')}")
    
    # Get configuration
    config = get_config()
    print(f"Search terms: {config.get_search_terms()}")
    
    # Initialize PubMed API
    pubmed = PubMedAPI()
    
    # Build query
    query = pubmed.build_query()
    print(f"Query: {query}")
    
    # Set max results to a small number for testing
    max_results = 5
    print(f"Max results: {max_results}")
    
    # Search PubMed
    print("\nSearching PubMed...")
    id_list = pubmed.search(query, max_results)
    
    if not id_list:
        print("No results found")
        return
    
    print(f"Found {len(id_list)} results")
    
    # Fetch article details
    print("\nFetching article details...")
    pubmed.fetch_details(id_list)
    
    # Convert to DataFrame
    df = pubmed.to_dataframe()
    
    # Print results
    print("\nResults:")
    for i, (_, row) in enumerate(df.iterrows()):
        print(f"\n{i+1}. {row['title']}")
        print(f"   Authors: {row.get('authors_str', 'N/A')}")
        print(f"   Journal: {row.get('journal', 'N/A')}, {row.get('year', 'N/A')}")
    
    # Export to BibTeX
    output_path = "output/pubmed_test_results.bib"
    print(f"\nExporting to BibTeX: {output_path}")
    pubmed.to_bibtex(output_path)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()

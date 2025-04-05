#!/usr/bin/env python
"""
Test script for Scopus API.

This script tests the Scopus API module by searching for articles related to lung cancer.
"""

import os
import json
import requests
from dotenv import load_dotenv
from src.python.scopus_api import ScopusAPI

def main():
    """Run a test search for lung cancer using Scopus API."""
    # Load environment variables
    load_dotenv()
    
    # Print environment variables for debugging
    api_key = os.getenv("SCOPUS_API_KEY", "")
    print(f"SCOPUS_API_KEY: {'*' * len(api_key)} (hidden for security)")
    
    # Test direct API call first
    test_direct_api_call()
    
    # Initialize Scopus API
    scopus = ScopusAPI()
    
    # Get search terms from configuration
    search_terms = scopus.scopus_config.get("search_terms", {})
    print(f"Search terms: {search_terms}")
    
    # Build query from configuration
    query = scopus.build_query()
    print(f"Query: {query}")
    
    # Set max results to a small number for testing
    max_results = 5
    print(f"Max results: {max_results}")
    
    # Search Scopus
    print("\nSearching Scopus...")
    
    # Try a simple query first for testing
    simple_query = "TITLE-ABS-KEY(lung cancer)"
    print(f"Using simple query: {simple_query}")
    results = scopus.search(simple_query, max_results)
    
    # Only try complex query if requested
    if not results and False:  # Set to True to test complex query
        print(f"\nTrying complex query: {query}")
        results = scopus.search(query, max_results)
    
    # Print raw result data for debugging
    if results:
        print("\nRaw result data (first result):")
        print(json.dumps(results[0], indent=2))
    
    # Print results
    print("\nResults:")
    for i, article in enumerate(results):
        print(f"\n{i+1}. {article.get('title', 'No title')}")
        print(f"   Authors: {article.get('authors_str', '')}")
        print(f"   Journal: {article.get('journal', '')}, {article.get('year', '')}")
        print(f"   DOI: {article.get('doi', '')}")
    
    # Export to BibTeX
    output_path = "output/scopus_test_results.bib"
    print(f"\nExporting to BibTeX: {output_path}")
    scopus.to_bibtex(output_path)
    
    print("\nTest completed successfully!")

def test_direct_api_call():
    """Test direct API call to Scopus."""
    print("\nMaking direct API call to Scopus...")
    
    # Get API key
    api_key = os.getenv("SCOPUS_API_KEY")
    
    # Set up headers
    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key
    }
    
    # Simple query for testing
    query = "TITLE-ABS-KEY(lung cancer)"
    
    # Set up parameters
    params = {
        "query": query,
        "view": "STANDARD",
        "count": 1
    }
    
    # Make API request
    url = "https://api.elsevier.com/content/search/scopus"
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Print headers for debugging
            print("Headers:", json.dumps(dict(response.headers), indent=2))
            
            data = response.json()
            
            if "search-results" in data and "entry" in data["search-results"]:
                entries = data["search-results"]["entry"]
                total_count = data["search-results"].get("opensearch:totalResults", "0")
                
                print("\nAPI Response Structure:")
                print(f"Total results: {total_count}")
                print(f"Fields available: {list(data['search-results'].keys())}")
                
                if entries:
                    # Print available fields in the first entry
                    first_entry = entries[0]
                    print("\nFirst entry fields:")
                    print(list(first_entry.keys()))
                    
                    # Print some sample fields from the first entry
                    print("\nFirst entry data (sample fields):")
                    for field in ["dc:title", "dc:creator", "prism:publicationName", "prism:coverDate", "prism:doi"]:
                        if field in first_entry:
                            print(f"{field}: {first_entry[field]}")
                    
                    # Save raw entry to file for inspection
                    os.makedirs("output", exist_ok=True)
                    with open("output/scopus_raw_entry.json", "w") as f:
                        json.dump(first_entry, f, indent=2)
                    print("\nSaved raw entry to output/scopus_raw_entry.json")
                    
                    # Manual data extraction for comparison
                    print("\nManual data extraction:")
                    print(f"Title: {first_entry.get('dc:title', '')}")
                    print(f"Journal: {first_entry.get('prism:publicationName', '')}")
                    year = first_entry.get("prism:coverDate", "").split("-")[0] if first_entry.get("prism:coverDate") else ""
                    print(f"Year: {year}")
                    print(f"DOI: {first_entry.get('prism:doi', '')}")
                    
                    # Extract authors
                    creator = first_entry.get("dc:creator", "")
                    print("Authors:")
                    if creator:
                        authors = creator.split(", ")
                        for i, author in enumerate(authors):
                            print(f"  {i+1}. {author}")
            else:
                print("No results found or unexpected response format")
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"Error making API request: {e}")

if __name__ == "__main__":
    main()

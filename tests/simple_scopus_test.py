#!/usr/bin/env python
"""
Simple test script for Scopus API.

This script tests the basic Scopus API functionality with a simple query.
"""

import os
import json
import requests
from dotenv import load_dotenv

def main():
    """Run a simple test of the Scopus API."""
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        print("No Scopus API key found in environment variables")
        return
    
    print(f"SCOPUS_API_KEY: {'*' * len(api_key)} (hidden for security)")
    
    # Set up headers
    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key
    }
    
    # Simple query for testing
    query = "TITLE-ABS-KEY(lung cancer)"
    print(f"Query: {query}")
    
    # Set up parameters
    params = {
        "query": query,
        "view": "STANDARD",
        "count": 5
    }
    
    # Make API request
    url = "https://api.elsevier.com/content/search/scopus"
    print(f"Making API request to {url}...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "search-results" in data and "entry" in data["search-results"]:
                entries = data["search-results"]["entry"]
                total_count = data["search-results"].get("opensearch:totalResults", "0")
                print(f"Total results: {total_count}")
                print(f"Retrieved {len(entries)} entries")
                
                # Print the first entry
                if entries:
                    print("\nFirst entry:")
                    entry = entries[0]
                    
                    # Print key fields
                    for field in ["dc:title", "dc:creator", "prism:publicationName", "prism:coverDate", "prism:doi"]:
                        if field in entry:
                            print(f"  {field}: {entry[field]}")
                    
                    # Create a BibTeX-like entry
                    print("\nBibTeX-like entry:")
                    title = entry.get("dc:title", "")
                    authors = entry.get("dc:creator", "")
                    journal = entry.get("prism:publicationName", "")
                    year = entry.get("prism:coverDate", "").split("-")[0] if entry.get("prism:coverDate") else ""
                    doi = entry.get("prism:doi", "")
                    
                    print(f"@article{{scopus_{year},")
                    print(f"  title = {{{title}}},")
                    print(f"  author = {{{authors}}},")
                    print(f"  journal = {{{journal}}},")
                    print(f"  year = {{{year}}},")
                    print(f"  doi = {{{doi}}}")
                    print("}")
                    
                    # Save all entries to a file
                    output_path = "output/simple_scopus_results.json"
                    with open(output_path, "w") as f:
                        json.dump(entries, f, indent=2)
                    print(f"\nSaved {len(entries)} entries to {output_path}")
                
            else:
                print("No results found or unexpected response format")
                print(json.dumps(data, indent=2))
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"Error making API request: {e}")

if __name__ == "__main__":
    main()

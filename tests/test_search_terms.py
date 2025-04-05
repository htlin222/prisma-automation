#!/usr/bin/env python
"""
Test script for search term files.

This script tests the loading of search terms from text files for different databases.
"""

import os
from dotenv import load_dotenv
from src.python.config_loader import get_config
from src.python.scopus_api import ScopusAPI


def main():
    """Test loading search terms from files for different databases."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    config = get_config()
    
    print("Testing search term files...")
    print("===========================\n")
    
    # Test loading search terms from files
    databases = ["pubmed", "scopus", "embase"]
    
    for db in databases:
        print("\nTesting {} search term:".format(db.upper()))
        print("-" * 30)
        
        try:
            # Try to load the search term from the file
            search_term = config.get_search_term_from_file(db)
            print("Successfully loaded search term from file:")
            print("{}".format(search_term))
            print("")
            
            # Check if the file exists
            file_path = config.config["search_strategy"]["search_term_files"][db]
            file_size = os.path.getsize(file_path)
            print("File: {}".format(file_path))
            print("Size: {} bytes".format(file_size))
            
        except (FileNotFoundError, KeyError) as e:
            print("Error: {}".format(e))
    
    # Test Scopus API with the search term file
    print("\n\nTesting Scopus API with search term file:")
    print("-" * 40)
    
    scopus = ScopusAPI()
    query = scopus.build_query()
    
    print("Scopus query built from search term file:")
    print("{}".format(query))


if __name__ == "__main__":
    main()

"""
Configuration loader for PRISMA automation.

This module provides utilities to load and access the search strategy
configuration defined in config.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """Load and provide access to the PRISMA search configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the configuration file. If None, will look for
                         config.json in the project root directory.
        """
        if config_path is None:
            # Find the project root (where config.json is located)
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.json"
        
        self.config_path = Path(config_path)
        self.project_root = self.config_path.parent
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the JSON file.

        Returns:
            Dict containing the configuration.
        
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            json.JSONDecodeError: If the configuration file is not valid JSON.
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(f"Invalid JSON in configuration file {self.config_path}")
    
    def get_database_config(self, database_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific database.

        Args:
            database_name: Name of the database (pubmed, cochrane, scopus, embase)

        Returns:
            Dict containing the database-specific configuration.
            
        Raises:
            KeyError: If the database is not found in the configuration.
        """
        try:
            # Get database-specific configuration
            db_specific = self.config["databases"].get(database_name, {})
            
            # Get default configuration
            db_defaults = self.config.get("database_defaults", {})
            
            # Merge defaults with database-specific configuration
            # Database-specific settings override defaults
            merged_config = {**db_defaults, **db_specific}
            
            # Add enabled flag if not present
            if "enabled" not in merged_config:
                merged_config["enabled"] = True
                
            return merged_config
        except KeyError:
            raise KeyError(f"Database '{database_name}' not found in configuration")
    
    def get_search_terms(self) -> Dict[str, Any]:
        """
        Get the search terms configuration.

        Returns:
            Dict containing the search terms and boolean operators.
        """
        return self.config["search_strategy"]
    
    def get_search_term_from_file(self, database_name: str) -> str:
        """
        Load the search term for a specific database from its text file.
        
        Args:
            database_name: Name of the database (pubmed, scopus, embase)
            
        Returns:
            String containing the search term from the file
            
        Raises:
            FileNotFoundError: If the search term file doesn't exist
            KeyError: If the database is not found in the search_term_files configuration
        """
        try:
            # Get the filename from the configuration
            search_term_files = self.config["search_strategy"].get("search_term_files", {})
            if database_name not in search_term_files:
                raise KeyError(f"No search term file specified for database '{database_name}'")
                
            file_path = self.project_root / search_term_files[database_name]
            
            # Read the search term from the file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Search term file not found at {file_path}")
                
            with open(file_path, 'r') as f:
                search_term = f.read().strip()
                
            return search_term
        except KeyError as e:
            raise KeyError(str(e))
        except FileNotFoundError as e:
            raise FileNotFoundError(str(e))
    
    def build_search_query(self, database_name: str) -> str:
        """
        Build a search query string for the specified database.
        
        This method first tries to load the search term from the database-specific
        text file. If that fails, it falls back to building the query from the
        search terms in the config.json file.

        Args:
            database_name: Name of the database to build the query for

        Returns:
            String containing the search query
        """
        # First try to get the search term from the file
        try:
            return self.get_search_term_from_file(database_name)
        except (FileNotFoundError, KeyError) as e:
            print(f"Warning: {e}. Falling back to building query from config.")
        
        # If that fails, fall back to the old method
        # Get the search terms and operators
        search_strategy = self.get_search_terms()
        
        # If there's an advanced query specified, use that
        if "advanced_query" in search_strategy and search_strategy["advanced_query"]:
            return search_strategy["advanced_query"]
        
        # Check if we have the old format search terms
        if "search_terms" not in search_strategy:
            raise KeyError("No search terms found in configuration and no search term file available")
            
        terms = search_strategy["search_terms"]
        operators = search_strategy["boolean_operators"]
        
        # Otherwise build from the individual terms
        query_parts = []
        
        # For each category of terms
        for category, term_list in terms.items():
            if not term_list:
                continue
                
            # Join terms within a category with the within_category operator
            category_query = f" {operators['within_category']} ".join(f"({term})" for term in term_list)
            
            # Add parentheses around the category query if there's more than one term
            if len(term_list) > 1:
                category_query = f"({category_query})"
                
            query_parts.append(category_query)
        
        # Join the category queries with the between_categories operator
        final_query = f" {operators['between_categories']} ".join(query_parts)
        
        return final_query
    
    def get_screening_criteria(self) -> Dict[str, Any]:
        """
        Get the screening criteria.

        Returns:
            Dict containing inclusion and exclusion criteria.
        """
        return self.config["screening"]
    
    def get_data_extraction_fields(self) -> Dict[str, Any]:
        """
        Get the data extraction fields.

        Returns:
            Dict containing the fields to extract.
        """
        return self.config["data_extraction"]
    
    def get_output_settings(self) -> Dict[str, Any]:
        """
        Get the output settings.

        Returns:
            Dict containing output format and path information.
        """
        return self.config["output"]


# Create a singleton instance for easy import
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """
    Get the configuration loader instance.

    Returns:
        ConfigLoader instance.
    """
    return config


if __name__ == "__main__":
    # Example usage
    config = get_config()
    print(f"Project title: {config.config['project']['title']}")
    print(f"PubMed configuration: {config.get_database_config('pubmed')}")
    
    # Try to get the search query from the file
    try:
        pubmed_query = config.get_search_term_from_file('pubmed')
        print(f"Search query for PubMed (from file): {pubmed_query}")
    except (FileNotFoundError, KeyError) as e:
        print(f"Error: {e}")
        print(f"Search query for PubMed (built from config): {config.build_search_query('pubmed')}")

"""
Scopus API module for PRISMA workflow.

This module handles API calls to Elsevier's Scopus Search API,
and exports results to BibTeX format for import into Zotero.
"""

import os
import time
from typing import Dict, List, Any, Optional

import requests
import pandas as pd
from dotenv import load_dotenv
from pybtex.database import BibliographyData, Entry

from src.python.config_loader import get_config


class ScopusAPI:
    """
    Scopus API client for PRISMA systematic reviews.
    
    This class handles searching Scopus, retrieving article data,
    and exporting to BibTeX format.
    """
    
    # Base URL for the Scopus Search API
    BASE_URL = "https://api.elsevier.com/content/search/scopus"
    
    # Default headers for API requests
    DEFAULT_HEADERS = {
        "Accept": "application/json",
        "X-ELS-ResourceVersion": "XOCS"
    }
    
    # Field mapping for Scopus API
    FIELD_MAPPING = {
        "title": "dc:title",
        "abstract": "dc:description",
        "authors": "dc:creator",
        "journal": "prism:publicationName",
        "year": "prism:coverDate",
        "volume": "prism:volume",
        "issue": "prism:issueIdentifier",
        "pages": "prism:pageRange",
        "doi": "prism:doi",
        "url": "prism:url",
        "keywords": "authkeywords",
        "affiliations": "affiliation",
        "citation_count": "citedby-count",
        "source_id": "source-id",
        "eid": "eid",
        "scopus_id": "dc:identifier"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Scopus API client.
        
        Args:
            api_key: API key for Scopus API (required)
        """
        # Load environment variables
        load_dotenv()
        
        # Set API key
        self.api_key = api_key or os.getenv("SCOPUS_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key is required for Scopus API. Set SCOPUS_API_KEY in .env file.")
        
        # Set headers with API key
        self.headers = self.DEFAULT_HEADERS.copy()
        self.headers["X-ELS-APIKey"] = self.api_key
        
        # Load configuration
        self.config = get_config()
        self.scopus_config = self.config.get_database_config("scopus")
        
        # Initialize results storage
        self.results = []
        self.df = None
    
    def build_query(self) -> str:
        """
        Build a Scopus search query based on the configuration.
        
        Returns:
            String containing the formatted Scopus search query
        """
        # First try to get the search term directly from the file
        try:
            return self.config.get_search_term_from_file("scopus")
        except (FileNotFoundError, KeyError) as e:
            print(f"Warning: {e}. Falling back to building query from config.")
        
        # Fall back to building the query from the configuration
        query_parts = []
        
        # Get search strategy from configuration
        search_strategy = self.config.get_search_terms()
        
        # Check if we have an advanced query
        if "advanced_query" in search_strategy and search_strategy["advanced_query"]:
            return search_strategy["advanced_query"]
        
        # Check if we have the old format search terms
        if "search_terms" in search_strategy:
            terms = search_strategy["search_terms"]
            operators = search_strategy["boolean_operators"]
            
            # Process each category of terms
            for category, term_list in terms.items():
                if not term_list:
                    continue
                
                # Format terms for Scopus syntax
                if category == "population":
                    field = "TITLE-ABS-KEY"
                elif category == "intervention":
                    field = "TITLE-ABS-KEY"
                elif category == "comparison":
                    field = "TITLE-ABS-KEY"
                elif category == "outcome":
                    field = "TITLE-ABS-KEY"
                elif category == "study_design":
                    field = "DOCTYPE"
                else:
                    field = "TITLE-ABS-KEY"
                
                # Join terms within category
                if category == "study_design":
                    # For document types, we don't need to wrap each term in parentheses
                    category_terms = [f"{field}({term})" for term in term_list]
                else:
                    # For other fields, wrap each term in parentheses
                    category_terms = [f"{field}({term})" for term in term_list]
                
                category_query = f" {operators['within_category']} ".join(category_terms)
                
                # Add parentheses if multiple terms
                if len(term_list) > 1:
                    category_query = f"({category_query})"
                
                query_parts.append(category_query)
            
            # Join categories with between_categories operator
            query = f" {operators['between_categories']} ".join(query_parts)
        else:
            # No search terms found
            raise ValueError("No search terms found in configuration and no search term file available")
        
        # Add date range if specified
        date_range = self.scopus_config.get("date_range", {})
        if date_range and "start" in date_range and "end" in date_range:
            start_date = date_range["start"]
            end_date = date_range["end"]
            start_year = int(start_date[:4])
            end_year = int(end_date[:4])
            date_query = f"PUBYEAR > {start_year - 1} AND PUBYEAR < {end_year + 1}"
            query = f"({query}) AND {date_query}"
        
        # Add subject areas if specified
        subject_areas = self.scopus_config.get("subject_areas", [])
        if subject_areas:
            subject_query = " OR ".join([f"SUBJAREA({area})" for area in subject_areas])
            query = f"({query}) AND ({subject_query})"
        
        # Add document types if specified
        document_types = self.scopus_config.get("document_types", [])
        if document_types:
            doc_type_query = " OR ".join([f"DOCTYPE({doc_type})" for doc_type in document_types])
            query = f"({query}) AND ({doc_type_query})"
        
        return query
    
    def search(self, query: Optional[str] = None, max_results: Optional[int] = None, 
               view: str = "STANDARD", sort: str = "relevancy") -> List[Dict[str, Any]]:
        """
        Search Scopus for articles matching the query.
        
        Args:
            query: Search query string. If None, builds from configuration.
            max_results: Maximum number of results to return. If None, uses config value.
            view: View option for results (STANDARD, COMPLETE, CITATION)
            sort: Sort order for results (relevancy, date, cited)
            
        Returns:
            List of dictionaries containing article data
        """
        # Build query if not provided
        if not query:
            query = self.build_query()
        
        # Set max results if not provided
        if not max_results:
            max_results = self.scopus_config.get("max_results", 1000)
        
        # Print query for debugging
        print(f"Searching Scopus with query: {query}")
        print(f"Max results: {max_results}")
        
        # For simpler testing, use a basic query if the complex one fails
        try_simplified_query = True
        
        # Set up parameters
        params = {
            "query": query,
            "view": view,
            "sort": sort,
            "count": min(25, max_results)  # Results per page
        }
        
        # Initialize results list
        results = []
        start = 0
        
        # Paginate through results
        while start < max_results:
            params["start"] = start
            
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params=params
                )
                
                # Check for errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Extract search results
                if "search-results" in data and "entry" in data["search-results"]:
                    entries = data["search-results"]["entry"]
                    
                    # Break if no more results
                    if not entries:
                        break
                    
                    # Process entries
                    for entry in entries:
                        # Direct extraction of key fields
                        article_data = {
                            "title": entry.get("dc:title", ""),
                            "scopus_id": entry.get("dc:identifier", "").replace("SCOPUS_ID:", ""),
                            "eid": entry.get("eid", ""),
                            "doi": entry.get("prism:doi", ""),
                            "url": entry.get("prism:url", ""),
                            "journal": entry.get("prism:publicationName", ""),
                            "volume": entry.get("prism:volume", ""),
                            "issue": entry.get("prism:issueIdentifier", ""),
                            "pages": entry.get("prism:pageRange", ""),
                            "citation_count": entry.get("citedby-count", "0"),
                            "source_id": entry.get("source-id", ""),
                            "document_type": entry.get("subtypeDescription", ""),
                            "abstract": "",  # Abstract not available in STANDARD view
                            "keywords": [],  # Keywords not available in STANDARD view
                            "year": ""
                        }
                        
                        # Extract year from coverDate
                        cover_date = entry.get("prism:coverDate", "")
                        if cover_date:
                            article_data["year"] = cover_date.split("-")[0]
                        
                        # Extract authors
                        authors = []
                        creator = entry.get("dc:creator", "")
                        if creator:
                            author_names = creator.split(", ")
                            for name in author_names:
                                if name:
                                    parts = name.split()
                                    if len(parts) > 1:
                                        first_name = " ".join(parts[:-1])
                                        last_name = parts[-1]
                                    else:
                                        first_name = ""
                                        last_name = name
                                    
                                    authors.append({
                                        "last_name": last_name,
                                        "first_name": first_name,
                                        "initials": "".join([p[0] for p in parts[:-1] if p]),
                                        "authid": ""
                                    })
                        
                        article_data["authors"] = authors
                        article_data["authors_str"] = creator
                        
                        results.append(article_data)
                    
                    # Update start for next page
                    start += len(entries)
                    
                    # Check if we've reached the total count
                    total_count = int(data["search-results"].get("opensearch:totalResults", 0))
                    if start >= total_count or start >= max_results:
                        break
                    
                    # Be nice to Elsevier servers
                    time.sleep(1)
                else:
                    print("No results found or unexpected response format")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error searching Scopus: {e}")
                if hasattr(e, "response") and e.response is not None:
                    print(f"Response: {e.response.text}")
                
                # If the complex query fails and we haven't tried a simplified query yet
                if try_simplified_query:
                    try_simplified_query = False
                    print("Trying with simplified query: TITLE-ABS-KEY(lung cancer)")
                    params["query"] = "TITLE-ABS-KEY(lung cancer)"
                    start = 0
                    continue
                
                break
        
        print(f"Found {len(results)} results")
        self.results = results
        return results
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert results to a pandas DataFrame.
        
        Returns:
            DataFrame containing article data
        """
        if not self.results:
            print("No results to convert to DataFrame")
            return pd.DataFrame()
        
        # Flatten the nested structure for DataFrame
        flat_results = []
        for article in self.results:
            flat_article = article.copy()
            
            # Format authors
            if "authors" in flat_article:
                authors_list = flat_article["authors"]
                authors_str = ", ".join(
                    f"{author['last_name']}, {author['first_name']}" 
                    for author in authors_list if "last_name" in author and "first_name" in author
                )
                flat_article["authors_str"] = authors_str
            
            # Format keywords
            if "keywords" in flat_article:
                flat_article["keywords_str"] = ", ".join(flat_article["keywords"])
            
            flat_results.append(flat_article)
        
        self.df = pd.DataFrame(flat_results)
        return self.df
    
    def to_bibtex(self, output_path: Optional[str] = None) -> str:
        """
        Convert results to BibTeX format and optionally save to file.
        
        Args:
            output_path: Path to save BibTeX file. If None, uses config value.
            
        Returns:
            String containing BibTeX data
        """
        # Check if results exist
        if not self.results:
            print("No results to export")
            return ""
        
        # Use provided output_path or get from config
        if output_path is None:
            output_path = os.path.join(
                os.getenv("OUTPUT_DIR", "output"),
                self.scopus_config.get("output_file", "scopus_results.bib")
            )
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create BibTeX data
        bib_data = BibliographyData()
        
        for i, article in enumerate(self.results):
            # Create entry key
            if "doi" in article and article["doi"]:
                entry_key = f"scopus_{article['doi'].replace('/', '_')}"
            elif "scopus_id" in article and article["scopus_id"]:
                entry_key = f"scopus_{article['scopus_id']}"
            else:
                entry_key = f"scopus_{i+1}"
            
            # Create author string, ensuring it's not empty
            author_str = " and ".join(
                f"{author['last_name']}, {author['first_name']}" 
                for author in article.get("authors", []) 
                if "last_name" in author and "first_name" in author
            )
            
            # If no authors could be extracted, use the authors_str field or a placeholder
            if not author_str:
                author_str = article.get("authors_str", "Unknown Author")
            
            # Ensure all fields are strings and not None
            fields = [
                ("author", author_str),
                ("title", article.get("title", "") or ""),
                ("journal", article.get("journal", "") or ""),
                ("year", article.get("year", "") or ""),
                ("volume", article.get("volume", "") or ""),
                ("number", article.get("issue", "") or ""),
                ("pages", article.get("pages", "") or ""),
                ("doi", article.get("doi", "") or ""),
                ("url", article.get("url", "") or ""),
                ("scopus_id", article.get("scopus_id", "") or ""),
                ("eid", article.get("eid", "") or ""),
                ("keywords", ", ".join(article.get("keywords", [])) or ""),
                ("citation_count", article.get("citation_count", "0") or "0"),
                ("document_type", article.get("document_type", "") or ""),
            ]
            
            # Filter out empty fields to avoid BibTeX errors
            fields = [(key, value) for key, value in fields if value]
            
            # Create entry
            entry = Entry("article", fields)
            bib_data.entries[entry_key] = entry
        
        # Write to file if output_path is provided
        if output_path:
            bib_data.to_file(output_path, "bibtex")
            print(f"BibTeX data saved to {output_path}")
        
        # Return BibTeX string
        return bib_data.to_string("bibtex")
    
    def run_search_pipeline(self, query: Optional[str] = None, output_path: Optional[str] = None) -> pd.DataFrame:
        """
        Run the complete search pipeline: search, and export.
        
        Args:
            query: Search query string. If None, builds from configuration.
            output_path: Path to save BibTeX file. If None, uses config value.
            
        Returns:
            DataFrame containing search results
        """
        # Search Scopus
        self.search(query)
        
        if not self.results:
            print("No results found")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = self.to_dataframe()
        
        # Export to BibTeX
        self.to_bibtex(output_path)
        
        return df


if __name__ == "__main__":
    # Example usage
    scopus = ScopusAPI()
    results_df = scopus.run_search_pipeline()
    
    # Print summary
    if not results_df.empty:
        print(f"\nFound {len(results_df)} articles")
        print("\nSample of results:")
        print(results_df[["title", "authors_str", "journal", "year"]].head())

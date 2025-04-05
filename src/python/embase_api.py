"""
Embase API module for PRISMA workflow.

This module handles API calls to Elsevier's Embase Search/Retrieval API,
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


class EmbaseAPI:
    """
    Embase API client for PRISMA systematic reviews.
    
    This class handles searching Embase, retrieving article data,
    and exporting to BibTeX format.
    """
    
    # Base URL for the Embase Search API
    BASE_URL = "https://api.elsevier.com/content/embase/article"
    
    # Default headers for API requests
    DEFAULT_HEADERS = {
        "Accept": "application/json"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Embase API client.
        
        Args:
            api_key: API key for Embase API (required)
        """
        # Load environment variables
        load_dotenv()
        
        # Set API key
        self.api_key = api_key or os.getenv("EMBASE_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key is required for Embase API. Set EMBASE_API_KEY in .env file.")
        
        # Set headers with API key
        self.headers = self.DEFAULT_HEADERS.copy()
        self.headers["X-ELS-APIKey"] = self.api_key
        
        # Load configuration
        self.config = get_config()
        self.embase_config = self.config.get_database_config("embase")
        
        # Initialize results storage
        self.results = []
        self.df = None
    
    def build_query(self) -> str:
        """
        Build an Embase search query based on the configuration.
        
        Returns:
            String containing the formatted Embase search query
        """
        # Get search terms from configuration
        search_strategy = self.config.get_search_terms()
        
        # Check if there's an advanced query specified
        if "advanced_query" in search_strategy and search_strategy["advanced_query"]:
            query = search_strategy["advanced_query"]
        else:
            # Build query from search terms
            query_parts = []
            terms = search_strategy["search_terms"]
            operators = search_strategy["boolean_operators"]
            
            # Process each category of terms
            for category, term_list in terms.items():
                if not term_list:
                    continue
                
                # Format terms for Embase syntax
                if category == "population":
                    field = "ti,ab,kw"  # title, abstract, keywords
                elif category == "intervention":
                    field = "ti,ab,kw"
                elif category == "comparison":
                    field = "ti,ab,kw"
                elif category == "outcome":
                    field = "ti,ab,kw"
                elif category == "study_design":
                    field = "it"  # item type
                else:
                    field = "ti,ab,kw"
                
                # Join terms within category
                category_terms = []
                for term in term_list:
                    if category == "study_design":
                        # For evidence types, we don't need to wrap in quotes
                        category_terms.append(f"{term}/{field}")
                    else:
                        # For other fields, wrap in quotes if contains spaces
                        if " " in term:
                            category_terms.append(f"'{term}'/{field}")
                        else:
                            category_terms.append(f"{term}/{field}")
                
                category_query = f" {operators['within_category']} ".join(category_terms)
                
                # Add parentheses if multiple terms
                if len(term_list) > 1:
                    category_query = f"({category_query})"
                
                query_parts.append(category_query)
            
            # Join categories with between_categories operator
            query = f" {operators['between_categories']} ".join(query_parts)
        
        # Add date range if specified
        date_range = self.embase_config.get("date_range", {})
        if date_range and "start" in date_range and "end" in date_range:
            start_date = date_range["start"]
            end_date = date_range["end"]
            date_query = f"[{start_date} TO {end_date}]/py"
            query = f"({query}) AND {date_query}"
        
        # Add evidence types if specified
        evidence_types = self.embase_config.get("evidence_types", [])
        if evidence_types:
            evidence_query = " OR ".join([f"'{ev_type}'/it" for ev_type in evidence_types])
            query = f"({query}) AND ({evidence_query})"
        
        return query
    
    def search(self, query: Optional[str] = None, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search Embase for articles matching the query.
        
        Args:
            query: Search query string. If None, builds from configuration.
            max_results: Maximum number of results to return. If None, uses config value.
            
        Returns:
            List of dictionaries containing article data
        """
        # Use provided query or build from config
        if query is None:
            query = self.build_query()
        
        # Use provided max_results or get from config
        if max_results is None:
            max_results = self.embase_config.get("max_results", 100)
        
        print(f"Searching Embase with query: {query}")
        print(f"Max results: {max_results}")
        
        # Prepare parameters
        params = {
            "query": query,
            "count": min(25, max_results)  # API limit is 25 per request
        }
        
        results = []
        start = 1
        
        # Paginate through results
        while len(results) < max_results:
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
                if "results" in data and "entry" in data["results"]:
                    entries = data["results"]["entry"]
                    
                    # Break if no more results
                    if not entries:
                        break
                    
                    # Process entries
                    for entry in entries:
                        article_data = self._extract_article_data(entry)
                        results.append(article_data)
                    
                    # Update start for next page
                    start += len(entries)
                    
                    # Check if we've reached the total count
                    total_count = int(data["results"].get("totalResults", 0))
                    if start > total_count or len(results) >= max_results:
                        break
                    
                    # Be nice to Elsevier servers
                    time.sleep(1)
                else:
                    print("No results found or unexpected response format")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error searching Embase: {e}")
                if hasattr(e, "response") and e.response is not None:
                    print(f"Response: {e.response.text}")
                break
        
        # Trim to max_results if needed
        if len(results) > max_results:
            results = results[:max_results]
            
        print(f"Found {len(results)} results")
        self.results = results
        return results
    
    def _extract_article_data(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from an Embase article entry.
        
        Args:
            entry: Embase article entry from API response
            
        Returns:
            Dictionary containing extracted article data
        """
        # Initialize data dictionary
        data = {
            "embase_id": entry.get("embase_id", ""),
            "title": entry.get("title", ""),
            "abstract": entry.get("abstract", ""),
            "doi": entry.get("doi", ""),
            "url": entry.get("url", ""),
            "journal": entry.get("journal", {}).get("title", ""),
            "volume": entry.get("journal", {}).get("volume", ""),
            "issue": entry.get("journal", {}).get("issue", ""),
            "pages": f"{entry.get('startingPage', '')}-{entry.get('endingPage', '')}",
            "publication_type": entry.get("publicationType", ""),
            "publication_date": entry.get("publicationDate", ""),
        }
        
        # Extract year from publication date
        if data["publication_date"]:
            try:
                data["year"] = data["publication_date"].split("-")[0]
            except (IndexError, AttributeError):
                data["year"] = ""
        else:
            data["year"] = ""
        
        # Extract authors
        data["authors"] = self._extract_authors(entry)
        
        # Extract keywords
        data["keywords"] = self._extract_keywords(entry)
        
        # Extract PubMed ID if available
        if "pubmed_id" in entry:
            data["pubmed_id"] = entry["pubmed_id"]
        
        return data
    
    def _extract_authors(self, entry: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract author information from article data.
        
        Args:
            entry: Embase article entry
            
        Returns:
            List of dictionaries containing author information
        """
        authors = []
        
        # Check if author information is available
        if "authors" in entry and isinstance(entry["authors"], list):
            for author in entry["authors"]:
                author_data = {
                    "last_name": author.get("surname", ""),
                    "first_name": author.get("given_name", ""),
                    "initials": author.get("initials", ""),
                }
                
                # Extract affiliation if available
                if "affiliation" in author:
                    author_data["affiliation"] = author["affiliation"]
                
                authors.append(author_data)
        
        return authors
    
    def _extract_keywords(self, entry: Dict[str, Any]) -> List[str]:
        """
        Extract keywords from article data.
        
        Args:
            entry: Embase article entry
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Check if keywords are available
        if "keywords" in entry and isinstance(entry["keywords"], list):
            keywords = entry["keywords"]
        
        # Check for MeSH terms
        if "mesh_terms" in entry and isinstance(entry["mesh_terms"], list):
            for mesh in entry["mesh_terms"]:
                if isinstance(mesh, str):
                    keywords.append(mesh)
                elif isinstance(mesh, dict) and "term" in mesh:
                    keywords.append(mesh["term"])
        
        # Check for Emtree terms
        if "emtree_terms" in entry and isinstance(entry["emtree_terms"], list):
            for emtree in entry["emtree_terms"]:
                if isinstance(emtree, str):
                    keywords.append(emtree)
                elif isinstance(emtree, dict) and "term" in emtree:
                    keywords.append(emtree["term"])
        
        return keywords
    
    def get_article_by_id(self, article_id: str, id_type: str = "embase") -> Dict[str, Any]:
        """
        Retrieve a specific article by its identifier.
        
        Args:
            article_id: The identifier of the article
            id_type: The type of identifier (embase, pubmed_id, doi, pii, lui, medline)
            
        Returns:
            Dictionary containing article data
        """
        valid_id_types = ["embase", "pubmed_id", "doi", "pii", "lui", "medline"]
        if id_type not in valid_id_types:
            raise ValueError(f"Invalid id_type. Must be one of: {', '.join(valid_id_types)}")
        
        # Build URL based on id_type
        if id_type == "embase":
            url = f"{self.BASE_URL}/embase/{article_id}"
        elif id_type == "pubmed_id":
            url = f"{self.BASE_URL}/pubmed_id/{article_id}"
        elif id_type == "doi":
            url = f"{self.BASE_URL}/doi/{article_id}"
        elif id_type == "pii":
            url = f"{self.BASE_URL}/pii/{article_id}"
        elif id_type == "lui":
            url = f"{self.BASE_URL}/lui/{article_id}"
        elif id_type == "medline":
            url = f"{self.BASE_URL}/medline/{article_id}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            if "article" in data:
                article_data = self._extract_article_data(data["article"])
                return article_data
            else:
                print(f"Unexpected response format for article {article_id}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving article {article_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Response: {e.response.text}")
            return {}
    
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
        if not self.results:
            print("No results to convert to BibTeX")
            return ""
        
        # Use provided output_path or get from config
        if output_path is None:
            output_settings = self.config.get_output_settings()
            output_path = output_settings.get("export_path", "output/embase_results.bib")
            
            # Modify the default path to be embase-specific
            if output_path == "output/search_results.bib":
                output_path = "output/embase_results.bib"
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create BibTeX bibliography
        bib_data = BibliographyData()
        
        for article in self.results:
            # Create BibTeX entry key
            if article["authors"] and "last_name" in article["authors"][0]:
                first_author = article["authors"][0]["last_name"].lower()
                first_author = ''.join(c for c in first_author if c.isalnum())
            else:
                first_author = "unknown"
            
            entry_key = f"{first_author}{article['year']}_{article['embase_id']}"
            
            # Create BibTeX entry
            fields = [
                ("author", " and ".join(
                    f"{author['last_name']}, {author['first_name']}" 
                    for author in article["authors"] if "last_name" in author and "first_name" in author
                )),
                ("title", article["title"]),
                ("journal", article["journal"]),
                ("year", article["year"]),
                ("volume", article["volume"]),
                ("number", article["issue"]),
                ("pages", article["pages"]),
                ("abstract", article["abstract"]),
                ("keywords", ", ".join(article["keywords"])),
                ("publication_type", article["publication_type"]),
                ("embase_id", article["embase_id"]),
            ]
            
            # Add optional fields if available
            if article.get("doi"):
                fields.append(("doi", article["doi"]))
            
            if article.get("url"):
                fields.append(("url", article["url"]))
            
            if article.get("pubmed_id"):
                fields.append(("pmid", article["pubmed_id"]))
            
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
        # Search Embase
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
    embase = EmbaseAPI()
    results_df = embase.run_search_pipeline()
    
    # Print summary
    if not results_df.empty:
        print(f"\nFound {len(results_df)} articles")
        print("\nSample of results:")
        print(results_df[["title", "authors_str", "journal", "year"]].head())

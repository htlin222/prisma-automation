"""
PubMed API module for PRISMA workflow.

This module handles API calls to PubMed using the Entrez API from Biopython,
and exports results to BibTeX format for import into Zotero.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import pandas as pd
from Bio import Entrez
from dotenv import load_dotenv
from pybtex.database import BibliographyData, Entry

from src.python.config_loader import get_config


class PubMedAPI:
    """
    PubMed API client for PRISMA systematic reviews.
    
    This class handles searching PubMed, retrieving article data,
    and exporting to BibTeX format.
    """
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the PubMed API client.
        
        Args:
            email: Email address for Entrez API (required by NCBI)
            api_key: API key for Entrez API (optional, increases rate limits)
        """
        # Load environment variables
        load_dotenv()
        
        # Set Entrez email and API key
        self.email = email or os.getenv("PUBMED_EMAIL")
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")
        
        if not self.email:
            raise ValueError("Email is required for PubMed API. Set PUBMED_EMAIL in .env file.")
        
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key
        
        # Load configuration
        self.config = get_config()
        self.pubmed_config = self.config.get_database_config("pubmed")
        
        # Initialize results storage
        self.results = []
        self.df = None
    
    def build_query(self) -> str:
        """
        Build a PubMed search query based on the configuration.
        
        Returns:
            String containing the formatted PubMed search query
        """
        # Use the ConfigLoader's build_search_query method to get the search term
        query = self.config.build_search_query("pubmed")
        
        # Add date range if specified
        date_range = self.pubmed_config.get("date_range", {})
        if date_range and "start" in date_range and "end" in date_range:
            start_date = date_range["start"]
            end_date = date_range["end"]
            date_query = f'("{start_date}"[Date - Create] : "{end_date}"[Date - Create])'
            query = f"{query} AND {date_query}"
        
        # Add article types if specified
        article_types = self.pubmed_config.get("article_types", [])
        if article_types:
            type_queries = [f'"{article_type}"[Publication Type]' for article_type in article_types]
            type_query = " OR ".join(type_queries)
            query = f"{query} AND ({type_query})"
        
        # Add language restriction if specified
        languages = self.pubmed_config.get("languages", [])
        if languages:
            lang_queries = [f'"{lang}"[Language]' for lang in languages]
            lang_query = " OR ".join(lang_queries)
            query = f"{query} AND ({lang_query})"
        
        # Add species restriction if specified
        species = self.pubmed_config.get("species", [])
        if species:
            species_queries = [f'"{sp}"[MeSH Terms]' for sp in species]
            species_query = " OR ".join(species_queries)
            query = f"{query} AND ({species_query})"
        
        return query
    
    def search(self, query: Optional[str] = None, max_results: Optional[int] = None) -> List[str]:
        """
        Search PubMed for articles matching the query.
        
        Args:
            query: Search query string. If None, builds from configuration.
            max_results: Maximum number of results to return. If None, uses config value.
            
        Returns:
            List of PubMed IDs (PMIDs) matching the search
        """
        # Use provided query or build from config
        if query is None:
            query = self.build_query()
        
        # Use provided max_results or get from config
        if max_results is None:
            max_results = self.pubmed_config.get("max_results", 100)
        
        print(f"Searching PubMed with query: {query}")
        print(f"Max results: {max_results}")
        
        # Search PubMed
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance"
        )
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record["IdList"]
        print(f"Found {len(id_list)} results")
        
        return id_list
    
    def fetch_details(self, id_list: List[str], batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for a list of PubMed IDs.
        
        Args:
            id_list: List of PubMed IDs to fetch
            batch_size: Number of records to fetch in each batch
            
        Returns:
            List of dictionaries containing article details
        """
        if not id_list:
            print("No IDs to fetch")
            return []
        
        # Use provided batch_size or get from config
        if batch_size is None:
            batch_size = self.pubmed_config.get("batch_size", 100)
        
        results = []
        
        # Process IDs in batches
        for i in range(0, len(id_list), batch_size):
            batch_ids = id_list[i:i+batch_size]
            print(f"Fetching details for {len(batch_ids)} articles (batch {i//batch_size + 1})")
            
            try:
                handle = Entrez.efetch(db="pubmed", id=batch_ids, retmode="xml")
                records = Entrez.read(handle)
                handle.close()
                
                # Process each article
                for record in records["PubmedArticle"]:
                    article_data = self._extract_article_data(record)
                    results.append(article_data)
                
                # Be nice to NCBI servers
                if i + batch_size < len(id_list):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error fetching batch {i//batch_size + 1}: {e}")
        
        self.results = results
        return results
    
    def _extract_article_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from a PubMed article record.
        
        Args:
            record: PubMed article record from Entrez
            
        Returns:
            Dictionary containing extracted article data
        """
        article = record["MedlineCitation"]["Article"]
        pmid = record["MedlineCitation"]["PMID"]
        
        # Extract basic article information
        data = {
            "pmid": pmid,
            "title": article.get("ArticleTitle", ""),
            "journal": article["Journal"]["Title"],
            "year": self._extract_year(article),
            "volume": article["Journal"].get("JournalIssue", {}).get("Volume", ""),
            "issue": article["Journal"].get("JournalIssue", {}).get("Issue", ""),
            "pages": article.get("Pagination", {}).get("MedlinePgn", ""),
            "doi": self._extract_doi(article),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
        
        # Extract abstract
        if "Abstract" in article and "AbstractText" in article["Abstract"]:
            abstract_parts = article["Abstract"]["AbstractText"]
            if isinstance(abstract_parts, list):
                # Handle structured abstracts
                abstract = ""
                for part in abstract_parts:
                    if hasattr(part, "attributes") and "Label" in part.attributes:
                        abstract += f"{part.attributes['Label']}: {part}\n"
                    else:
                        abstract += f"{part}\n"
                data["abstract"] = abstract.strip()
            else:
                data["abstract"] = abstract_parts
        else:
            data["abstract"] = ""
        
        # Extract authors
        data["authors"] = self._extract_authors(article)
        
        # Extract keywords
        data["keywords"] = self._extract_keywords(record)
        
        # Extract publication type
        data["publication_type"] = self._extract_publication_type(record)
        
        return data
    
    def _extract_year(self, article: Dict[str, Any]) -> str:
        """Extract publication year from article data."""
        journal_issue = article["Journal"].get("JournalIssue", {})
        
        if "PubDate" in journal_issue:
            pub_date = journal_issue["PubDate"]
            if "Year" in pub_date:
                return pub_date["Year"]
            elif "MedlineDate" in pub_date:
                # Extract year from MedlineDate (format varies)
                import re
                year_match = re.search(r'\d{4}', pub_date["MedlineDate"])
                if year_match:
                    return year_match.group(0)
        
        # Fallback to current year
        return str(datetime.now().year)
    
    def _extract_doi(self, article: Dict[str, Any]) -> str:
        """Extract DOI from article data."""
        if "ELocationID" in article:
            for location in article["ELocationID"]:
                if location.attributes.get("EIdType") == "doi":
                    return location
        
        # Try to find DOI in ArticleIdList
        if "PubmedData" in article and "ArticleIdList" in article["PubmedData"]:
            for article_id in article["PubmedData"]["ArticleIdList"]:
                if article_id.attributes.get("IdType") == "doi":
                    return article_id
        
        return ""
    
    def _extract_authors(self, article: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract author information from article data."""
        authors = []
        
        if "AuthorList" in article:
            for author in article["AuthorList"]:
                author_data = {
                    "last_name": author.get("LastName", ""),
                    "first_name": author.get("ForeName", ""),
                    "initials": author.get("Initials", ""),
                }
                
                # Extract affiliation if available
                if "AffiliationInfo" in author and author["AffiliationInfo"]:
                    author_data["affiliation"] = author["AffiliationInfo"][0]["Affiliation"]
                
                authors.append(author_data)
        
        return authors
    
    def _extract_keywords(self, record: Dict[str, Any]) -> List[str]:
        """Extract keywords from article data."""
        keywords = []
        
        # Extract MeSH terms
        if "MeshHeadingList" in record["MedlineCitation"]:
            for mesh in record["MedlineCitation"]["MeshHeadingList"]:
                if "DescriptorName" in mesh:
                    keywords.append(mesh["DescriptorName"])
        
        # Extract keywords if available
        if "KeywordList" in record["MedlineCitation"]:
            for keyword_list in record["MedlineCitation"]["KeywordList"]:
                for keyword in keyword_list:
                    keywords.append(keyword)
        
        return keywords
    
    def _extract_publication_type(self, record: Dict[str, Any]) -> List[str]:
        """Extract publication type from article data."""
        pub_types = []
        
        if "PublicationTypeList" in record["MedlineCitation"]["Article"]:
            for pub_type in record["MedlineCitation"]["Article"]["PublicationTypeList"]:
                pub_types.append(pub_type)
        
        return pub_types
    
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
            
            # Format publication type
            if "publication_type" in flat_article:
                flat_article["publication_type_str"] = ", ".join(flat_article["publication_type"])
            
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
            output_path = output_settings.get("export_path", "output/pubmed_results.bib")
        
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
            
            entry_key = f"{first_author}{article['year']}_{article['pmid']}"
            
            # Create BibTeX entry
            entry = Entry(
                "article",
                [
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
                    ("doi", article["doi"]),
                    ("url", article["url"]),
                    ("pmid", article["pmid"]),
                    ("keywords", ", ".join(article["keywords"])),
                ]
            )
            
            bib_data.entries[entry_key] = entry
        
        # Write to file if output_path is provided
        if output_path:
            bib_data.to_file(output_path, "bibtex")
            print(f"BibTeX data saved to {output_path}")
        
        # Return BibTeX string
        return bib_data.to_string("bibtex")
    
    def run_search_pipeline(self, query: Optional[str] = None, output_path: Optional[str] = None) -> pd.DataFrame:
        """
        Run the complete search pipeline: search, fetch details, and export.
        
        Args:
            query: Search query string. If None, builds from configuration.
            output_path: Path to save BibTeX file. If None, uses config value.
            
        Returns:
            DataFrame containing search results
        """
        # Search PubMed
        id_list = self.search(query)
        
        if not id_list:
            print("No results found")
            return pd.DataFrame()
        
        # Fetch article details
        self.fetch_details(id_list)
        
        # Convert to DataFrame
        df = self.to_dataframe()
        
        # Export to BibTeX
        self.to_bibtex(output_path)
        
        return df


if __name__ == "__main__":
    # Example usage
    pubmed = PubMedAPI()
    results_df = pubmed.run_search_pipeline()
    
    # Print summary
    if not results_df.empty:
        print(f"\nFound {len(results_df)} articles")
        print("\nSample of results:")
        print(results_df[["title", "authors_str", "journal", "year"]].head())

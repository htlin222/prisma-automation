#!/usr/bin/env python
"""
Command-line interface for PRISMA workflow automation.

This module provides a CLI for running searches across multiple databases,
exporting results, and managing the PRISMA workflow.
"""

import argparse
import os
import sys
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

# Import API modules
try:
    from src.python.pubmed_api import PubMedAPI
except ImportError:
    try:
        # Try relative import as fallback
        from pubmed_api import PubMedAPI
    except ImportError:
        print("Warning: PubMed API module not found. PubMed search will not be available.")
        PubMedAPI = None

try:
    from src.python.scopus_api import ScopusAPI
except ImportError:
    try:
        # Try relative import as fallback
        from scopus_api import ScopusAPI
    except ImportError:
        print("Warning: Scopus API module not found. Scopus search will not be available.")
        ScopusAPI = None

try:
    from src.python.embase_api import EmbaseAPI
except ImportError:
    try:
        # Try relative import as fallback
        from embase_api import EmbaseAPI
    except ImportError:
        print("Warning: Embase API module not found. Embase search will not be available.")
        EmbaseAPI = None

try:
    from src.python.config_loader import get_config
except ImportError:
    try:
        # Try relative import as fallback
        from config_loader import get_config
    except ImportError:
        print("Error: Config loader module not found. Exiting.")
        sys.exit(1)


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="PRISMA workflow automation tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search databases for articles"
    )
    search_parser.add_argument(
        "--databases", "-d", nargs="+", default=["pubmed", "scopus", "embase"],
        help="Databases to search (pubmed, scopus, embase)"
    )
    search_parser.add_argument(
        "--query", "-q", type=str,
        help="Custom search query (overrides config.json)"
    )
    search_parser.add_argument(
        "--output", "-o", type=str,
        help="Output directory for BibTeX files"
    )
    search_parser.add_argument(
        "--max-results", "-m", type=int,
        help="Maximum number of results per database"
    )
    search_parser.add_argument(
        "--combine", "-c", action="store_true",
        help="Combine results from all databases into a single BibTeX file"
    )
    
    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export search results to different formats"
    )
    export_parser.add_argument(
        "--input", "-i", type=str, required=True,
        help="Input BibTeX file"
    )
    export_parser.add_argument(
        "--format", "-f", type=str, choices=["csv", "excel", "json"], default="excel",
        help="Output format"
    )
    export_parser.add_argument(
        "--output", "-o", type=str,
        help="Output file path"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config", help="Manage configuration"
    )
    config_parser.add_argument(
        "--show", "-s", action="store_true",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--edit", "-e", action="store_true",
        help="Open configuration file in default editor"
    )
    
    return parser


def search_databases(
    databases: List[str],
    query: Optional[str] = None,
    output_dir: Optional[str] = None,
    max_results: Optional[int] = None,
    combine: bool = False
) -> Dict[str, Any]:
    """
    Search specified databases and export results.
    
    Args:
        databases: List of database names to search
        query: Custom search query (overrides config.json)
        output_dir: Output directory for BibTeX files
        max_results: Maximum number of results per database
        combine: Whether to combine results into a single BibTeX file
        
    Returns:
        Dictionary with results summary
    """
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    config = get_config()
    
    # Prepare output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_settings = config.get_output_settings()
        output_path = output_settings.get("export_path", "output/search_results.bib")
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    all_entries = []
    
    # Search each database
    for db_name in databases:
        print(f"\n{'='*50}")
        print(f"Searching {db_name.upper()}...")
        print(f"{'='*50}")
        
        # Get database-specific configuration
        db_config = config.get_database_config(db_name)
        
        # Skip if database is disabled
        if not db_config.get("enabled", True):
            print(f"{db_name} is disabled in configuration. Skipping.")
            continue
        
        # Set output path
        if combine:
            output_path = os.path.join(output_dir, "combined_results.bib")
        else:
            output_path = os.path.join(output_dir, f"{db_name}_results.bib")
        
        # Search database
        try:
            if db_name == "pubmed":
                if PubMedAPI is None:
                    print("PubMed API module not available. Skipping.")
                    continue
                
                api = PubMedAPI()
                df = api.run_search_pipeline(query, output_path)
                
                if not df.empty:
                    results[db_name] = {
                        "count": len(df),
                        "output_path": output_path
                    }
                    if combine:
                        all_entries.extend(api.results)
            
            elif db_name == "scopus":
                if ScopusAPI is None:
                    print("Scopus API module not available. Skipping.")
                    continue
                
                api = ScopusAPI()
                df = api.run_search_pipeline(query, output_path)
                
                if not df.empty:
                    results[db_name] = {
                        "count": len(df),
                        "output_path": output_path
                    }
                    if combine:
                        all_entries.extend(api.results)
            
            elif db_name == "embase":
                if EmbaseAPI is None:
                    print("Embase API module not available. Skipping.")
                    continue
                
                api = EmbaseAPI()
                df = api.run_search_pipeline(query, output_path)
                
                if not df.empty:
                    results[db_name] = {
                        "count": len(df),
                        "output_path": output_path
                    }
                    if combine:
                        all_entries.extend(api.results)
            
            else:
                print(f"Unknown database: {db_name}")
        
        except Exception as e:
            print(f"Error searching {db_name}: {e}")
    
    # Combine results if requested
    if combine and all_entries:
        from pybtex.database import BibliographyData, Entry
        
        print("\nCombining results from all databases...")
        bib_data = BibliographyData()
        
        for i, entry in enumerate(all_entries):
            # Create BibTeX entry key
            if "authors" in entry and entry["authors"] and "last_name" in entry["authors"][0]:
                first_author = entry["authors"][0]["last_name"].lower()
                first_author = ''.join(c for c in first_author if c.isalnum())
            else:
                first_author = "unknown"
            
            year = entry.get("year", "")
            entry_key = f"{first_author}{year}_{i}"
            
            # Create BibTeX entry fields
            fields = []
            
            # Add author field
            if "authors" in entry and entry["authors"]:
                author_str = " and ".join(
                    f"{author['last_name']}, {author['first_name']}" 
                    for author in entry["authors"] 
                    if "last_name" in author and "first_name" in author
                )
                fields.append(("author", author_str))
            
            # Add other common fields
            for field in ["title", "journal", "year", "volume", "issue", "pages", "abstract", "doi", "url"]:
                if field in entry and entry[field]:
                    fields.append((field, entry[field]))
            
            # Add keywords
            if "keywords" in entry and entry["keywords"]:
                if isinstance(entry["keywords"], list):
                    fields.append(("keywords", ", ".join(entry["keywords"])))
                else:
                    fields.append(("keywords", entry["keywords"]))
            
            # Add database-specific identifiers
            for id_field in ["pmid", "scopus_id", "embase_id", "eid"]:
                if id_field in entry and entry[id_field]:
                    fields.append((id_field, entry[id_field]))
            
            # Create entry
            bib_entry = Entry("article", fields)
            bib_data.entries[entry_key] = bib_entry
        
        # Write combined BibTeX file
        bib_data.to_file(output_path, "bibtex")
        print(f"Combined results saved to {output_path}")
        
        results["combined"] = {
            "count": len(bib_data.entries),
            "output_path": output_path
        }
    
    return results


def export_results(input_file: str, format: str, output_file: Optional[str] = None) -> bool:
    """
    Export search results to different formats.
    
    Args:
        input_file: Input BibTeX file
        format: Output format (csv, excel, json)
        output_file: Output file path
        
    Returns:
        True if export was successful, False otherwise
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            return False
        
        # Import pybtex
        from pybtex.database import parse_file
        import pandas as pd
        
        # Parse BibTeX file
        bib_data = parse_file(input_file)
        
        # Convert to DataFrame
        entries = []
        for key, entry in bib_data.entries.items():
            data = {
                "entry_key": key,
                "entry_type": entry.type,
            }
            
            # Add fields
            for name, value in entry.fields.items():
                data[name] = value
            
            # Add formatted authors
            if "author" in entry.persons:
                authors = entry.persons["author"]
                data["authors"] = ", ".join(str(author) for author in authors)
            
            entries.append(data)
        
        df = pd.DataFrame(entries)
        
        # Determine output file path
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}.{format}"
        
        # Export to specified format
        if format == "csv":
            df.to_csv(output_file, index=False)
        elif format == "excel":
            df.to_excel(output_file, index=False)
        elif format == "json":
            df.to_json(output_file, orient="records", indent=2)
        
        print(f"Exported {len(df)} entries to {output_file}")
        return True
    
    except Exception as e:
        print(f"Error exporting results: {e}")
        return False


def manage_config(show: bool = False, edit: bool = False) -> None:
    """
    Manage configuration.
    
    Args:
        show: Whether to show current configuration
        edit: Whether to open configuration file in default editor
    """
    config = get_config()
    config_path = config.config_path
    
    if show:
        # Show current configuration
        print(f"Configuration file: {config_path}")
        print("\nProject:")
        print(f"  Title: {config.config['project']['title']}")
        print(f"  Description: {config.config['project']['description']}")
        
        print("\nEnabled Databases:")
        for db_name in config.config["databases"]:
            db_config = config.get_database_config(db_name)
            enabled = db_config.get("enabled", True)
            print(f"  {db_name}: {'Enabled' if enabled else 'Disabled'}")
        
        print("\nOutput Settings:")
        output_settings = config.get_output_settings()
        print(f"  Format: {output_settings.get('format', 'bib')}")
        print(f"  Deduplication: {output_settings.get('deduplication', False)}")
        print(f"  Export Path: {output_settings.get('export_path', 'output/search_results.bib')}")
    
    if edit:
        # Open configuration file in default editor
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(config_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", config_path])
            else:  # Linux
                subprocess.call(["xdg-open", config_path])
            
            print(f"Opened configuration file: {config_path}")
        except Exception as e:
            print(f"Error opening configuration file: {e}")
            print(f"Configuration file path: {config_path}")


def main():
    """Main entry point for the CLI."""
    # Parse command-line arguments
    parser = setup_parser()
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "search":
        results = search_databases(
            databases=args.databases,
            query=args.query,
            output_dir=args.output,
            max_results=args.max_results,
            combine=args.combine
        )
        
        # Print summary
        print("\nSearch Results Summary:")
        for db_name, result in results.items():
            print(f"  {db_name}: {result['count']} articles")
            print(f"    Output: {result['output_path']}")
    
    elif args.command == "export":
        export_results(
            input_file=args.input,
            format=args.format,
            output_file=args.output
        )
    
    elif args.command == "config":
        manage_config(
            show=args.show,
            edit=args.edit
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

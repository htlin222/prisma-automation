#!/usr/bin/env python
"""
Automatic Deduplication for PRISMA Workflow Automation.

This script combines all BibTeX files ending with _results.bib,
deduplicates entries, flags borderline cases for manual review,
and generates a duplicates report.
"""

import os
import re
import glob
import argparse
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

from pybtex.database import BibliographyData, Entry, parse_file


class Deduplicator:
    """
    Deduplicates BibTeX entries from multiple files.
    
    Uses a multi-stage approach to identify duplicates:
    1. Exact DOI match (highest confidence)
    2. Title similarity + year match (medium confidence)
    3. Author similarity + year + journal match (medium confidence)
    4. Title similarity only (low confidence, flagged for review)
    """
    
    def __init__(self, input_dir: str, output_file: str, report_file: str):
        """
        Initialize the deduplicator.
        
        Args:
            input_dir: Directory containing BibTeX files
            output_file: Path to save deduplicated BibTeX file
            report_file: Path to save duplicates report
        """
        self.input_dir = input_dir
        self.output_file = output_file
        self.report_file = report_file
        self.entries = {}  # Dict to store all entries
        self.duplicates = []  # List to store duplicate entries
        self.borderline_cases = []  # List to store borderline cases
        
    def load_bibtex_files(self) -> int:
        """
        Load all BibTeX files ending with _results.bib.
        
        Returns:
            Number of entries loaded
        """
        # Find all BibTeX files
        bibtex_files = glob.glob(os.path.join(self.input_dir, "*_results.bib"))
        
        if not bibtex_files:
            print(f"No BibTeX files found in {self.input_dir}")
            return 0
        
        print(f"Found {len(bibtex_files)} BibTeX files:")
        for file in bibtex_files:
            print(f"  - {os.path.basename(file)}")
        
        # Load all entries
        total_entries = 0
        for file in bibtex_files:
            try:
                bib_data = parse_file(file)
                source = os.path.basename(file).replace("_results.bib", "")
                
                for key, entry in bib_data.entries.items():
                    # Add source information to the entry
                    entry.fields["source"] = source
                    
                    # Create a new key that includes the source to avoid key collisions
                    new_key = f"{source}_{key}"
                    self.entries[new_key] = entry
                    total_entries += 1
                
                print(f"  Loaded {len(bib_data.entries)} entries from {os.path.basename(file)}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        print(f"Total entries loaded: {total_entries}")
        return total_entries
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Normalize a title for comparison.
        
        Args:
            title: Title to normalize
            
        Returns:
            Normalized title
        """
        if not title:
            return ""
        
        # Remove punctuation, extra spaces, and convert to lowercase
        title = re.sub(r'[^\w\s]', '', title.lower())
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    @staticmethod
    def normalize_authors(authors: str) -> str:
        """
        Normalize author names for comparison.
        
        Args:
            authors: Author string to normalize
            
        Returns:
            Normalized author string
        """
        if not authors:
            return ""
        
        # Extract last names only
        last_names = []
        for author in authors.split(" and "):
            # Handle different formats (First Last or Last, First)
            if "," in author:
                last_name = author.split(",")[0].strip()
            else:
                parts = author.strip().split()
                last_name = parts[-1] if parts else ""
            
            last_names.append(last_name.lower())
        
        return " ".join(sorted(last_names))
    
    @staticmethod
    def calculate_similarity(str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Jaccard similarity.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        # Split into words
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        # Calculate Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_duplicates(self) -> Tuple[Dict[str, Entry], List[Tuple[str, str, float, str]]]:
        """
        Find duplicate entries using a multi-stage approach.
        
        Returns:
            Tuple of (deduplicated entries, list of duplicates)
        """
        if not self.entries:
            return {}, []
        
        # Group entries by DOI
        doi_groups = {}
        for key, entry in self.entries.items():
            doi = entry.fields.get("doi", "").lower().strip()
            if doi:
                if doi not in doi_groups:
                    doi_groups[doi] = []
                doi_groups[doi].append(key)
        
        # Create a dictionary to store unique entries
        unique_entries = {}
        
        # Track processed entries
        processed = set()
        
        # First pass: Check exact DOI matches (highest confidence)
        for doi, keys in doi_groups.items():
            if len(keys) > 1:
                # Keep the first entry as the primary
                primary_key = keys[0]
                unique_entries[primary_key] = self.entries[primary_key]
                processed.add(primary_key)
                
                # Mark others as duplicates
                for dup_key in keys[1:]:
                    self.duplicates.append((
                        primary_key,
                        dup_key,
                        1.0,  # Confidence score for DOI match
                        "DOI match"
                    ))
                    processed.add(dup_key)
            else:
                # Single entry with this DOI
                unique_entries[keys[0]] = self.entries[keys[0]]
                processed.add(keys[0])
        
        # Second pass: Check title similarity + year match
        title_dict = {}
        for key, entry in self.entries.items():
            if key in processed:
                continue
                
            title = self.normalize_title(entry.fields.get("title", ""))
            year = entry.fields.get("year", "")
            
            if title and year:
                title_dict[(title, year)] = title_dict.get((title, year), []) + [key]
        
        # Process title+year matches
        for (title, year), keys in title_dict.items():
            if len(keys) > 1:
                # Keep the first entry as the primary
                primary_key = keys[0]
                unique_entries[primary_key] = self.entries[primary_key]
                processed.add(primary_key)
                
                # Mark others as duplicates
                for dup_key in keys[1:]:
                    self.duplicates.append((
                        primary_key,
                        dup_key,
                        0.9,  # Confidence score for title+year match
                        "Title and year match"
                    ))
                    processed.add(dup_key)
            else:
                # Single entry with this title+year
                unique_entries[keys[0]] = self.entries[keys[0]]
                processed.add(keys[0])
        
        # Third pass: Check for similar titles (borderline cases)
        remaining = [key for key in self.entries if key not in processed]
        
        # Compare each remaining entry with all unique entries
        for key in remaining:
            entry = self.entries[key]
            title = self.normalize_title(entry.fields.get("title", ""))
            authors = self.normalize_authors(entry.fields.get("author", ""))
            year = entry.fields.get("year", "")
            
            best_match = None
            best_score = 0.0
            match_reason = ""
            
            for unique_key, unique_entry in unique_entries.items():
                unique_title = self.normalize_title(unique_entry.fields.get("title", ""))
                unique_authors = self.normalize_authors(unique_entry.fields.get("author", ""))
                unique_year = unique_entry.fields.get("year", "")
                
                # Calculate title similarity
                title_sim = self.calculate_similarity(title, unique_title)
                
                # Check for high title similarity
                if title_sim > 0.8:
                    # If years match, consider it a likely duplicate
                    if year == unique_year:
                        if title_sim > best_score:
                            best_score = title_sim
                            best_match = unique_key
                            match_reason = "High title similarity and year match"
                    # If authors are similar, consider it a potential duplicate
                    elif authors and unique_authors:
                        author_sim = self.calculate_similarity(authors, unique_authors)
                        if author_sim > 0.5:
                            score = (title_sim + author_sim) / 2
                            if score > best_score:
                                best_score = score
                                best_match = unique_key
                                match_reason = "Title and author similarity"
                
                # Medium title similarity but matching authors and year
                elif title_sim > 0.5 and year == unique_year:
                    author_sim = self.calculate_similarity(authors, unique_authors)
                    if author_sim > 0.7:
                        score = (title_sim + author_sim) / 2
                        if score > best_score:
                            best_score = score
                            best_match = unique_key
                            match_reason = "Author similarity and year match"
            
            if best_match and best_score > 0.7:
                # High confidence duplicate
                self.duplicates.append((
                    best_match,
                    key,
                    best_score,
                    match_reason
                ))
                processed.add(key)
            elif best_match and best_score > 0.5:
                # Borderline case, flag for review
                self.borderline_cases.append((
                    best_match,
                    key,
                    best_score,
                    match_reason
                ))
                # Still add to unique entries for now
                unique_entries[key] = entry
                processed.add(key)
            else:
                # No match found, consider unique
                unique_entries[key] = entry
                processed.add(key)
        
        return unique_entries, self.duplicates
    
    def save_deduplicated_bibtex(self, unique_entries: Dict[str, Entry]) -> None:
        """
        Save deduplicated entries to a BibTeX file.
        
        Args:
            unique_entries: Dictionary of unique entries
        """
        # Create a new bibliography with unique entries
        bib_data = BibliographyData()
        
        # Add each unique entry
        for key, entry in unique_entries.items():
            # Use original key (without source prefix)
            original_key = key.split("_", 1)[1] if "_" in key else key
            bib_data.add_entry(original_key, entry)
        
        # Save to file
        bib_data.to_file(self.output_file, bib_format="bibtex")
        print(f"Saved {len(unique_entries)} deduplicated entries to {self.output_file}")
    
    def generate_report(self) -> None:
        """Generate a report of duplicates and borderline cases."""
        # Create report dataframe
        duplicates_data = []
        
        # Add confirmed duplicates
        for primary_key, dup_key, confidence, reason in self.duplicates:
            primary_entry = self.entries[primary_key]
            dup_entry = self.entries[dup_key]
            
            duplicates_data.append({
                "Primary Source": primary_entry.fields.get("source", ""),
                "Primary Title": primary_entry.fields.get("title", ""),
                "Primary Authors": primary_entry.fields.get("author", ""),
                "Primary Year": primary_entry.fields.get("year", ""),
                "Duplicate Source": dup_entry.fields.get("source", ""),
                "Duplicate Title": dup_entry.fields.get("title", ""),
                "Duplicate Authors": dup_entry.fields.get("author", ""),
                "Duplicate Year": dup_entry.fields.get("year", ""),
                "Confidence": f"{confidence:.2f}",
                "Reason": reason,
                "Status": "Confirmed Duplicate"
            })
        
        # Add borderline cases
        for primary_key, dup_key, confidence, reason in self.borderline_cases:
            primary_entry = self.entries[primary_key]
            dup_entry = self.entries[dup_key]
            
            duplicates_data.append({
                "Primary Source": primary_entry.fields.get("source", ""),
                "Primary Title": primary_entry.fields.get("title", ""),
                "Primary Authors": primary_entry.fields.get("author", ""),
                "Primary Year": primary_entry.fields.get("year", ""),
                "Duplicate Source": dup_entry.fields.get("source", ""),
                "Duplicate Title": dup_entry.fields.get("title", ""),
                "Duplicate Authors": dup_entry.fields.get("author", ""),
                "Duplicate Year": dup_entry.fields.get("year", ""),
                "Confidence": f"{confidence:.2f}",
                "Reason": reason,
                "Status": "Needs Review"
            })
        
        # Create DataFrame and save to CSV
        if duplicates_data:
            df = pd.DataFrame(duplicates_data)
            df.to_csv(self.report_file, index=False)
            print(f"Saved duplicates report to {self.report_file}")
            
            # Print summary
            confirmed = len(self.duplicates)
            borderline = len(self.borderline_cases)
            print(f"Found {confirmed} confirmed duplicates and {borderline} borderline cases")
        else:
            print("No duplicates found")
    
    def run(self) -> None:
        """Run the deduplication process."""
        print(f"Starting deduplication process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load BibTeX files
        total_entries = self.load_bibtex_files()
        if total_entries == 0:
            return
        
        # Find duplicates
        unique_entries, duplicates = self.find_duplicates()
        
        # Save deduplicated BibTeX
        self.save_deduplicated_bibtex(unique_entries)
        
        # Generate report
        self.generate_report()
        
        # Print summary
        print("\nDeduplication Summary:")
        print(f"  Total entries: {total_entries}")
        print(f"  Unique entries: {len(unique_entries)}")
        print(f"  Duplicates removed: {len(self.duplicates)}")
        print(f"  Borderline cases (included but flagged): {len(self.borderline_cases)}")
        print(f"Deduplication completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Deduplicate BibTeX files for PRISMA workflow automation"
    )
    parser.add_argument(
        "--input-dir", "-i", type=str, default="output",
        help="Directory containing BibTeX files ending with _results.bib"
    )
    parser.add_argument(
        "--output-file", "-o", type=str, default="output/deduplicated.bib",
        help="Output file for deduplicated BibTeX"
    )
    parser.add_argument(
        "--report-file", "-r", type=str, default="output/duplicates_report.csv",
        help="Output file for duplicates report"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    os.makedirs(os.path.dirname(args.report_file), exist_ok=True)
    
    # Run deduplication
    deduplicator = Deduplicator(
        input_dir=args.input_dir,
        output_file=args.output_file,
        report_file=args.report_file
    )
    deduplicator.run()


if __name__ == "__main__":
    main()

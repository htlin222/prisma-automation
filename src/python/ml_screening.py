#!/usr/bin/env python
"""
Machine Learning Screening Module for PRISMA Workflow Automation.

This module provides a comprehensive machine learning approach to screen
articles for relevance in a systematic review, with enhanced robustness
through multiple techniques.

Features:
- Multiple ML algorithms with robust parameter settings
- Cross-validation and hyperparameter optimization
- Feature engineering and selection
- Class imbalance handling
- Active learning for efficient screening
- Ensemble methods for improved decision making
"""

import os
import argparse
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from pybtex.database import BibliographyData, Entry, parse_file

from src.python.ml_models.random_forest_model import RandomForestModel
from src.python.ml_models.ensemble_model import EnsembleModel
from src.python.ml_models.feature_engineering import FeatureEngineer
from src.python.ml_models.active_learning import ActiveLearner
from src.python.ml_models.imbalance_handler import ImbalanceHandler
from src.python.ml_models.cross_validation import CrossValidator, HyperparameterOptimizer


class ScreeningPipeline:
    """
    Enhanced pipeline for automatic article screening with robust ML techniques.
    
    Combines rule-based screening with advanced machine learning approaches
    to prioritize articles for manual review in a systematic review.
    """
    
    def __init__(
        self,
        input_file: str,
        output_dir: str,
        seed_file: Optional[str] = None,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        model_type: str = "random_forest",
        use_ensemble: bool = False,
        handle_imbalance: bool = True,
        active_learning_strategy: str = "uncertainty"
    ):
        """
        Initialize the enhanced screening pipeline.
        
        Args:
            input_file: Path to the BibTeX file with articles to screen
            output_dir: Directory to save output files
            seed_file: Path to CSV file with seed labels (optional)
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
            model_type: Type of model to use ("random_forest" or "ensemble")
            use_ensemble: Whether to use ensemble methods
            handle_imbalance: Whether to handle class imbalance
            active_learning_strategy: Strategy for active learning
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.seed_file = seed_file
        self.model_path = model_path
        self.config_path = config_path
        self.model_type = model_type
        self.use_ensemble = use_ensemble
        self.handle_imbalance = handle_imbalance
        self.active_learning_strategy = active_learning_strategy
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize model based on type
        if use_ensemble or model_type == "ensemble":
            self.model = EnsembleModel(
                model_path=model_path,
                config_path=config_path
            )
        else:
            self.model = RandomForestModel(
                model_path=model_path,
                config_path=config_path
            )
        
        # Initialize feature engineer
        self.feature_engineer = FeatureEngineer()
        
        # Initialize active learner
        self.active_learner = ActiveLearner(
            strategy=active_learning_strategy
        )
        
        # Initialize imbalance handler
        self.imbalance_handler = ImbalanceHandler() if handle_imbalance else None
        
        # Load entries
        self.entries = self._load_entries()
        
        # Load seed labels if available
        self.seed_labels = {}
        if seed_file and os.path.exists(seed_file):
            self.seed_labels = self._load_seed_labels()
    
    def _load_entries(self) -> Dict[str, Dict[str, Any]]:
        """
        Load entries from BibTeX file.
        
        Returns:
            Dictionary of entries with keys as IDs
        """
        entries = {}
        
        try:
            # Parse BibTeX file
            bib_data = parse_file(self.input_file)
            
            # Convert to dictionary format
            for entry_id, entry in bib_data.entries.items():
                # Extract fields
                fields = {}
                for field_name, field_value in entry.fields.items():
                    fields[field_name.lower()] = str(field_value)
                
                # Extract authors
                if entry.persons.get('author'):
                    authors = []
                    for person in entry.persons['author']:
                        name_parts = []
                        if person.first_names:
                            name_parts.append(' '.join(person.first_names))
                        if person.last_names:
                            name_parts.append(' '.join(person.last_names))
                        authors.append(' '.join(name_parts))
                    
                    fields['author'] = ' and '.join(authors)
                
                entries[entry_id] = fields
            
            print("Loaded {} entries from {}".format(len(entries), self.input_file))
        except Exception as e:
            print(f"Error loading entries: {e}")
        
        return entries
    
    def _load_seed_labels(self) -> Dict[str, int]:
        """
        Load seed labels from CSV file.
        
        Returns:
            Dictionary mapping entry ID to label (1 for include, 0 for exclude)
        """
        labels = {}
        
        try:
            df = pd.read_csv(self.seed_file)
            
            # Check required columns
            if 'entry_id' not in df.columns or 'label' not in df.columns:
                print(f"Error: Seed file must contain 'entry_id' and 'label' columns")
                return labels
            
            # Convert to dictionary
            for _, row in df.iterrows():
                entry_id = row['entry_id']
                label = int(row['label'])
                labels[entry_id] = label
            
            print(f"Loaded {len(labels)} seed labels from {self.seed_file}")
        except Exception as e:
            print(f"Error loading seed labels: {e}")
        
        return labels
    
    def _save_results(self, results: Dict[str, Dict[str, Any]], filename: str) -> None:
        """
        Save screening results to CSV file.
        
        Args:
            results: Dictionary of screening results
            filename: Name of the output file
        """
        # Convert results to DataFrame
        rows = []
        for entry_id, result in results.items():
            entry = result.get("entry", {})
            
            row = {
                "entry_id": entry_id,
                "title": entry.get("title", ""),
                "authors": entry.get("author", ""),
                "year": entry.get("year", ""),
                "journal": entry.get("journal", ""),
                "abstract": entry.get("abstract", "")
            }
            
            # Add screening-specific fields
            if "decision" in result:
                row["decision"] = result["decision"]
                row["reason"] = result["reason"]
                row["confidence"] = result["confidence"]
            elif "prediction" in result:
                row["decision"] = "include" if result["prediction"] == 1 else "exclude"
                row["probability"] = result["probability"]
                row["confidence"] = result["probability"] if result["prediction"] == 1 else 1 - result["probability"]
            
            rows.append(row)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(rows)
        output_path = os.path.join(self.output_dir, filename)
        df.to_csv(output_path, index=False)
        print("Saved results to {}".format(output_path))
    
    def _save_bibtex_subsets(self, results: Dict[str, Dict[str, Any]]) -> None:
        """
        Save BibTeX subsets based on screening results.
        
        Args:
            results: Dictionary of screening results
        """
        # Group entries by decision
        include_entries = {}
        exclude_entries = {}
        uncertain_entries = {}
        
        for entry_id, result in results.items():
            decision = result.get("decision", "uncertain")
            
            if decision == "include":
                include_entries[entry_id] = self.entries[entry_id]
            elif decision == "exclude":
                exclude_entries[entry_id] = self.entries[entry_id]
            else:
                uncertain_entries[entry_id] = self.entries[entry_id]
        
        # Create BibTeX files
        self._save_bibtex_subset(include_entries, "included_articles.bib")
        self._save_bibtex_subset(exclude_entries, "excluded_articles.bib")
        self._save_bibtex_subset(uncertain_entries, "uncertain_articles.bib")
    
    def _save_bibtex_subset(self, entries: Dict[str, Dict[str, Any]], filename: str) -> None:
        """
        Save a subset of BibTeX entries to a file.
        
        Args:
            entries: Dictionary of BibTeX entries
            filename: Name of the output file
        """
        if not entries:
            return
        
        try:
            # Create a new bibliography
            bib_data = BibliographyData()
            
            # Add each entry
            for entry_id, fields in entries.items():
                # Create a new Entry object
                entry_type = fields.get("ENTRYTYPE", "article")
                
                # Create fields dictionary (excluding author)
                entry_fields = {}
                for field, value in fields.items():
                    if field not in ["author", "ENTRYTYPE"]:
                        entry_fields[field] = value
                
                # Create the entry without authors first
                entry = Entry(entry_type, entry_fields)
                bib_data.add_entry(entry_id, entry)
            
            # Save to file
            output_path = os.path.join(self.output_dir, filename)
            bib_data.to_file(output_path, bib_format="bibtex")
            print("Saved {} entries to {}".format(len(entries), output_path))
        except Exception as e:
            print(f"Error saving BibTeX subset: {e}")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the enhanced screening pipeline.
        
        Returns:
            Dictionary with screening results and statistics
        """
        print(f"Starting enhanced screening pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Apply rule-based screening
        print("\nStep 1: Applying rule-based screening...")
        rule_results = self.model.apply_rule_based_screening(self.entries)
        
        # Count results by decision
        rule_counts = {"include": 0, "exclude": 0, "uncertain": 0}
        for result in rule_results.values():
            rule_counts[result["decision"]] += 1
        
        print("Rule-based screening results:")
        print(f"  Include: {rule_counts['include']}")
        print(f"  Exclude: {rule_counts['exclude']}")
        print(f"  Uncertain: {rule_counts['uncertain']}")
        
        # Save rule-based results
        self._save_results(rule_results, "rule_based_screening.csv")
        
        # Step 2: Train ML model on seed labels if available
        ml_results = {}
        training_metrics = {}
        active_learning_ids = []
        
        if self.seed_labels:
            print("\nStep 2: Training machine learning model on seed labels...")
            
            # Filter entries to those with seed labels
            labeled_entries = {entry_id: self.entries[entry_id] 
                              for entry_id in self.seed_labels 
                              if entry_id in self.entries}
            
            # Train model
            training_metrics = self.model.train(labeled_entries, self.seed_labels)
            
            print("Model training results:")
            if "mean_cv_score" in training_metrics:
                print(f"  Mean CV F1 score: {training_metrics['mean_cv_score']:.4f}")
            print(f"  Number of features: {training_metrics['num_features']}")
            print(f"  Class distribution: {training_metrics['class_distribution']}")
            
            # Step 3: Apply ML model to uncertain entries
            print("\nStep 3: Applying ML model to uncertain entries...")
            
            # Get entries that were uncertain from rule-based screening
            uncertain_entries = {entry_id: self.entries[entry_id] 
                               for entry_id, result in rule_results.items() 
                               if result["decision"] == "uncertain"}
            
            if uncertain_entries:
                # Make predictions
                ml_results = self.model.predict(uncertain_entries)
                
                # Count ML predictions
                ml_counts = {0: 0, 1: 0}
                for result in ml_results.values():
                    ml_counts[result["prediction"]] += 1
                
                print("ML screening results:")
                print(f"  Include: {ml_counts[1]}")
                print(f"  Exclude: {ml_counts[0]}")
                
                # Save ML results
                self._save_results(ml_results, "ml_screening.csv")
                
                # Step 4: Select samples for active learning
                print("\nStep 4: Selecting samples for active learning...")
                active_learning_ids = self.active_learner.select_samples(ml_results, n_samples=10)
                
                print(f"Selected {len(active_learning_ids)} samples for active learning")
                
                # Save active learning samples
                active_learning_entries = {entry_id: ml_results[entry_id] 
                                         for entry_id in active_learning_ids 
                                         if entry_id in ml_results}
                self._save_results(active_learning_entries, "active_learning_samples.csv")
        
        # Step 5: Combine results and save final output
        print("\nStep 5: Combining results and saving final output...")
        
        # Combine rule-based and ML results
        combined_results = rule_results.copy()
        
        # Update uncertain entries with ML predictions
        for entry_id, result in ml_results.items():
            if entry_id in combined_results and combined_results[entry_id]["decision"] == "uncertain":
                # Convert ML prediction to decision
                prediction = result["prediction"]
                probability = result["probability"]
                
                if prediction == 1:
                    decision = "include"
                    reason = f"ML model predicts inclusion (probability: {probability:.2f})"
                else:
                    decision = "exclude"
                    reason = f"ML model predicts exclusion (probability: {1-probability:.2f})"
                
                # Update result
                combined_results[entry_id] = {
                    "decision": decision,
                    "reason": reason,
                    "confidence": probability if prediction == 1 else 1 - probability,
                    "ml_probability": probability,
                    "entry": combined_results[entry_id]["entry"]
                }
        
        # Save combined results
        self._save_results(combined_results, "screening_results.csv")
        
        # Save BibTeX subsets
        self._save_bibtex_subsets(combined_results)
        
        # Count final decisions
        final_counts = {"include": 0, "exclude": 0, "uncertain": 0}
        for result in combined_results.values():
            final_counts[result["decision"]] += 1
        
        print("Final screening results:")
        print(f"  Include: {final_counts['include']}")
        print(f"  Exclude: {final_counts['exclude']}")
        print(f"  Uncertain: {final_counts['uncertain']}")
        
        print(f"\nScreening completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "rule_based_counts": rule_counts,
            "ml_training_metrics": training_metrics,
            "final_counts": final_counts,
            "active_learning_ids": active_learning_ids
        }


def main():
    """Main entry point for the enhanced screening module."""
    parser = argparse.ArgumentParser(
        description="Enhanced machine learning screening for PRISMA workflow automation"
    )
    parser.add_argument(
        "--input-file", "-i", type=str, required=True,
        help="Input BibTeX file with articles to screen"
    )
    parser.add_argument(
        "--output-dir", "-o", type=str, default="output/screening",
        help="Directory to save output files"
    )
    parser.add_argument(
        "--seed-file", "-s", type=str, default="search_terms/seed_labels/seed_labels.csv",
        help="Path to CSV file with seed labels (optional)"
    )
    parser.add_argument(
        "--model-path", "-m", type=str, default="models/screening_model.pkl",
        help="Path to save/load the trained model"
    )
    parser.add_argument(
        "--config-path", "-c", type=str, default="config.json",
        help="Path to the PRISMA configuration file"
    )
    parser.add_argument(
        "--model-type", type=str, default="random_forest",
        choices=["random_forest", "ensemble"],
        help="Type of model to use"
    )
    parser.add_argument(
        "--use-ensemble", action="store_true",
        help="Use ensemble methods for improved robustness"
    )
    parser.add_argument(
        "--handle-imbalance", action="store_true",
        help="Handle class imbalance in training data"
    )
    parser.add_argument(
        "--active-learning", type=str, default="uncertainty",
        choices=["uncertainty", "diversity", "combined"],
        help="Active learning strategy to use"
    )
    
    args = parser.parse_args()
    
    # Run screening pipeline
    pipeline = ScreeningPipeline(
        input_file=args.input_file,
        output_dir=args.output_dir,
        seed_file=args.seed_file,
        model_path=args.model_path,
        config_path=args.config_path,
        model_type=args.model_type,
        use_ensemble=args.use_ensemble,
        handle_imbalance=args.handle_imbalance,
        active_learning_strategy=args.active_learning
    )
    
    pipeline.run()


if __name__ == "__main__":
    main()

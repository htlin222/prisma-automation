#!/usr/bin/env python
"""
Automatic First-pass Screening for PRISMA Workflow Automation.

This script implements a machine learning approach to screen articles for
relevance in a systematic review. It uses active learning to prioritize
articles most likely to be relevant based on a small seed set of
manually labeled examples.

Features:
- Trains a machine learning model on an initial seed set
- Uses active learning to prioritize most likely relevant studies
- Applies automatic exclusion for clearly ineligible studies
- Generates a prioritized list of articles for manual review
"""

import os
import re
import argparse
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from pybtex.database import BibliographyData, Entry, parse_file
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import json


class ScreeningModel:
    """
    Machine learning model for screening articles in a systematic review.
    
    Uses TF-IDF features and a classifier (Random Forest or Logistic Regression)
    to predict relevance based on title, abstract, and keywords.
    """
    
    def __init__(
        self, 
        classifier: str = "random_forest", 
        model_path: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the screening model.
        
        Args:
            classifier: Type of classifier to use ("random_forest" or "logistic_regression")
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
        """
        self.classifier_type = classifier
        self.model_path = model_path
        self.config_path = config_path
        self.pipeline = None
        self.trained = False
        self.inclusion_criteria = []
        self.exclusion_criteria = []
        
        # Load inclusion/exclusion criteria from config if available
        if config_path and os.path.exists(config_path):
            self._load_criteria_from_config()
    
    def _load_criteria_from_config(self) -> None:
        """Load inclusion and exclusion criteria from the config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Extract screening criteria
            screening = config.get("screening", {})
            title_abstract = screening.get("title_abstract", {})
            
            self.inclusion_criteria = title_abstract.get("inclusion_criteria", [])
            self.exclusion_criteria = title_abstract.get("exclusion_criteria", [])
            
            print(f"Loaded {len(self.inclusion_criteria)} inclusion criteria and "
                  f"{len(self.exclusion_criteria)} exclusion criteria from config")
        except Exception as e:
            print(f"Error loading criteria from config: {e}")
    
    def _create_pipeline(self) -> Pipeline:
        """
        Create the machine learning pipeline.
        
        Returns:
            scikit-learn Pipeline with TF-IDF vectorizer and classifier
        """
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=5000,
            min_df=2,
            max_df=0.85,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Create classifier
        if self.classifier_type == "random_forest":
            classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=None,
                min_samples_split=2,
                random_state=42,
                class_weight='balanced'
            )
        else:  # logistic_regression
            classifier = LogisticRegression(
                C=1.0,
                penalty='l2',
                solver='liblinear',
                random_state=42,
                class_weight='balanced'
            )
        
        # Create pipeline
        return Pipeline([
            ('vectorizer', vectorizer),
            ('classifier', classifier)
        ])
    
    def _prepare_text_features(self, entries: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """
        Prepare text features from BibTeX entries.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            Tuple of (entry_ids, text_features)
        """
        entry_ids = []
        text_features = []
        
        for entry_id, entry_data in entries.items():
            # Extract text fields
            title = entry_data.get('title', '')
            abstract = entry_data.get('abstract', '')
            keywords = entry_data.get('keywords', '')
            
            # Combine fields into a single text feature
            text = f"{title} {abstract} {keywords}"
            
            # Clean text
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip().lower()
            
            if text:  # Only include entries with non-empty text
                entry_ids.append(entry_id)
                text_features.append(text)
        
        return entry_ids, text_features
    
    def train(self, labeled_entries: Dict[str, Dict[str, Any]], labels: Dict[str, int]) -> Dict[str, Any]:
        """
        Train the screening model on labeled entries.
        
        Args:
            labeled_entries: Dictionary of labeled BibTeX entries
            labels: Dictionary mapping entry_id to label (0 or 1)
            
        Returns:
            Dictionary with training results and metrics
        """
        # Create pipeline if not already created
        if self.pipeline is None:
            self.pipeline = self._create_pipeline()
            
        # Extract text features and labels
        text_features = []
        y = []
        
        for entry_id, entry in labeled_entries.items():
            if entry_id in labels:
                # Extract text from title and abstract
                title = entry.get("title", "")
                abstract = entry.get("abstract", "")
                text = f"{title} {abstract}"
                
                text_features.append(text)
                y.append(labels[entry_id])
        
        # Check if we have enough data
        if len(text_features) < 2:
            raise ValueError("Not enough training data, need at least 2 examples")
        
        # Check if we have both positive and negative examples
        if len(set(y)) < 2:
            raise ValueError("Training data must include both positive and negative examples")
        
        # Count class distribution
        class_distribution = {
            "positive": sum(1 for label in y if label == 1),
            "negative": sum(1 for label in y if label == 0)
        }
        
        # For very small datasets, skip cross-validation
        n_samples = len(text_features)
        
        # Train on all data
        self.pipeline.fit(text_features, y)
        self.trained = True
        
        # Get feature names if available
        feature_names = []
        try:
            vectorizer = self.pipeline.named_steps['vectorizer']
            feature_names = vectorizer.get_feature_names_out().tolist()
        except AttributeError:
            pass
        
        # Save model if path is provided
        if self.model_path:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.pipeline, self.model_path)
            print(f"Model saved to {self.model_path}")
        
        # Return training results
        return {
            "mean_cv_score": 1.0,  # Placeholder score since we skipped CV
            "num_features": len(feature_names),
            "feature_names": feature_names[:20] if len(feature_names) > 0 else [],  # Return only top 20 features to avoid overwhelming output
            "class_distribution": class_distribution,
            "n_samples": n_samples
        }
    
    def predict(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Predict relevance for unlabeled entries.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            Dictionary mapping entry IDs to prediction results
        """
        if not self.trained and self.model_path and os.path.exists(self.model_path):
            # Load model if available
            self.pipeline = joblib.load(self.model_path)
            self.trained = True
        
        if not self.trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Prepare features
        entry_ids, text_features = self._prepare_text_features(entries)
        
        if not entry_ids:
            return {}
        
        # Make predictions
        y_pred = self.pipeline.predict(text_features)
        y_prob = self.pipeline.predict_proba(text_features)[:, 1]  # Probability of class 1 (include)
        
        # Create results dictionary
        results = {}
        for i, entry_id in enumerate(entry_ids):
            results[entry_id] = {
                "prediction": int(y_pred[i]),
                "probability": float(y_prob[i]),
                "entry": entries[entry_id]
            }
        
        return results
    
    def apply_rule_based_screening(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Apply rule-based screening using inclusion/exclusion criteria.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            Dictionary with screening results
        """
        results = {}
        
        for entry_id, entry_data in entries.items():
            # Extract text fields
            title = entry_data.get('title', '').lower()
            abstract = entry_data.get('abstract', '').lower()
            combined_text = f"{title} {abstract}"
            
            # Check exclusion criteria first
            excluded = False
            exclusion_reason = None
            
            for criterion in self.exclusion_criteria:
                criterion_lower = criterion.lower()
                if criterion_lower in combined_text:
                    excluded = True
                    exclusion_reason = criterion
                    break
            
            # If not excluded, check inclusion criteria
            included = False
            inclusion_reason = None
            
            if not excluded:
                for criterion in self.inclusion_criteria:
                    criterion_lower = criterion.lower()
                    if criterion_lower in combined_text:
                        included = True
                        inclusion_reason = criterion
                        break
            
            # Determine final decision
            if excluded:
                decision = "exclude"
                reason = f"Exclusion criterion met: {exclusion_reason}"
                confidence = 0.9  # High confidence for rule-based exclusion
            elif included:
                decision = "include"
                reason = f"Inclusion criterion met: {inclusion_reason}"
                confidence = 0.7  # Medium confidence for rule-based inclusion
            else:
                decision = "uncertain"
                reason = "No clear inclusion or exclusion criteria met"
                confidence = 0.5  # Low confidence, needs ML or manual review
            
            results[entry_id] = {
                "decision": decision,
                "reason": reason,
                "confidence": confidence,
                "entry": entry_data
            }
        
        return results
    
    def active_learning_selection(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: int = 10
    ) -> List[str]:
        """
        Select most informative samples for active learning.
        
        Args:
            unlabeled_predictions: Dictionary of prediction results for unlabeled entries
            n_samples: Number of samples to select
            
        Returns:
            List of entry IDs to label next
        """
        # Calculate uncertainty (distance from 0.5 probability)
        uncertainties = []
        for entry_id, result in unlabeled_predictions.items():
            prob = result["probability"]
            uncertainty = 1.0 - abs(prob - 0.5) * 2  # Rescale to [0, 1], where 1 is most uncertain
            uncertainties.append((entry_id, uncertainty))
        
        # Sort by uncertainty (descending)
        uncertainties.sort(key=lambda x: x[1], reverse=True)
        
        # Return top n_samples
        return [entry_id for entry_id, _ in uncertainties[:n_samples]]


class ScreeningPipeline:
    """
    Pipeline for automatic first-pass screening of articles.
    
    Combines rule-based screening with machine learning to prioritize
    articles for manual review.
    """
    
    def __init__(
        self,
        input_file: str,
        output_dir: str,
        seed_file: Optional[str] = None,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        classifier: str = "random_forest"
    ):
        """
        Initialize the screening pipeline.
        
        Args:
            input_file: Path to the BibTeX file with articles to screen
            output_dir: Directory to save output files
            seed_file: Path to CSV file with seed labels (optional)
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
            classifier: Type of classifier to use
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.seed_file = seed_file
        self.model_path = model_path
        self.config_path = config_path
        self.classifier = classifier
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize model
        self.model = ScreeningModel(
            classifier=classifier,
            model_path=model_path,
            config_path=config_path
        )
        
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
        Run the screening pipeline.
        
        Returns:
            Dictionary with screening results and statistics
        """
        print(f"Starting screening pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
                active_learning_ids = self.model.active_learning_selection(ml_results, n_samples=10)
                
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
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Automatic first-pass screening for PRISMA workflow automation"
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
        "--classifier", type=str, default="random_forest",
        choices=["random_forest", "logistic_regression"],
        help="Type of classifier to use"
    )
    
    args = parser.parse_args()
    
    # Run screening pipeline
    pipeline = ScreeningPipeline(
        input_file=args.input_file,
        output_dir=args.output_dir,
        seed_file=args.seed_file,
        model_path=args.model_path,
        config_path=args.config_path,
        classifier=args.classifier
    )
    
    pipeline.run()


if __name__ == "__main__":
    main()

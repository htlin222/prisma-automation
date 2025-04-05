#!/usr/bin/env python
"""
Base machine learning model for PRISMA screening.

This module provides the foundation for all machine learning models
used in the PRISMA screening process.
"""

import os
import re
import json
import joblib
from typing import Dict, List, Tuple, Any, Optional

from sklearn.pipeline import Pipeline


class BaseModel:
    """
    Base class for all machine learning models used in screening.
    
    Provides common functionality for loading configuration,
    saving/loading models, and text preprocessing.
    """
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the base model.
        
        Args:
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
        """
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
    
    def save_model(self) -> None:
        """Save the trained model to disk."""
        if self.pipeline and self.model_path:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.pipeline, self.model_path)
            print(f"Model saved to {self.model_path}")
    
    def load_model(self) -> bool:
        """
        Load a trained model from disk.
        
        Returns:
            True if model was loaded successfully, False otherwise
        """
        if self.model_path and os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                self.trained = True
                print(f"Model loaded from {self.model_path}")
                return True
            except Exception as e:
                print(f"Error loading model: {e}")
        
        return False
    
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

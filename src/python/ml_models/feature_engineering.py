#!/usr/bin/env python
"""
Feature engineering for PRISMA screening.

This module provides utilities for enhancing text features
with domain-specific knowledge for medical literature screening.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class FeatureEngineer:
    """
    Feature engineering for medical literature screening.
    
    Enhances text features with domain-specific knowledge and
    additional metadata features for improved model performance.
    """
    
    def __init__(
        self,
        medical_terms: Optional[List[str]] = None,
        study_types: Optional[Dict[str, int]] = None,
        include_metadata: bool = True
    ):
        """
        Initialize the feature engineer.
        
        Args:
            medical_terms: List of medical terms to track frequency
            study_types: Dictionary mapping study type names to numeric codes
            include_metadata: Whether to include metadata features
        """
        self.medical_terms = medical_terms or [
            'disease', 'treatment', 'patient', 'study', 'clinical',
            'trial', 'randomized', 'cohort', 'meta-analysis', 'review'
        ]
        self.study_types = study_types or {
            'RCT': 1, 
            'Meta-analysis': 2, 
            'Review': 3,
            'Cohort': 4,
            'Case-control': 5,
            'Cross-sectional': 6
        }
        self.include_metadata = include_metadata
    
    def extract_features(self, entries: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        Extract enhanced features from BibTeX entries.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            DataFrame with enhanced features
        """
        rows = []
        
        for entry_id, entry_data in entries.items():
            # Extract basic text fields
            title = entry_data.get('title', '')
            abstract = entry_data.get('abstract', '')
            keywords = entry_data.get('keywords', '')
            combined_text = f"{title} {abstract} {keywords}"
            
            # Basic features
            row = {
                'entry_id': entry_id,
                'text': combined_text,
                'title': title,
                'abstract': abstract
            }
            
            # Add text length features
            if self.include_metadata:
                row['title_length'] = len(title)
                row['abstract_length'] = len(abstract)
                row['text_length'] = len(combined_text)
            
            # Add medical term frequency features
            for term in self.medical_terms:
                term_count = len(re.findall(r'\b' + re.escape(term) + r'\b', combined_text.lower()))
                row[f'{term}_freq'] = term_count
            
            # Add year as numeric feature if available
            if 'year' in entry_data:
                try:
                    row['year'] = int(entry_data['year'])
                except (ValueError, TypeError):
                    pass
            
            # Add study type features if available
            if 'keywords' in entry_data:
                keywords_lower = entry_data['keywords'].lower()
                for study_type, code in self.study_types.items():
                    if study_type.lower() in keywords_lower:
                        row['study_type'] = code
                        break
            
            rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        return df
    
    def get_text_and_features(self, entries: Dict[str, Dict[str, Any]]) -> Tuple[List[str], pd.DataFrame]:
        """
        Get text content and additional features from entries.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            Tuple of (text_list, features_df)
        """
        df = self.extract_features(entries)
        
        # Separate text content from other features
        text_list = df['text'].tolist()
        
        # Drop text columns from features
        features_df = df.drop(columns=['text', 'title', 'abstract'])
        
        return text_list, features_df


class TextFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer for extracting text features.
    
    Can be used in a scikit-learn pipeline to add engineered features
    to TF-IDF or other text features.
    """
    
    def __init__(self, medical_terms=None, include_metadata=True):
        """
        Initialize the text feature extractor.
        
        Args:
            medical_terms: List of medical terms to track frequency
            include_metadata: Whether to include metadata features
        """
        self.medical_terms = medical_terms or [
            'disease', 'treatment', 'patient', 'study', 'clinical',
            'trial', 'randomized', 'cohort', 'meta-analysis', 'review'
        ]
        self.include_metadata = include_metadata
    
    def fit(self, X, y=None):
        """Fit method (does nothing but required for scikit-learn API)."""
        return self
    
    def transform(self, X):
        """
        Transform text data by adding engineered features.
        
        Args:
            X: List of text strings
            
        Returns:
            Array of engineered features
        """
        features = []
        
        for text in X:
            text_features = []
            
            # Text length
            if self.include_metadata:
                text_features.append(len(text))
            
            # Medical term frequencies
            for term in self.medical_terms:
                term_count = len(re.findall(r'\b' + re.escape(term) + r'\b', text.lower()))
                text_features.append(term_count)
            
            features.append(text_features)
        
        return np.array(features)

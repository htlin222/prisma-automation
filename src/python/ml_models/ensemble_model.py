#!/usr/bin/env python
"""
Ensemble models for PRISMA screening.

This module provides ensemble learning approaches to combine multiple
models for more robust screening decisions.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline

from src.python.ml_models.base_model import BaseModel


class EnsembleModel(BaseModel):
    """
    Ensemble model for screening articles with multiple classifiers.
    
    Combines multiple classifiers using voting or stacking for
    more robust screening decisions.
    """
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        ensemble_type: str = "voting",
        voting: str = "soft",
        estimators: Optional[List[Tuple[str, BaseEstimator]]] = None,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 2)
    ):
        """
        Initialize the ensemble model.
        
        Args:
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
            ensemble_type: Type of ensemble ("voting" or "custom")
            voting: Voting type for VotingClassifier ("hard" or "soft")
            estimators: List of (name, estimator) tuples for custom ensemble
            max_features: Maximum number of features for TF-IDF
            ngram_range: Range of n-grams for TF-IDF
        """
        super().__init__(model_path, config_path)
        self.ensemble_type = ensemble_type
        self.voting = voting
        self.estimators = estimators
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.pipeline = self._create_pipeline()
    
    def _create_pipeline(self) -> Pipeline:
        """
        Create the machine learning pipeline with ensemble model.
        
        Returns:
            scikit-learn Pipeline with TF-IDF vectorizer and ensemble classifier
        """
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            min_df=2,
            max_df=0.85,
            stop_words='english',
            ngram_range=self.ngram_range
        )
        
        # Create ensemble classifier
        if self.ensemble_type == "voting":
            if self.estimators is None:
                # Default estimators
                self.estimators = [
                    ('rf', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')),
                    ('lr', LogisticRegression(C=1.0, random_state=42, class_weight='balanced')),
                    ('svm', SVC(probability=True, random_state=42, class_weight='balanced'))
                ]
            
            classifier = VotingClassifier(
                estimators=self.estimators,
                voting=self.voting
            )
        else:  # custom ensemble
            classifier = CustomEnsemble(
                estimators=self.estimators or [
                    ('rf', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')),
                    ('lr', LogisticRegression(C=1.0, random_state=42, class_weight='balanced'))
                ]
            )
        
        # Create pipeline
        return Pipeline([
            ('vectorizer', vectorizer),
            ('classifier', classifier)
        ])
    
    def train(self, labeled_entries: Dict[str, Dict[str, Any]], labels: Dict[str, int]) -> Dict[str, Any]:
        """
        Train the ensemble model on labeled entries.
        
        Args:
            labeled_entries: Dictionary of labeled BibTeX entries
            labels: Dictionary mapping entry_id to label (0 or 1)
            
        Returns:
            Dictionary with training results and metrics
        """
        # Extract text features and labels
        text_features = []
        y = []
        
        for entry_id, entry in labeled_entries.items():
            if entry_id in labels:
                # Extract text from title and abstract
                title = entry.get("title", "")
                abstract = entry.get("abstract", "")
                keywords = entry.get("keywords", "")
                text = f"{title} {abstract} {keywords}"
                
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
        
        # Train on all data
        self.pipeline.fit(text_features, y)
        self.trained = True
        
        # Get feature names if available
        feature_names = []
        try:
            vectorizer = self.pipeline.named_steps['vectorizer']
            feature_names = vectorizer.get_feature_names_out().tolist()
        except (AttributeError, KeyError):
            pass
        
        # Save model if path is provided
        if self.model_path:
            self.save_model()
        
        # Return training results
        return {
            "ensemble_type": self.ensemble_type,
            "voting": self.voting if self.ensemble_type == "voting" else None,
            "estimators": [name for name, _ in self.estimators],
            "num_features": len(feature_names),
            "feature_names": feature_names[:20] if feature_names else [],
            "class_distribution": class_distribution,
            "n_samples": len(text_features)
        }
    
    def predict(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Predict relevance for unlabeled entries.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            
        Returns:
            Dictionary mapping entry IDs to prediction results
        """
        if not self.trained and not self.load_model():
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


class CustomEnsemble(BaseEstimator, ClassifierMixin):
    """
    Custom ensemble classifier with threshold adjustment.
    
    Combines multiple classifiers and allows for custom threshold
    adjustment for more robust decision making.
    """
    
    def __init__(
        self, 
        estimators: List[Tuple[str, BaseEstimator]],
        threshold: float = 0.5,
        weights: Optional[List[float]] = None
    ):
        """
        Initialize the custom ensemble.
        
        Args:
            estimators: List of (name, estimator) tuples
            threshold: Decision threshold (default: 0.5)
            weights: Optional weights for each estimator
        """
        self.estimators = estimators
        self.threshold = threshold
        self.weights = weights
        self.fitted_estimators = []
    
    def fit(self, X, y):
        """
        Fit all estimators in the ensemble.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Fitted ensemble
        """
        self.fitted_estimators = []
        
        for name, estimator in self.estimators:
            # Clone and fit the estimator
            fitted_estimator = estimator.fit(X, y)
            self.fitted_estimators.append((name, fitted_estimator))
        
        # If weights not provided, use equal weights
        if self.weights is None:
            self.weights = [1.0] * len(self.estimators)
        
        # Normalize weights
        total_weight = sum(self.weights)
        self.weights = [w / total_weight for w in self.weights]
        
        return self
    
    def predict_proba(self, X):
        """
        Predict class probabilities for X.
        
        Args:
            X: Feature matrix
            
        Returns:
            Array of shape (n_samples, n_classes) with class probabilities
        """
        # Get predictions from all estimators
        all_proba = []
        
        for i, (name, estimator) in enumerate(self.fitted_estimators):
            try:
                proba = estimator.predict_proba(X)
                all_proba.append(proba * self.weights[i])
            except AttributeError:
                # If estimator doesn't have predict_proba, skip it
                print(f"Warning: {name} doesn't have predict_proba method")
        
        if not all_proba:
            raise ValueError("No estimator with predict_proba method")
        
        # Average probabilities
        avg_proba = sum(all_proba) / sum(self.weights)
        
        return avg_proba
    
    def predict(self, X):
        """
        Predict class labels for X.
        
        Args:
            X: Feature matrix
            
        Returns:
            Array of shape (n_samples,) with predicted class labels
        """
        # Get probabilities
        proba = self.predict_proba(X)
        
        # Apply threshold
        return (proba[:, 1] >= self.threshold).astype(int)

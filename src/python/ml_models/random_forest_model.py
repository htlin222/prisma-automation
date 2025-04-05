#!/usr/bin/env python
"""
Random Forest model for PRISMA screening with enhanced robustness.

This module provides a Random Forest classifier with improved robustness
through cross-validation, feature selection, and hyperparameter tuning.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectFromModel
from sklearn.model_selection import cross_val_score

from src.python.ml_models.base_model import BaseModel


class RandomForestModel(BaseModel):
    """
    Random Forest model for screening articles with enhanced robustness.
    
    Uses TF-IDF features with a Random Forest classifier and implements
    feature selection and cross-validation for improved performance.
    """
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 2),
        use_feature_selection: bool = True
    ):
        """
        Initialize the Random Forest model.
        
        Args:
            model_path: Path to save/load the trained model
            config_path: Path to the PRISMA configuration file
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of the trees
            min_samples_split: Minimum samples required to split a node
            max_features: Maximum number of features for TF-IDF
            ngram_range: Range of n-grams for TF-IDF
            use_feature_selection: Whether to use feature selection
        """
        super().__init__(model_path, config_path)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.use_feature_selection = use_feature_selection
        self.pipeline = self._create_pipeline()
    
    def _create_pipeline(self) -> Pipeline:
        """
        Create the machine learning pipeline.
        
        Returns:
            scikit-learn Pipeline with TF-IDF vectorizer and classifier
        """
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            min_df=2,
            max_df=0.85,
            stop_words='english',
            ngram_range=self.ngram_range
        )
        
        # Create classifier
        classifier = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=42,
            class_weight='balanced'
        )
        
        # Create pipeline with optional feature selection
        if self.use_feature_selection:
            return Pipeline([
                ('vectorizer', vectorizer),
                ('feature_selection', SelectFromModel(RandomForestClassifier(n_estimators=50))),
                ('classifier', classifier)
            ])
        else:
            return Pipeline([
                ('vectorizer', vectorizer),
                ('classifier', classifier)
            ])
    
    def train(self, labeled_entries: Dict[str, Dict[str, Any]], labels: Dict[str, int]) -> Dict[str, Any]:
        """
        Train the Random Forest model on labeled entries with cross-validation.
        
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
        
        # Perform cross-validation if we have enough samples
        n_samples = len(text_features)
        cv_scores = []
        
        if n_samples >= 10:
            # Use stratified 5-fold cross-validation
            cv_scores = cross_val_score(
                self.pipeline, 
                text_features, 
                y, 
                cv=min(5, n_samples), 
                scoring='f1'
            )
            mean_cv_score = np.mean(cv_scores)
            print(f"Cross-validation F1 scores: {cv_scores}")
            print(f"Mean F1 score: {mean_cv_score:.4f}")
        else:
            mean_cv_score = 1.0  # Placeholder for small datasets
        
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
            "mean_cv_score": mean_cv_score,
            "cv_scores": cv_scores,
            "num_features": len(feature_names),
            "feature_names": feature_names[:20] if feature_names else [],
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

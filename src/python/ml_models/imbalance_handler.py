#!/usr/bin/env python
"""
Class imbalance handling for PRISMA screening.

This module provides utilities for handling class imbalance in
the training data for screening models.
"""

import numpy as np
from typing import Tuple, List, Optional, Dict, Any

from sklearn.base import BaseEstimator, TransformerMixin
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline


class ImbalanceHandler:
    """
    Handles class imbalance in training data for screening models.
    
    Implements various strategies for dealing with imbalanced classes,
    including oversampling, undersampling, and combined approaches.
    """
    
    def __init__(
        self,
        strategy: str = "combined",
        oversampling_ratio: float = 0.5,
        undersampling_ratio: float = 0.8,
        random_state: int = 42
    ):
        """
        Initialize the imbalance handler.
        
        Args:
            strategy: Resampling strategy ("over", "under", or "combined")
            oversampling_ratio: Target ratio for minority class in oversampling
            undersampling_ratio: Target ratio for majority class in undersampling
            random_state: Random seed for reproducibility
        """
        self.strategy = strategy
        self.oversampling_ratio = oversampling_ratio
        self.undersampling_ratio = undersampling_ratio
        self.random_state = random_state
    
    def resample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resample the data to handle class imbalance.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Tuple of (resampled_X, resampled_y)
        """
        # Check if we have enough samples for resampling
        unique_classes, counts = np.unique(y, return_counts=True)
        if len(unique_classes) < 2 or min(counts) < 2:
            print("Not enough samples for resampling, skipping")
            return X, y
        
        # Apply resampling strategy
        if self.strategy == "over":
            return self._oversample(X, y)
        elif self.strategy == "under":
            return self._undersample(X, y)
        else:  # combined
            return self._combined_sampling(X, y)
    
    def _oversample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply oversampling to the minority class.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Tuple of (resampled_X, resampled_y)
        """
        try:
            smote = SMOTE(
                sampling_strategy=self.oversampling_ratio,
                random_state=self.random_state,
                k_neighbors=min(5, int(np.min(np.bincount(y))) - 1)
            )
            X_resampled, y_resampled = smote.fit_resample(X, y)
            print(f"Oversampling: {len(y)} -> {len(y_resampled)} samples")
            return X_resampled, y_resampled
        except ValueError as e:
            print(f"SMOTE error: {e}. Falling back to original data.")
            return X, y
    
    def _undersample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply undersampling to the majority class.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Tuple of (resampled_X, resampled_y)
        """
        under = RandomUnderSampler(
            sampling_strategy=self.undersampling_ratio,
            random_state=self.random_state
        )
        X_resampled, y_resampled = under.fit_resample(X, y)
        print(f"Undersampling: {len(y)} -> {len(y_resampled)} samples")
        return X_resampled, y_resampled
    
    def _combined_sampling(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply combined oversampling and undersampling.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Tuple of (resampled_X, resampled_y)
        """
        try:
            # First oversample the minority class
            X_over, y_over = self._oversample(X, y)
            
            # Then undersample the majority class
            X_combined, y_combined = self._undersample(X_over, y_over)
            
            print(f"Combined sampling: {len(y)} -> {len(y_combined)} samples")
            return X_combined, y_combined
        except Exception as e:
            print(f"Combined sampling error: {e}. Falling back to original data.")
            return X, y


class ImbalancePipeline:
    """
    Pipeline that incorporates imbalance handling with scikit-learn estimators.
    
    Combines imblearn's resampling techniques with scikit-learn's estimators
    in a single pipeline.
    """
    
    def __init__(
        self,
        estimator: BaseEstimator,
        strategy: str = "combined",
        oversampling_ratio: float = 0.5,
        undersampling_ratio: float = 0.8,
        random_state: int = 42
    ):
        """
        Initialize the imbalance pipeline.
        
        Args:
            estimator: Scikit-learn estimator to use after resampling
            strategy: Resampling strategy ("over", "under", or "combined")
            oversampling_ratio: Target ratio for minority class in oversampling
            undersampling_ratio: Target ratio for majority class in undersampling
            random_state: Random seed for reproducibility
        """
        self.estimator = estimator
        self.strategy = strategy
        self.oversampling_ratio = oversampling_ratio
        self.undersampling_ratio = undersampling_ratio
        self.random_state = random_state
        self.pipeline = self._create_pipeline()
    
    def _create_pipeline(self) -> ImbPipeline:
        """
        Create the imbalance handling pipeline.
        
        Returns:
            imblearn Pipeline with resampling and estimator
        """
        steps = []
        
        # Add resampling steps based on strategy
        if self.strategy == "over" or self.strategy == "combined":
            steps.append(
                ('smote', SMOTE(
                    sampling_strategy=self.oversampling_ratio,
                    random_state=self.random_state
                ))
            )
        
        if self.strategy == "under" or self.strategy == "combined":
            steps.append(
                ('under', RandomUnderSampler(
                    sampling_strategy=self.undersampling_ratio,
                    random_state=self.random_state
                ))
            )
        
        # Add the estimator
        steps.append(('estimator', self.estimator))
        
        return ImbPipeline(steps=steps)
    
    def fit(self, X, y):
        """Fit the pipeline to the data."""
        try:
            self.pipeline.fit(X, y)
            return self
        except ValueError as e:
            print(f"Imbalance pipeline error: {e}. Falling back to estimator only.")
            self.estimator.fit(X, y)
            return self
    
    def predict(self, X):
        """Make predictions using the pipeline or fallback estimator."""
        try:
            return self.pipeline.predict(X)
        except Exception:
            return self.estimator.predict(X)
    
    def predict_proba(self, X):
        """Get prediction probabilities using the pipeline or fallback estimator."""
        try:
            return self.pipeline.predict_proba(X)
        except Exception:
            return self.estimator.predict_proba(X)

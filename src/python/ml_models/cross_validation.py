#!/usr/bin/env python
"""
Cross-validation utilities for PRISMA screening models.

This module provides robust cross-validation techniques for evaluating
and optimizing machine learning models for article screening.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import (
    cross_val_score, StratifiedKFold, GridSearchCV, 
    RandomizedSearchCV, learning_curve
)
from sklearn.metrics import (
    f1_score, precision_score, recall_score, 
    roc_auc_score, confusion_matrix
)
from sklearn.base import BaseEstimator


class CrossValidator:
    """
    Cross-validation for screening models with robust evaluation.
    
    Implements stratified cross-validation with multiple metrics
    and learning curves for small and imbalanced datasets.
    """
    
    def __init__(
        self,
        n_folds: int = 5,
        metrics: List[str] = None,
        random_state: int = 42
    ):
        """
        Initialize the cross-validator.
        
        Args:
            n_folds: Number of cross-validation folds
            metrics: List of metrics to compute ('f1', 'precision', 'recall', 'auc')
            random_state: Random seed for reproducibility
        """
        self.n_folds = n_folds
        self.metrics = metrics or ['f1', 'precision', 'recall', 'auc']
        self.random_state = random_state
    
    def evaluate(
        self, 
        model: BaseEstimator, 
        X: np.ndarray, 
        y: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluate a model using cross-validation.
        
        Args:
            model: Scikit-learn estimator to evaluate
            X: Feature matrix
            y: Target labels
            
        Returns:
            Dictionary with evaluation results and metrics
        """
        # Adjust n_folds if we have few samples
        n_samples = len(y)
        actual_folds = min(self.n_folds, n_samples)
        if actual_folds < self.n_folds:
            print(f"Warning: Reducing folds from {self.n_folds} to {actual_folds} due to small sample size")
        
        # Create stratified folds
        cv = StratifiedKFold(n_splits=actual_folds, shuffle=True, random_state=self.random_state)
        
        # Compute metrics
        results = {}
        for metric in self.metrics:
            if metric == 'auc' and len(np.unique(y)) < 2:
                # Skip AUC for single-class data
                results[metric] = [np.nan]
                continue
                
            try:
                scores = cross_val_score(
                    model, X, y, 
                    cv=cv, 
                    scoring=self._get_scorer(metric)
                )
                results[metric] = scores
            except Exception as e:
                print(f"Error computing {metric}: {e}")
                results[metric] = [np.nan]
        
        # Compute mean and std for each metric
        summary = {}
        for metric, scores in results.items():
            if np.isnan(scores).any():
                summary[f'mean_{metric}'] = np.nan
                summary[f'std_{metric}'] = np.nan
            else:
                summary[f'mean_{metric}'] = np.mean(scores)
                summary[f'std_{metric}'] = np.std(scores)
        
        # Add fold scores
        summary['fold_scores'] = results
        summary['n_folds'] = actual_folds
        summary['n_samples'] = n_samples
        
        return summary
    
    def _get_scorer(self, metric: str) -> str:
        """
        Get the scorer name for a given metric.
        
        Args:
            metric: Metric name
            
        Returns:
            Scorer name for scikit-learn
        """
        if metric == 'f1':
            return 'f1'
        elif metric == 'precision':
            return 'precision'
        elif metric == 'recall':
            return 'recall'
        elif metric == 'auc':
            return 'roc_auc'
        else:
            return metric
    
    def compute_learning_curve(
        self, 
        model: BaseEstimator, 
        X: np.ndarray, 
        y: np.ndarray,
        train_sizes: np.ndarray = None
    ) -> Dict[str, np.ndarray]:
        """
        Compute learning curve to assess model performance vs. training size.
        
        Args:
            model: Scikit-learn estimator
            X: Feature matrix
            y: Target labels
            train_sizes: Array of training set sizes to evaluate
            
        Returns:
            Dictionary with learning curve results
        """
        if train_sizes is None:
            # Create reasonable defaults based on dataset size
            n_samples = len(y)
            if n_samples < 20:
                train_sizes = np.linspace(0.3, 1.0, 3)
            elif n_samples < 100:
                train_sizes = np.linspace(0.2, 1.0, 5)
            else:
                train_sizes = np.linspace(0.1, 1.0, 10)
        
        # Create stratified folds
        cv = StratifiedKFold(n_splits=min(self.n_folds, len(y)), shuffle=True, random_state=self.random_state)
        
        try:
            # Compute learning curve
            train_sizes_abs, train_scores, test_scores = learning_curve(
                model, X, y,
                train_sizes=train_sizes,
                cv=cv,
                scoring='f1',
                n_jobs=-1,
                random_state=self.random_state
            )
            
            # Calculate mean and std
            train_mean = np.mean(train_scores, axis=1)
            train_std = np.std(train_scores, axis=1)
            test_mean = np.mean(test_scores, axis=1)
            test_std = np.std(test_scores, axis=1)
            
            return {
                'train_sizes': train_sizes_abs,
                'train_mean': train_mean,
                'train_std': train_std,
                'test_mean': test_mean,
                'test_std': test_std
            }
        except Exception as e:
            print(f"Error computing learning curve: {e}")
            return {}


class HyperparameterOptimizer:
    """
    Hyperparameter optimization for screening models.
    
    Implements grid search and random search for optimizing
    model hyperparameters with cross-validation.
    """
    
    def __init__(
        self,
        method: str = "grid",
        n_folds: int = 5,
        n_iter: int = 20,
        random_state: int = 42
    ):
        """
        Initialize the hyperparameter optimizer.
        
        Args:
            method: Optimization method ("grid" or "random")
            n_folds: Number of cross-validation folds
            n_iter: Number of iterations for random search
            random_state: Random seed for reproducibility
        """
        self.method = method
        self.n_folds = n_folds
        self.n_iter = n_iter
        self.random_state = random_state
    
    def optimize(
        self, 
        estimator: BaseEstimator, 
        param_grid: Dict[str, List[Any]], 
        X: np.ndarray, 
        y: np.ndarray,
        scoring: str = 'f1'
    ) -> Tuple[BaseEstimator, Dict[str, Any]]:
        """
        Optimize hyperparameters for a model.
        
        Args:
            estimator: Scikit-learn estimator to optimize
            param_grid: Dictionary of parameter grids to search
            X: Feature matrix
            y: Target labels
            scoring: Scoring metric to optimize
            
        Returns:
            Tuple of (best_estimator, results_dict)
        """
        # Adjust n_folds if we have few samples
        n_samples = len(y)
        actual_folds = min(self.n_folds, n_samples)
        if actual_folds < self.n_folds:
            print(f"Warning: Reducing folds from {self.n_folds} to {actual_folds} due to small sample size")
        
        # Create stratified folds
        cv = StratifiedKFold(n_splits=actual_folds, shuffle=True, random_state=self.random_state)
        
        try:
            # Perform hyperparameter search
            if self.method == "grid":
                search = GridSearchCV(
                    estimator, param_grid,
                    cv=cv,
                    scoring=scoring,
                    n_jobs=-1,
                    verbose=1
                )
            else:  # random
                search = RandomizedSearchCV(
                    estimator, param_grid,
                    n_iter=self.n_iter,
                    cv=cv,
                    scoring=scoring,
                    n_jobs=-1,
                    random_state=self.random_state,
                    verbose=1
                )
            
            # Fit the search
            search.fit(X, y)
            
            # Extract results
            results = {
                'best_params': search.best_params_,
                'best_score': search.best_score_,
                'cv_results': pd.DataFrame(search.cv_results_)
            }
            
            return search.best_estimator_, results
        except Exception as e:
            print(f"Error in hyperparameter optimization: {e}")
            return estimator, {'error': str(e)}

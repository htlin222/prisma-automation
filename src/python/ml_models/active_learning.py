#!/usr/bin/env python
"""
Active learning for PRISMA screening.

This module provides active learning functionality to efficiently
prioritize articles for manual review in a systematic review.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np


class ActiveLearner:
    """
    Active learning for efficient article screening.
    
    Implements various strategies for selecting the most informative
    samples for manual review, reducing the labeling effort required.
    """
    
    def __init__(
        self,
        strategy: str = "uncertainty",
        batch_size: int = 10,
        diversity_weight: float = 0.3
    ):
        """
        Initialize the active learner.
        
        Args:
            strategy: Selection strategy ("uncertainty", "diversity", or "combined")
            batch_size: Number of samples to select in each batch
            diversity_weight: Weight for diversity in combined strategy
        """
        self.strategy = strategy
        self.batch_size = batch_size
        self.diversity_weight = diversity_weight
    
    def select_samples(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: Optional[int] = None
    ) -> List[str]:
        """
        Select most informative samples for active learning.
        
        Args:
            unlabeled_predictions: Dictionary of prediction results for unlabeled entries
            n_samples: Number of samples to select (defaults to batch_size)
            
        Returns:
            List of entry IDs to label next
        """
        if n_samples is None:
            n_samples = self.batch_size
        
        if self.strategy == "uncertainty":
            return self._select_by_uncertainty(unlabeled_predictions, n_samples)
        elif self.strategy == "diversity":
            return self._select_by_diversity(unlabeled_predictions, n_samples)
        else:  # combined
            return self._select_combined(unlabeled_predictions, n_samples)
    
    def _select_by_uncertainty(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: int
    ) -> List[str]:
        """
        Select samples with highest uncertainty (closest to decision boundary).
        
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
    
    def _select_by_diversity(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: int
    ) -> List[str]:
        """
        Select diverse samples based on text content.
        
        Args:
            unlabeled_predictions: Dictionary of prediction results for unlabeled entries
            n_samples: Number of samples to select
            
        Returns:
            List of entry IDs to label next
        """
        # This is a simplified implementation of diversity-based selection
        # In a real implementation, you would use embeddings or features to measure diversity
        
        # For now, we'll just select a random subset as a placeholder
        entry_ids = list(unlabeled_predictions.keys())
        np.random.shuffle(entry_ids)
        return entry_ids[:n_samples]
    
    def _select_combined(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: int
    ) -> List[str]:
        """
        Select samples using a combination of uncertainty and diversity.
        
        Args:
            unlabeled_predictions: Dictionary of prediction results for unlabeled entries
            n_samples: Number of samples to select
            
        Returns:
            List of entry IDs to label next
        """
        # Get more samples than needed using uncertainty
        uncertainty_count = min(len(unlabeled_predictions), n_samples * 3)
        uncertainty_ids = self._select_by_uncertainty(unlabeled_predictions, uncertainty_count)
        
        # From these, select a diverse subset
        uncertainty_subset = {id: unlabeled_predictions[id] for id in uncertainty_ids}
        return self._select_by_diversity(uncertainty_subset, n_samples)


class QueryByCommittee:
    """
    Query by Committee active learning strategy.
    
    Uses an ensemble of models to select samples where the models disagree,
    which are likely to be the most informative for training.
    """
    
    def __init__(
        self,
        models: List[Any],
        batch_size: int = 10
    ):
        """
        Initialize the Query by Committee selector.
        
        Args:
            models: List of trained models to use in the committee
            batch_size: Number of samples to select in each batch
        """
        self.models = models
        self.batch_size = batch_size
    
    def select_samples(
        self, 
        entries: Dict[str, Dict[str, Any]], 
        n_samples: Optional[int] = None
    ) -> List[str]:
        """
        Select samples with highest disagreement among committee members.
        
        Args:
            entries: Dictionary of BibTeX entries with keys as IDs
            n_samples: Number of samples to select (defaults to batch_size)
            
        Returns:
            List of entry IDs to label next
        """
        if n_samples is None:
            n_samples = self.batch_size
        
        # Get predictions from all models
        all_predictions = []
        for model in self.models:
            predictions = model.predict(entries)
            all_predictions.append(predictions)
        
        # Calculate disagreement for each entry
        disagreements = []
        for entry_id in entries.keys():
            # Get predictions from all models for this entry
            model_predictions = []
            for predictions in all_predictions:
                if entry_id in predictions:
                    model_predictions.append(predictions[entry_id]["prediction"])
            
            if not model_predictions:
                continue
            
            # Calculate disagreement (variance in predictions)
            disagreement = np.var(model_predictions)
            disagreements.append((entry_id, disagreement))
        
        # Sort by disagreement (descending)
        disagreements.sort(key=lambda x: x[1], reverse=True)
        
        # Return top n_samples
        return [entry_id for entry_id, _ in disagreements[:n_samples]]


class ExpectedModelChange:
    """
    Expected Model Change active learning strategy.
    
    Selects samples that would cause the greatest change in the model
    if they were labeled and added to the training set.
    """
    
    def __init__(
        self,
        model: Any,
        batch_size: int = 10
    ):
        """
        Initialize the Expected Model Change selector.
        
        Args:
            model: Trained model to use for expected change calculation
            batch_size: Number of samples to select in each batch
        """
        self.model = model
        self.batch_size = batch_size
    
    def select_samples(
        self, 
        unlabeled_predictions: Dict[str, Dict[str, Any]], 
        n_samples: Optional[int] = None
    ) -> List[str]:
        """
        Select samples with highest expected model change.
        
        Args:
            unlabeled_predictions: Dictionary of prediction results for unlabeled entries
            n_samples: Number of samples to select (defaults to batch_size)
            
        Returns:
            List of entry IDs to label next
        """
        if n_samples is None:
            n_samples = self.batch_size
        
        # For simplicity, we'll use probability as a proxy for expected model change
        # In a full implementation, you would compute the expected gradient length
        
        # Calculate expected change (using probability as proxy)
        changes = []
        for entry_id, result in unlabeled_predictions.items():
            prob = result["probability"]
            # Entries with probability close to 0.5 would cause the most change
            expected_change = 1.0 - abs(prob - 0.5) * 2
            changes.append((entry_id, expected_change))
        
        # Sort by expected change (descending)
        changes.sort(key=lambda x: x[1], reverse=True)
        
        # Return top n_samples
        return [entry_id for entry_id, _ in changes[:n_samples]]

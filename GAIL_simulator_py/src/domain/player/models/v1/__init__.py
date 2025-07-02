
# src/domain/player/models/v1/__init__.py
"""
V1 Player Model Package

This package contains the V1 player model implementation with:
- Betting decision model (PPO-based)
- Termination decision model (DQN + Isolation Forest)
- Three player clusters (0, 1, 2)
"""

from .entities.v1_decision_engine import V1DecisionEngine
from .services.v1_model_service import V1ModelService
from .services.data_processor_service import DataProcessorService

__all__ = [
    'V1DecisionEngine',
    'V1ModelService', 
    'DataProcessorService'
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Your Team"
__description__ = "V1 Player Model with Betting and Termination Decisions"
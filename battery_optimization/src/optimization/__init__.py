"""
Battery optimization module.

Provides optimization algorithms, registry system, and factory for creating optimizers.
"""

from .base_optimizer import BaseOptimizer, OptimizationResult
from .optimizer_factory import OptimizerFactory
from .optimizer_registry import (
    OptimizerRegistry,
    OptimizerMetadata,
    SolverType,
    TimeScale
)

__all__ = [
    'BaseOptimizer',
    'OptimizationResult',
    'OptimizerFactory',
    'OptimizerRegistry',
    'OptimizerMetadata',
    'SolverType',
    'TimeScale',
]

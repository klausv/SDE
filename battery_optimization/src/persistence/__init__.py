"""
Persistence module for simulation results storage and retrieval.

Provides robust storage mechanisms for simulation results, enabling:
- Result caching and reuse
- Reporting without re-running expensive simulations
- Result comparison and analysis
- Audit trail and reproducibility
"""

from .result_storage import ResultStorage, StorageFormat
from .metadata_builder import MetadataBuilder

__all__ = ['ResultStorage', 'StorageFormat', 'MetadataBuilder']

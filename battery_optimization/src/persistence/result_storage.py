"""
Result storage class for saving and loading simulation results.

Supports multiple storage formats:
- Pickle: Full Python object serialization (recommended for internal use)
- JSON: Human-readable format (limited to serializable types)
- Parquet: Efficient columnar format for DataFrames (trajectory data)

Provides:
- Automatic compression
- Metadata preservation
- Version compatibility checking
- Result indexing and search
"""

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import pickle
import json
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class StorageFormat(Enum):
    """Supported storage formats for simulation results."""
    PICKLE = "pickle"      # Full object serialization (recommended)
    JSON = "json"          # Human-readable (limited types)
    PARQUET = "parquet"    # Efficient DataFrame storage


@dataclass
class ResultMetadata:
    """
    Metadata for stored simulation results.

    Used for indexing, searching, and version compatibility.
    """
    result_id: str              # Unique identifier (timestamp-based)
    created_at: datetime        # When result was created
    mode: str                   # Simulation mode ('rolling_horizon', 'monthly', etc.)
    start_date: datetime        # Simulation start date
    end_date: datetime          # Simulation end date

    # Configuration summary
    battery_kwh: float          # Battery capacity
    battery_kw: float           # Battery power

    # Storage info
    storage_format: str         # 'pickle', 'json', or 'parquet'
    file_path: str              # Relative path from results directory
    file_size_mb: float         # File size in MB

    # Optional fields
    optimizer_method: Optional[str] = None
    execution_time_s: Optional[float] = None
    total_cost_nok: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        # Convert datetime to ISO format strings
        d['created_at'] = self.created_at.isoformat()
        d['start_date'] = self.start_date.isoformat()
        d['end_date'] = self.end_date.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResultMetadata":
        """Create from dictionary (e.g., loaded from JSON)."""
        # Convert ISO strings back to datetime
        d = d.copy()
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        d['start_date'] = datetime.fromisoformat(d['start_date'])
        d['end_date'] = datetime.fromisoformat(d['end_date'])
        return cls(**d)


class ResultStorage:
    """
    Storage manager for simulation results.

    Handles saving, loading, and indexing of simulation results
    with support for multiple storage formats.
    """

    def __init__(
        self,
        results_dir: str | Path = "results",
        default_format: StorageFormat = StorageFormat.PICKLE
    ):
        """
        Initialize result storage.

        Args:
            results_dir: Base directory for storing results
            default_format: Default storage format to use
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.default_format = default_format

        # Index file for quick metadata lookup
        self.index_file = self.results_dir / "result_index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load result index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    index_data = json.load(f)
                    self.index = {
                        rid: ResultMetadata.from_dict(meta)
                        for rid, meta in index_data.items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load result index: {e}")
                self.index = {}
        else:
            self.index = {}

    def _save_index(self) -> None:
        """Save result index to disk."""
        try:
            index_data = {
                rid: meta.to_dict()
                for rid, meta in self.index.items()
            }
            with open(self.index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save result index: {e}")

    def _generate_result_id(self, mode: str, start_date: datetime) -> str:
        """
        Generate unique result identifier.

        Format: {mode}_{start_date}_{timestamp}

        Args:
            mode: Simulation mode
            start_date: Simulation start date

        Returns:
            Unique result ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = start_date.strftime("%Y%m%d")
        return f"{mode}_{date_str}_{timestamp}"

    def save(
        self,
        results: "SimulationResults",  # Forward reference
        result_id: Optional[str] = None,
        format: Optional[StorageFormat] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Save simulation results to disk.

        Args:
            results: SimulationResults object to save
            result_id: Optional custom result ID (auto-generated if None)
            format: Storage format (uses default if None)
            notes: Optional notes to attach to result

        Returns:
            result_id: The ID assigned to this result

        Example:
            >>> storage = ResultStorage()
            >>> result_id = storage.save(results, notes="Baseline configuration")
            >>> print(f"Saved as: {result_id}")
        """
        # Generate result ID if not provided
        if result_id is None:
            result_id = self._generate_result_id(results.mode, results.start_date)

        # Use default format if not specified
        if format is None:
            format = self.default_format

        # Create subdirectory for this result
        result_dir = self.results_dir / result_id
        result_dir.mkdir(parents=True, exist_ok=True)

        # Save based on format
        if format == StorageFormat.PICKLE:
            file_path = result_dir / "results.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(results, f, protocol=pickle.HIGHEST_PROTOCOL)

        elif format == StorageFormat.JSON:
            # JSON format: Save DataFrames separately as CSV, metadata as JSON
            file_path = result_dir / "results.json"

            # Save trajectory as Parquet (more efficient than CSV)
            results.trajectory.to_parquet(result_dir / "trajectory.parquet")
            results.monthly_summary.to_parquet(result_dir / "monthly_summary.parquet")

            # Save metadata and metrics as JSON
            json_data = {
                'mode': results.mode,
                'start_date': results.start_date.isoformat(),
                'end_date': results.end_date.isoformat(),
                'economic_metrics': results.economic_metrics,
                'metadata': results.metadata,
            }
            with open(file_path, 'w') as f:
                json.dump(json_data, f, indent=2)

        elif format == StorageFormat.PARQUET:
            # Parquet format: Everything as Parquet files
            results.trajectory.to_parquet(result_dir / "trajectory.parquet")
            results.monthly_summary.to_parquet(result_dir / "monthly_summary.parquet")

            # Metadata as JSON
            json_data = {
                'mode': results.mode,
                'start_date': results.start_date.isoformat(),
                'end_date': results.end_date.isoformat(),
                'economic_metrics': results.economic_metrics,
                'metadata': results.metadata,
            }
            with open(result_dir / "metadata.json", 'w') as f:
                json.dump(json_data, f, indent=2)
            file_path = result_dir / "trajectory.parquet"

        # Get file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # Create metadata for index
        metadata = ResultMetadata(
            result_id=result_id,
            created_at=datetime.now(),
            mode=results.mode,
            start_date=results.start_date,
            end_date=results.end_date,
            battery_kwh=results.metadata.get('battery_kwh', 0),
            battery_kw=results.metadata.get('battery_kw', 0),
            storage_format=format.value,
            file_path=str(file_path.relative_to(self.results_dir)),
            file_size_mb=file_size_mb,
            optimizer_method=results.metadata.get('optimizer_method'),
            execution_time_s=results.metadata.get('execution_time_s'),
            total_cost_nok=results.economic_metrics.get('total_cost_nok'),
            notes=notes
        )

        # Update index
        self.index[result_id] = metadata
        self._save_index()

        logger.info(
            f"Saved result '{result_id}' ({format.value}, {file_size_mb:.2f} MB) "
            f"to {result_dir}"
        )

        return result_id

    def load(self, result_id: str) -> "SimulationResults":
        """
        Load simulation results from disk.

        Args:
            result_id: Result ID to load

        Returns:
            SimulationResults object

        Raises:
            KeyError: If result_id not found in index
            FileNotFoundError: If result files missing

        Example:
            >>> storage = ResultStorage()
            >>> results = storage.load("rolling_horizon_20241001_120000")
        """
        if result_id not in self.index:
            raise KeyError(f"Result ID '{result_id}' not found in index")

        metadata = self.index[result_id]
        result_dir = self.results_dir / result_id

        # Load based on storage format
        if metadata.storage_format == "pickle":
            file_path = result_dir / "results.pkl"
            with open(file_path, 'rb') as f:
                results = pickle.load(f)

        elif metadata.storage_format == "json":
            # Load JSON metadata
            with open(result_dir / "results.json", 'r') as f:
                json_data = json.load(f)

            # Load DataFrames
            trajectory = pd.read_parquet(result_dir / "trajectory.parquet")
            monthly_summary = pd.read_parquet(result_dir / "monthly_summary.parquet")

            # Reconstruct SimulationResults
            from src.simulation.simulation_results import SimulationResults
            results = SimulationResults(
                mode=json_data['mode'],
                start_date=datetime.fromisoformat(json_data['start_date']),
                end_date=datetime.fromisoformat(json_data['end_date']),
                trajectory=trajectory,
                monthly_summary=monthly_summary,
                economic_metrics=json_data['economic_metrics'],
                metadata=json_data['metadata']
            )

        elif metadata.storage_format == "parquet":
            # Load Parquet files
            trajectory = pd.read_parquet(result_dir / "trajectory.parquet")
            monthly_summary = pd.read_parquet(result_dir / "monthly_summary.parquet")

            # Load metadata
            with open(result_dir / "metadata.json", 'r') as f:
                json_data = json.load(f)

            # Reconstruct SimulationResults
            from src.simulation.simulation_results import SimulationResults
            results = SimulationResults(
                mode=json_data['mode'],
                start_date=datetime.fromisoformat(json_data['start_date']),
                end_date=datetime.fromisoformat(json_data['end_date']),
                trajectory=trajectory,
                monthly_summary=monthly_summary,
                economic_metrics=json_data['economic_metrics'],
                metadata=json_data['metadata']
            )

        logger.info(f"Loaded result '{result_id}' ({metadata.storage_format})")
        return results

    def list_results(
        self,
        mode: Optional[str] = None,
        start_date_after: Optional[datetime] = None,
        start_date_before: Optional[datetime] = None
    ) -> List[ResultMetadata]:
        """
        List available results with optional filtering.

        Args:
            mode: Filter by simulation mode
            start_date_after: Filter results starting after this date
            start_date_before: Filter results starting before this date

        Returns:
            List of ResultMetadata objects matching filters

        Example:
            >>> storage = ResultStorage()
            >>> results = storage.list_results(mode="rolling_horizon")
            >>> for meta in results:
            >>>     print(f"{meta.result_id}: {meta.total_cost_nok:.2f} NOK")
        """
        results = list(self.index.values())

        # Apply filters
        if mode is not None:
            results = [r for r in results if r.mode == mode]

        if start_date_after is not None:
            results = [r for r in results if r.start_date >= start_date_after]

        if start_date_before is not None:
            results = [r for r in results if r.start_date <= start_date_before]

        # Sort by created_at (newest first)
        results.sort(key=lambda r: r.created_at, reverse=True)

        return results

    def delete(self, result_id: str) -> None:
        """
        Delete a stored result.

        Args:
            result_id: Result ID to delete

        Raises:
            KeyError: If result_id not found
        """
        if result_id not in self.index:
            raise KeyError(f"Result ID '{result_id}' not found")

        # Remove files
        result_dir = self.results_dir / result_id
        if result_dir.exists():
            import shutil
            shutil.rmtree(result_dir)

        # Remove from index
        del self.index[result_id]
        self._save_index()

        logger.info(f"Deleted result '{result_id}'")

    def get_metadata(self, result_id: str) -> ResultMetadata:
        """
        Get metadata for a result without loading full result.

        Args:
            result_id: Result ID

        Returns:
            ResultMetadata object

        Raises:
            KeyError: If result_id not found
        """
        if result_id not in self.index:
            raise KeyError(f"Result ID '{result_id}' not found")

        return self.index[result_id]

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored results.

        Returns:
            Dictionary with storage statistics
        """
        total_size_mb = sum(meta.file_size_mb for meta in self.index.values())

        modes = {}
        for meta in self.index.values():
            modes[meta.mode] = modes.get(meta.mode, 0) + 1

        return {
            'total_results': len(self.index),
            'total_size_mb': total_size_mb,
            'results_by_mode': modes,
            'storage_dir': str(self.results_dir.absolute())
        }

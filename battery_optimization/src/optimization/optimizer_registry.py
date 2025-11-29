"""
Optimizer Registry for method traceability and documentation.

Provides comprehensive metadata about available optimization methods,
their parameters, requirements, and use cases. Enables transparent
documentation of which optimizer was used for each simulation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Literal, Any
from enum import Enum

from src.optimization.base_optimizer import BaseOptimizer


class SolverType(Enum):
    """Supported solver types for optimization."""
    LP = "lp"           # Linear Programming
    MILP = "milp"       # Mixed-Integer Linear Programming
    MPC = "mpc"         # Model Predictive Control
    HEURISTIC = "heuristic"


class TimeScale(Enum):
    """Time scale for optimization horizon."""
    HOURLY = "hourly"       # Hour-by-hour
    DAILY = "daily"         # Day-by-day
    WEEKLY = "weekly"       # Week-by-week
    MONTHLY = "monthly"     # Month-by-month


@dataclass
class OptimizerMetadata:
    """
    Metadata describing an optimization method.

    Provides comprehensive information about capabilities, requirements,
    and use cases for method selection and traceability.
    """
    # Identification
    name: str                           # Unique identifier (e.g., 'rolling_horizon')
    display_name: str                   # Human-readable name
    description: str                    # Detailed description
    version: str = "1.0"                # Implementation version

    # Classification
    solver_type: SolverType = SolverType.LP
    time_scale: TimeScale = TimeScale.HOURLY
    optimization_scope: Literal["local", "global"] = "global"

    # Capabilities
    supports_degradation: bool = False  # Battery degradation tracking
    supports_power_tariff: bool = False # Power tariff optimization
    supports_forecasting: bool = False  # Forecast-based operation
    supports_rolling_execution: bool = False  # Iterative execution

    # Requirements
    requires_solver: Optional[str] = None  # External solver requirement (HiGHS, CBC, etc.)
    min_horizon_hours: int = 1         # Minimum planning horizon
    max_horizon_hours: int = 8760      # Maximum planning horizon
    typical_horizon_hours: int = 168   # Recommended horizon

    # Performance characteristics
    typical_solve_time_s: float = 1.0  # Expected solve time
    memory_usage_mb: float = 100.0     # Typical memory usage
    scales_linearly: bool = True       # Computational complexity

    # Use cases
    best_for: List[str] = field(default_factory=list)  # Recommended scenarios
    limitations: List[str] = field(default_factory=list)  # Known limitations
    references: List[str] = field(default_factory=list)  # Academic/technical references

    # Implementation
    optimizer_class: Optional[Type[BaseOptimizer]] = None  # Class implementing this method
    adapter_class: Optional[Type] = None  # Adapter class if applicable
    config_section: Optional[str] = None  # Configuration section name


class OptimizerRegistry:
    """
    Registry of available battery optimization methods.

    Provides discovery, metadata access, and traceability for all
    optimization algorithms available in the system.
    """

    # Class-level storage for registered optimizers
    _optimizers: Dict[str, OptimizerMetadata] = {}

    @classmethod
    def register(cls, metadata: OptimizerMetadata) -> None:
        """
        Register an optimization method.

        Args:
            metadata: OptimizerMetadata describing the method

        Raises:
            ValueError: If optimizer name already registered
        """
        if metadata.name in cls._optimizers:
            raise ValueError(f"Optimizer '{metadata.name}' already registered")

        cls._optimizers[metadata.name] = metadata

    @classmethod
    def get(cls, name: str) -> OptimizerMetadata:
        """
        Get metadata for specific optimizer.

        Args:
            name: Optimizer name

        Returns:
            OptimizerMetadata for the optimizer

        Raises:
            KeyError: If optimizer not registered
        """
        if name not in cls._optimizers:
            available = ", ".join(cls._optimizers.keys())
            raise KeyError(
                f"Optimizer '{name}' not registered. "
                f"Available: {available}"
            )

        return cls._optimizers[name]

    @classmethod
    def list_all(cls) -> List[OptimizerMetadata]:
        """
        Get list of all registered optimizers.

        Returns:
            List of OptimizerMetadata objects
        """
        return list(cls._optimizers.values())

    @classmethod
    def list_names(cls) -> List[str]:
        """
        Get list of all registered optimizer names.

        Returns:
            List of optimizer names
        """
        return list(cls._optimizers.keys())

    @classmethod
    def filter_by(
        cls,
        solver_type: Optional[SolverType] = None,
        supports_degradation: Optional[bool] = None,
        supports_power_tariff: Optional[bool] = None,
        supports_forecasting: Optional[bool] = None,
        max_solve_time_s: Optional[float] = None
    ) -> List[OptimizerMetadata]:
        """
        Filter optimizers by capabilities.

        Args:
            solver_type: Required solver type
            supports_degradation: Must support degradation tracking
            supports_power_tariff: Must support power tariff optimization
            supports_forecasting: Must support forecasting
            max_solve_time_s: Maximum acceptable solve time

        Returns:
            List of matching OptimizerMetadata objects
        """
        results = cls.list_all()

        if solver_type is not None:
            results = [o for o in results if o.solver_type == solver_type]

        if supports_degradation is not None:
            results = [o for o in results if o.supports_degradation == supports_degradation]

        if supports_power_tariff is not None:
            results = [o for o in results if o.supports_power_tariff == supports_power_tariff]

        if supports_forecasting is not None:
            results = [o for o in results if o.supports_forecasting == supports_forecasting]

        if max_solve_time_s is not None:
            results = [o for o in results if o.typical_solve_time_s <= max_solve_time_s]

        return results

    @classmethod
    def print_summary(cls) -> None:
        """Print summary of all registered optimizers to console."""
        print("\n" + "=" * 100)
        print("REGISTERED BATTERY OPTIMIZATION METHODS")
        print("=" * 100)

        if not cls._optimizers:
            print("No optimizers registered.")
            return

        for name, meta in sorted(cls._optimizers.items()):
            print(f"\n{meta.display_name} ({name})")
            print(f"  Version:      {meta.version}")
            print(f"  Type:         {meta.solver_type.value.upper()}")
            print(f"  Scale:        {meta.time_scale.value}")
            print(f"  Scope:        {meta.optimization_scope}")
            print(f"  Horizon:      {meta.typical_horizon_hours} hours (typical)")

            # Capabilities
            capabilities = []
            if meta.supports_degradation:
                capabilities.append("degradation")
            if meta.supports_power_tariff:
                capabilities.append("power tariff")
            if meta.supports_forecasting:
                capabilities.append("forecasting")
            if meta.supports_rolling_execution:
                capabilities.append("rolling execution")

            if capabilities:
                print(f"  Capabilities: {', '.join(capabilities)}")

            # Performance
            print(f"  Solve Time:   ~{meta.typical_solve_time_s:.1f}s (typical)")
            print(f"  Memory:       ~{meta.memory_usage_mb:.0f} MB")

            # Use cases
            if meta.best_for:
                print(f"  Best For:")
                for use_case in meta.best_for:
                    print(f"    - {use_case}")

            if meta.limitations:
                print(f"  Limitations:")
                for limitation in meta.limitations:
                    print(f"    - {limitation}")

            print("-" * 100)


# Register built-in optimizers
def _register_builtin_optimizers():
    """Register all built-in optimization methods."""

    # Rolling Horizon Optimizer
    OptimizerRegistry.register(OptimizerMetadata(
        name="rolling_horizon",
        display_name="Rolling Horizon MPC Optimizer",
        description=(
            "Model Predictive Control with receding horizon. Optimizes over a "
            "fixed time window, executes first step, then rolls forward. "
            "Provides good balance between computational efficiency and solution quality."
        ),
        version="2.0",
        solver_type=SolverType.MPC,
        time_scale=TimeScale.HOURLY,
        optimization_scope="local",
        supports_degradation=True,
        supports_power_tariff=True,
        supports_forecasting=True,
        supports_rolling_execution=True,
        requires_solver="HiGHS",
        min_horizon_hours=24,
        max_horizon_hours=336,  # 2 weeks
        typical_horizon_hours=168,  # 1 week
        typical_solve_time_s=0.5,
        memory_usage_mb=150,
        scales_linearly=True,
        best_for=[
            "Real-time operation with forecast updates",
            "Long simulation periods (months, years)",
            "Systems with weather forecast integration",
            "Computational resource constraints"
        ],
        limitations=[
            "Myopic optimization (local optimality)",
            "Solution quality depends on horizon length",
            "May miss global optimization opportunities"
        ],
        references=[
            "Mayne et al. (2000): Constrained model predictive control",
            "Rawlings & Mayne (2009): Model Predictive Control"
        ],
        adapter_class=None,  # Will be set when adapter is imported
        config_section="rolling_horizon"
    ))

    # Monthly LP Optimizer
    OptimizerRegistry.register(OptimizerMetadata(
        name="monthly",
        display_name="Monthly Linear Programming Optimizer",
        description=(
            "Monthly horizon LP optimization. Optimizes each month independently "
            "with perfect foresight within the month. Good for analysis and "
            "understanding monthly dynamics."
        ),
        version="1.0",
        solver_type=SolverType.LP,
        time_scale=TimeScale.MONTHLY,
        optimization_scope="global",
        supports_degradation=False,
        supports_power_tariff=True,
        supports_forecasting=False,
        supports_rolling_execution=False,
        requires_solver="HiGHS",
        min_horizon_hours=24*28,  # Shortest month
        max_horizon_hours=24*31,  # Longest month
        typical_horizon_hours=24*30,
        typical_solve_time_s=2.0,
        memory_usage_mb=200,
        scales_linearly=True,
        best_for=[
            "Monthly analysis and reporting",
            "Understanding seasonal patterns",
            "Baseline performance estimation",
            "Economic analysis by month"
        ],
        limitations=[
            "No continuity between months",
            "Cannot capture multi-month strategies",
            "Perfect foresight within month (unrealistic)",
            "No degradation tracking"
        ],
        config_section="monthly"
    ))

    # Weekly/Yearly Optimizer
    OptimizerRegistry.register(OptimizerMetadata(
        name="yearly",
        display_name="Weekly Rolling Horizon Optimizer",
        description=(
            "Weekly horizon rolling optimization for full-year simulations. "
            "Optimizes over 1-week windows, executes first day, rolls forward. "
            "Designed for efficient yearly analysis."
        ),
        version="1.0",
        solver_type=SolverType.MPC,
        time_scale=TimeScale.WEEKLY,
        optimization_scope="local",
        supports_degradation=False,
        supports_power_tariff=True,
        supports_forecasting=True,
        supports_rolling_execution=True,
        requires_solver="HiGHS",
        min_horizon_hours=24*7,
        max_horizon_hours=24*14,
        typical_horizon_hours=24*7,
        typical_solve_time_s=1.5,
        memory_usage_mb=180,
        scales_linearly=True,
        best_for=[
            "Full-year simulations",
            "Annual economic analysis",
            "Seasonal pattern analysis",
            "Computational efficiency for yearly data"
        ],
        limitations=[
            "Shorter horizon than rolling_horizon",
            "May miss longer-term patterns",
            "No degradation tracking currently"
        ],
        config_section="yearly"
    ))


# Auto-register builtin optimizers on module import
_register_builtin_optimizers()

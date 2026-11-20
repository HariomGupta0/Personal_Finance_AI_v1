"""
Config-driven thresholds and weights for the deterministic financial reasoning engine.
Provides centralized defaults that guarantee 100% mathematical backward-compatibility
while enabling configurable experimentation and sensitivity analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DTIBands:
    """Debt-to-Income (DTI) ratio risk classification boundaries (percentages)."""
    healthy_max: float = 20.0
    moderate_max: float = 35.0
    high_max: float = 50.0


@dataclass(frozen=True)
class RunwayBands:
    """Emergency runway duration classifications (months)."""
    critical_max: float = 1.0
    insufficient_max: float = 3.0
    healthy_max: float = 6.0
    target_months: float = 3.0


@dataclass(frozen=True)
class HealthScoreWeights:
    """Component score ceilings and calibration points for the 0-100 financial health model."""
    savings_max_score: float = 35.0
    savings_target_rate: float = 20.0
    runway_max_score: float = 35.0
    runway_target_months: float = 3.0
    debt_max_score: float = 30.0
    debt_min_dti: float = 20.0
    debt_max_dti: float = 50.0


@dataclass(frozen=True)
class GradeCutoffs:
    """Score boundaries for letter grades A through D."""
    grade_a_min: float = 85.0
    grade_b_min: float = 70.0
    grade_c_min: float = 50.0


@dataclass(frozen=True)
class EngineConfig:
    """
    Master configuration for financial engine reasoning.
    All defaults exactly match existing production formulas.
    """
    emergency_reserve_multiplier: int = 3
    dti_bands: DTIBands = field(default_factory=DTIBands)
    runway_bands: RunwayBands = field(default_factory=RunwayBands)
    health_weights: HealthScoreWeights = field(default_factory=HealthScoreWeights)
    grade_cutoffs: GradeCutoffs = field(default_factory=GradeCutoffs)
    trailing_n_months: Optional[int] = None  # None = off by default; uses single target month
    fixed_obligations_default: float = 0.0   # 0.0 = off by default


DEFAULT_ENGINE_CONFIG = EngineConfig()

"""Production functions: hours -> outputs with diminishing returns and noise.

Noise enters as a standard-normal draw ``z`` supplied by the caller (from rng.py), so
these functions stay pure. Lags arise from accumulating fractional progress into whole
units (``accumulate``) and from journal decision lags in env/journals.py.
"""

from __future__ import annotations

import math

from lecsim.config import ProductionParams


def lognormal_noise(z: float, sigma: float) -> float:
    """Mean-one multiplicative noise: exp(sigma*z - sigma^2/2)."""
    return math.exp(sigma * z - sigma * sigma / 2)


def produce(hours: float, params: ProductionParams, z: float, multiplier: float = 1.0) -> float:
    """Output from ``hours`` (per semester): scale * multiplier * hours^alpha * noise."""
    if hours < 0:
        raise ValueError("hours must be non-negative")
    if hours == 0:
        return 0.0
    return params.scale * multiplier * hours**params.alpha * lognormal_noise(z, params.sigma)


def accumulate(progress: float, produced: float) -> tuple[int, float]:
    """Add ``produced`` to fractional ``progress``; return (whole units completed, remainder)."""
    total = progress + produced
    whole = math.floor(total)
    return whole, total - whole

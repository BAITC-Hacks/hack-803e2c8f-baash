"""Reproducible offline exploration of approved canonical datasets."""

from .manifest import DatasetManifest, build_manifest, read_canonical
from .quality import Dimension, RegionQuality, assess, weakest_dimensions
from .temporal import TemporalProfile, moving_average, profile

__all__ = [
    "DatasetManifest",
    "Dimension",
    "RegionQuality",
    "TemporalProfile",
    "assess",
    "build_manifest",
    "moving_average",
    "profile",
    "read_canonical",
    "weakest_dimensions",
]

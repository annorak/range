"""Range — declarative, ephemeral, AI-native cyber-range platform."""

import importlib.metadata

# Single source of truth is the installed distribution metadata (pyproject version).
__version__ = importlib.metadata.version("range-lab")

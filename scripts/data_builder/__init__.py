"""Data builder package for terminal agent training.

This package provides utilities for building training data from YAML history files
and system prompts for both SFT (Supervised Fine-Tuning) and DPO (Direct Preference Optimization).
"""

from .sft_data_builder import sft_data_from_edits
from .utils import create_mistral_message

__all__ = ["sft_data_from_edits", "create_mistral_message"]

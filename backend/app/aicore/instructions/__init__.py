#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instructions module - Dynamic instruction generation
"""

from .instruction_builder import InstructionBuilder, InstructionContext
from .prompt_utils import ModelVersion

__all__ = [
    'InstructionBuilder',
    'InstructionContext',
    'ModelVersion'
] 
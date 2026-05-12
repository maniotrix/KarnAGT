#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core module - Main AI assistant and client classes
"""

from .configurable_openai_assistant import ConfigurableOpenAIAssistant
from .configurable_assistant_client import ConfigurableAssistantClient, ConfigurableAssistantManager, configurable_assistant_manager

__all__ = [
    'ConfigurableOpenAIAssistant',
    'ConfigurableAssistantClient',
    'ConfigurableAssistantManager',
    'configurable_assistant_manager'
] 
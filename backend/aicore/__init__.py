#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI Core System

Provides configurable AI assistants using the OpenAI Agents SDK with centralized configuration management
"""

# Legacy imports (backward compatibility)
from aicore.openai_assistant import OpenAIAssistant

# New configurable system imports
from aicore.config import AIConfig, ConfigManager, config_manager
from aicore.core import (
    ConfigurableOpenAIAssistant, 
    ConfigurableAssistantClient, 
    ConfigurableAssistantManager,
    configurable_assistant_manager
)
from aicore.ai_agents import ConfigurableCodeExecutorAgent
from aicore.instructions import InstructionBuilder, InstructionContext

__all__ = [
    # Legacy
    'OpenAIAssistant',
    
    # Configuration system
    'AIConfig',
    'ConfigManager', 
    'config_manager',
    
    # Configurable core classes
    'ConfigurableOpenAIAssistant',
    'ConfigurableAssistantClient',
    'ConfigurableAssistantManager',
    'configurable_assistant_manager',
    
    # Configurable agents
    'ConfigurableCodeExecutorAgent',
    
    # Instruction system
    'InstructionBuilder',
    'InstructionContext'
]

__version__ = "2.0.0" 
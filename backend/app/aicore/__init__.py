#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI Core System

Provides configurable AI assistants using the OpenAI Agents SDK with centralized configuration management
"""

# New configurable system imports
from app.aicore.config import AIConfig, ConfigManager, config_manager
from app.aicore.core import (
    ConfigurableOpenAIAssistant, 
    ConfigurableAssistantClient, 
    ConfigurableAssistantManager,
    configurable_assistant_manager
)
from app.aicore.ai_agents import ConfigurableCodeExecutorAgent
from app.aicore.instructions import InstructionBuilder, InstructionContext

__all__ = [
    
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
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent Configuration - Centralized agent behavior settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class ToolUseStrategy(Enum):
    """Strategy for handling tool use in agents"""
    RUN_LLM_AGAIN = "run_llm_again"
    STOP_ON_FIRST_TOOL = "stop_on_first_tool"
    CUSTOM_HANDLER = "custom_handler"


@dataclass
class WebSearchConfig:
    """Configuration for web search tool"""
    enabled: bool = True
    location: Dict[str, str] = field(default_factory=lambda: {
        "type": "approximate", 
        "city": "New Delhi"
    })
    max_results: int = 5


@dataclass
class CodeExecutionConfig:
    """Configuration for code execution capabilities"""
    enabled: bool = True
    timeout_seconds: int = 300
    allowed_packages: List[str] = field(default_factory=lambda: [
        "matplotlib", "numpy", "pandas", "seaborn", "scipy", "sklearn",
        "nltk", "requests", "beautifulsoup4", "pillow"
    ])
    plots_enabled: bool = True
    system_commands_enabled: bool = True
    allowed_command_prefixes: List[str] = field(default_factory=lambda: [
        "python", "pip", "python -m"
    ])


@dataclass
class GuardrailConfig:
    """Configuration for input/output guardrails"""
    input_guardrails: List[str] = field(default_factory=list)
    output_guardrails: List[str] = field(default_factory=list)
    max_input_length: int = 50000
    max_output_length: int = 100000
    content_filtering: bool = True


@dataclass
class AgentConfig:
    """Comprehensive agent configuration"""
    
    # Basic agent properties
    name: str = "AI Assistant"
    description: str = "An intelligent AI assistant capable of various tasks"
    
    # Core prompt configuration
    core_prompt: str = ""  # Will be loaded from instruction builder
    instruction_template: str = "default"  # Template name to use
    dynamic_instructions: bool = True  # Whether to use function-based instructions
    
    # Model configuration reference
    model_name: str = "gpt-4o-mini-2024-07-18"
    
    # Tool configurations
    web_search: WebSearchConfig = field(default_factory=WebSearchConfig)
    code_execution: CodeExecutionConfig = field(default_factory=CodeExecutionConfig)
    custom_tools: List[str] = field(default_factory=list)  # Names of custom tools to load
    
    # Agent behavior
    tool_use_strategy: ToolUseStrategy = ToolUseStrategy.RUN_LLM_AGAIN
    custom_tool_handler: Optional[Callable] = None
    reset_tool_choice: bool = True
    
    # Memory and context
    maintain_conversation_history: bool = True
    max_context_messages: int = 50
    context_window_strategy: str = "sliding"  # sliding, truncate, summarize
    
    # Guardrails and safety
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)
    
    # Handoffs and delegation
    handoffs_enabled: bool = False
    available_handoffs: List[str] = field(default_factory=list)
    
    # Output configuration
    output_type: str = "str"  # Can be extended for structured outputs
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    created_by: str = "system"
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.tool_use_strategy == ToolUseStrategy.CUSTOM_HANDLER and not self.custom_tool_handler:
            raise ValueError("Custom tool handler must be provided when using CUSTOM_HANDLER strategy")
    
    def get_enabled_tools(self) -> List[str]:
        """Get list of enabled tool names"""
        tools = []
        if self.code_execution.enabled:
            tools.extend(["execute_code", "execute_system_command"])
        if self.web_search.enabled:
            tools.append("web_search")
        tools.extend(self.custom_tools)
        return tools
    
    def clone(self, **kwargs) -> 'AgentConfig':
        """Create a copy with modified attributes"""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config 
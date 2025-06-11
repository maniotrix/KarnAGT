#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Runner Configuration - Centralized runner execution settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class StreamingMode(Enum):
    """Streaming configuration modes"""
    DISABLED = "disabled"
    TEXT_ONLY = "text_only"
    FULL_EVENTS = "full_events"
    CUSTOM = "custom"


class CancellationStrategy(Enum):
    """Stream cancellation strategies"""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    COMPLETE_TURN = "complete_turn"


@dataclass
class TracingConfig:
    """Configuration for tracing and monitoring"""
    enabled: bool = True
    include_sensitive_data: bool = False
    workflow_name: str = "AI Agent Workflow"
    trace_id: Optional[str] = None
    group_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailExecutionConfig:
    """Configuration for guardrail execution"""
    input_guardrails_enabled: bool = True
    output_guardrails_enabled: bool = True
    fail_fast: bool = True  # Stop on first guardrail failure
    parallel_execution: bool = True
    timeout_seconds: int = 30


@dataclass
class StreamingConfig:
    """Configuration for streaming behavior"""
    mode: StreamingMode = StreamingMode.TEXT_ONLY
    buffer_size: int = 1024
    flush_interval_ms: int = 50
    cancellation_strategy: CancellationStrategy = CancellationStrategy.GRACEFUL
    callback_timeout_ms: int = 5000
    error_recovery: bool = True
    
    # Event filtering for FULL_EVENTS mode
    include_raw_responses: bool = True
    include_tool_calls: bool = True
    include_agent_updates: bool = True
    include_guardrail_results: bool = False


@dataclass
class ExecutionConfig:
    """Configuration for execution behavior"""
    max_turns: int = 10
    turn_timeout_seconds: int = 300
    total_timeout_seconds: int = 1800
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    
    # Context management
    preserve_context_on_error: bool = True
    cleanup_on_completion: bool = True
    memory_limit_mb: int = 512


@dataclass
class ModelProviderConfig:
    """Configuration for model provider settings"""
    provider_name: str = "openai"
    api_key_env_var: str = "OPENAI_API_KEY"
    base_url: Optional[str] = None
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class HookConfig:
    """Configuration for execution hooks"""
    enabled: bool = True
    on_agent_start: Optional[Callable] = None
    on_agent_end: Optional[Callable] = None
    on_turn_start: Optional[Callable] = None
    on_turn_end: Optional[Callable] = None
    on_tool_call: Optional[Callable] = None
    on_error: Optional[Callable] = None
    custom_hooks: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class RunnerConfig:
    """Comprehensive runner configuration covering all execution parameters"""
    
    # Basic execution settings
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # Streaming configuration
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    
    # Model provider settings
    model_provider: ModelProviderConfig = field(default_factory=ModelProviderConfig)
    
    # Tracing and monitoring
    tracing: TracingConfig = field(default_factory=TracingConfig)
    
    # Guardrail execution
    guardrails: GuardrailExecutionConfig = field(default_factory=GuardrailExecutionConfig)
    
    # Hooks and callbacks
    hooks: HookConfig = field(default_factory=HookConfig)
    
    # Context and state management
    context_preservation: bool = True
    state_persistence: bool = False
    state_storage_path: Optional[str] = None
    
    # Performance settings
    concurrent_tool_execution: bool = True
    max_concurrent_tools: int = 5
    memory_optimization: bool = True
    
    # Debug and development
    debug_mode: bool = False
    verbose_logging: bool = False
    log_level: str = "INFO"
    
    # Response handling
    response_timeout_seconds: int = 300
    partial_response_handling: bool = True
    response_validation: bool = True
    
    # Error handling
    error_recovery_enabled: bool = True
    fallback_strategies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.execution.max_turns <= 0:
            raise ValueError("max_turns must be positive")
        
        if self.execution.total_timeout_seconds < self.execution.turn_timeout_seconds:
            raise ValueError("total_timeout must be >= turn_timeout")
        
        if self.streaming.mode == StreamingMode.CUSTOM and not self.hooks.custom_hooks:
            raise ValueError("Custom streaming mode requires custom hooks")
    
    def get_sdk_run_config(self) -> Dict[str, Any]:
        """Convert to SDK RunConfig parameters"""
        return {
            "tracing_disabled": not self.tracing.enabled,
            "trace_include_sensitive_data": self.tracing.include_sensitive_data,
            "workflow_name": self.tracing.workflow_name,
            "trace_id": self.tracing.trace_id,
            "group_id": self.tracing.group_id,
            "trace_metadata": self.tracing.metadata,
        }
    
    def is_streaming_enabled(self) -> bool:
        """Check if streaming is enabled"""
        return self.streaming.mode != StreamingMode.DISABLED
    
    def clone(self, **kwargs) -> 'RunnerConfig':
        """Create a copy with modified attributes"""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config 
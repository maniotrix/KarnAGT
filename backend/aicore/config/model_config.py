#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Model Configuration - Centralized model and provider settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class ModelProvider(Enum):
    """Supported model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelFamily(Enum):
    """Model family classifications"""
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5"
    CLAUDE = "claude"
    LLAMA = "llama"
    CUSTOM = "custom"


@dataclass
class ModelParameters:
    """Core model generation parameters"""
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    stop_sequences: List[str] = field(default_factory=list)
    
    # Advanced parameters
    repetition_penalty: Optional[float] = None
    length_penalty: Optional[float] = None
    diversity_penalty: Optional[float] = None
    
    def __post_init__(self):
        """Validate parameters"""
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError("Top_p must be between 0.0 and 1.0")
        if self.top_k is not None and self.top_k <= 0:
            raise ValueError("Top_k must be positive")


@dataclass
class ProviderSettings:
    """Provider-specific settings"""
    provider: ModelProvider = ModelProvider.OPENAI
    api_key_env_var: str = "OPENAI_API_KEY"
    base_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    
    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: Optional[str] = None
    
    # Custom provider settings
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_auth: Optional[Dict[str, Any]] = None
    
    # Connection settings
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    connection_pool_size: int = 10


@dataclass
class ModelCapabilities:
    """Model capability flags"""
    supports_functions: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = True
    supports_system_messages: bool = True
    
    # Context and token limits
    max_context_tokens: int = 4096
    max_output_tokens: int = 4096
    supports_long_context: bool = False
    
    # Advanced features
    supports_tool_choice: bool = True
    supports_parallel_tools: bool = True
    supports_structured_output: bool = False


@dataclass
class CostSettings:
    """Cost tracking and limits"""
    track_costs: bool = True
    input_token_cost: float = 0.0  # Cost per 1K input tokens
    output_token_cost: float = 0.0  # Cost per 1K output tokens
    
    # Cost limits
    max_cost_per_request: Optional[float] = None
    max_cost_per_session: Optional[float] = None
    max_cost_per_user_daily: Optional[float] = None
    
    # Budget alerts
    cost_alert_threshold: Optional[float] = None
    budget_alert_callback: Optional[str] = None


@dataclass
class ModelConfig:
    """Comprehensive model configuration"""
    
    # Basic model identification
    name: str = "gpt-4o-mini-2024-07-18"
    display_name: str = "GPT-4 Mini"
    family: ModelFamily = ModelFamily.GPT4
    version: str = "2024-07-18"
    
    # Provider configuration
    provider: ProviderSettings = field(default_factory=ProviderSettings)
    
    # Model parameters
    parameters: ModelParameters = field(default_factory=ModelParameters)
    
    # Model capabilities
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    
    # Cost configuration
    costs: CostSettings = field(default_factory=CostSettings)
    
    # Model-specific settings
    model_specific_params: Dict[str, Any] = field(default_factory=dict)
    
    # Fallback configuration
    fallback_models: List[str] = field(default_factory=list)
    auto_fallback: bool = True
    
    # Performance settings
    batch_size: int = 1
    concurrent_requests: int = 1
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    
    # Quality and safety
    content_filter_level: str = "medium"  # low, medium, high
    safety_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Caching and optimization
    enable_caching: bool = True
    cache_ttl_minutes: int = 60
    compression_enabled: bool = False
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_by: str = "system"
    last_updated: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.name:
            raise ValueError("Model name cannot be empty")
        
        if self.costs.max_cost_per_request and self.costs.max_cost_per_session:
            if self.costs.max_cost_per_request > self.costs.max_cost_per_session:
                raise ValueError("max_cost_per_request cannot exceed max_cost_per_session")
    
    def get_full_model_name(self) -> str:
        """Get the complete model identifier"""
        if self.provider.provider == ModelProvider.AZURE_OPENAI:
            return f"{self.provider.azure_deployment or self.name}"
        return self.name
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get provider-specific configuration"""
        config = {
            "provider": self.provider.provider.value,
            "timeout_seconds": self.provider.timeout_seconds,
            "max_retries": self.provider.max_retries,
            "retry_delay_seconds": self.provider.retry_delay_seconds,
        }
        
        if self.provider.base_url:
            config["base_url"] = self.provider.base_url
        
        if self.provider.provider == ModelProvider.AZURE_OPENAI:
            config["azure_endpoint"] = self.provider.azure_endpoint
            config["azure_deployment"] = self.provider.azure_deployment
            config["api_version"] = self.provider.api_version
        
        return config
    
    def get_model_parameters_dict(self) -> Dict[str, Any]:
        """Get model parameters as dictionary for SDK"""
        params = {
            "temperature": self.parameters.temperature,
            "top_p": self.parameters.top_p,
            "frequency_penalty": self.parameters.frequency_penalty,
            "presence_penalty": self.parameters.presence_penalty,
        }
        
        if self.parameters.max_tokens:
            params["max_tokens"] = self.parameters.max_tokens
        
        if self.parameters.stop_sequences:
            params["stop"] = self.parameters.stop_sequences
        
        # Add model-specific parameters
        for key, value in self.model_specific_params.items():
            params[key] = value
        
        return params
    
    def clone(self, **kwargs) -> 'ModelConfig':
        """Create a copy with modified attributes"""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config
    
    def is_compatible_with(self, required_capabilities: List[str]) -> bool:
        """Check if model supports required capabilities"""
        capability_map = {
            "functions": self.capabilities.supports_functions,
            "vision": self.capabilities.supports_vision,
            "audio": self.capabilities.supports_audio,
            "streaming": self.capabilities.supports_streaming,
            "json_mode": self.capabilities.supports_json_mode,
            "system_messages": self.capabilities.supports_system_messages,
            "tool_choice": self.capabilities.supports_tool_choice,
            "parallel_tools": self.capabilities.supports_parallel_tools,
            "structured_output": self.capabilities.supports_structured_output,
        }
        
        return all(capability_map.get(cap, False) for cap in required_capabilities) 
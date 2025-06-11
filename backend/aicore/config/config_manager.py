#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Manager - Centralized configuration loading and management
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union, Type, TypeVar, List
from dataclasses import dataclass, field
from pathlib import Path

from .agent_config import AgentConfig
from .runner_config import RunnerConfig
from .model_config import ModelConfig
from .tool_config import ToolConfig

T = TypeVar('T')


@dataclass
class AIConfig:
    """Master configuration combining all sub-configurations"""
    agent: AgentConfig = field(default_factory=AgentConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    
    # Environment and deployment settings
    environment: str = "development"
    debug_mode: bool = False
    log_level: str = "INFO"
    
    # Metadata
    config_version: str = "1.0"
    loaded_from: str = "defaults"
    last_modified: Optional[str] = None


class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager
        
        Args:
            config_dir: Directory to search for configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"
        self._config_cache: Dict[str, AIConfig] = {}
        self._environment_configs: Dict[str, Dict[str, Any]] = {}
        
    def load_config(
        self, 
        config_name: str = "default",
        environment: Optional[str] = None,
        user_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> AIConfig:
        """
        Load configuration with precedence:
        1. Defaults
        2. Environment config file
        3. User-specific config
        4. Runtime overrides
        
        Args:
            config_name: Name of the configuration to load
            environment: Environment name (dev, prod, test)
            user_id: User ID for user-specific configs
            overrides: Runtime configuration overrides
            
        Returns:
            Complete AIConfig instance
        """
        cache_key = f"{config_name}_{environment}_{user_id}"
        
        if cache_key in self._config_cache and not overrides:
            return self._config_cache[cache_key]
        
        # Start with defaults
        config = self._load_default_config()
        
        # Apply environment-specific settings
        if environment:
            env_config = self._load_environment_config(environment)
            config = self._merge_configs(config, env_config)
        
        # Apply config-specific settings
        if config_name != "default":
            named_config = self._load_named_config(config_name)
            config = self._merge_configs(config, named_config)
        
        # Apply user-specific settings
        if user_id:
            user_config = self._load_user_config(user_id)
            config = self._merge_configs(config, user_config)
        
        # Apply runtime overrides
        if overrides:
            config = self._apply_overrides(config, overrides)
        
        # Cache the result
        if not overrides:  # Don't cache configs with runtime overrides
            self._config_cache[cache_key] = config
        
        return config
    
    def _load_default_config(self) -> AIConfig:
        """Load default configuration"""
        return AIConfig()
    
    def _load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration"""
        if environment in self._environment_configs:
            return self._environment_configs[environment]
        
        config_data = {}
        
        # Try to load from various file formats
        for ext in ['.yaml', '.yml', '.json']:
            config_file = self.config_dir / f"{environment}{ext}"
            if config_file.exists():
                config_data = self._load_config_file(config_file)
                break
        
        # Load from environment variables
        env_config = self._load_from_environment_variables(environment)
        config_data.update(env_config)
        
        self._environment_configs[environment] = config_data
        return config_data
    
    def _load_named_config(self, config_name: str) -> Dict[str, Any]:
        """Load named configuration"""
        for ext in ['.yaml', '.yml', '.json']:
            config_file = self.config_dir / f"{config_name}{ext}"
            if config_file.exists():
                return self._load_config_file(config_file)
        
        return {}
    
    def _load_user_config(self, user_id: str) -> Dict[str, Any]:
        """Load user-specific configuration"""
        user_config_dir = self.config_dir / "users"
        if not user_config_dir.exists():
            return {}
        
        for ext in ['.yaml', '.yml', '.json']:
            config_file = user_config_dir / f"{user_id}{ext}"
            if config_file.exists():
                return self._load_config_file(config_file)
        
        return {}
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.json':
                    return json.load(f)
                else:  # YAML
                    return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
            return {}
    
    def _load_from_environment_variables(self, environment: str) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Define environment variable mapping
        env_mapping = {
            # Model configuration
            'OPENAI_API_KEY': 'model.provider.api_key_env_var',
            'OPENAI_MODEL': 'model.name',
            'OPENAI_TEMPERATURE': 'model.parameters.temperature',
            'OPENAI_MAX_TOKENS': 'model.parameters.max_tokens',
            
            # Agent configuration
            'AGENT_NAME': 'agent.name',
            'AGENT_MAX_TURNS': 'runner.execution.max_turns',
            'AGENT_TIMEOUT': 'runner.execution.turn_timeout_seconds',
            
            # Feature flags
            'ENABLE_WEB_SEARCH': 'agent.web_search.enabled',
            'ENABLE_CODE_EXECUTION': 'agent.code_execution.enabled',
            'ENABLE_STREAMING': 'runner.streaming.mode',
            
            # Debug and logging
            'DEBUG_MODE': 'debug_mode',
            'LOG_LEVEL': 'log_level',
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config, config_path, self._convert_env_value(value))
        
        return config
    
    def _set_nested_config(self, config: Dict[str, Any], path: str, value: Any):
        """Set nested configuration value using dot notation"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _merge_configs(self, base_config: AIConfig, updates: Dict[str, Any]) -> AIConfig:
        """Merge configuration updates into base configuration"""
        import copy
        merged = copy.deepcopy(base_config)
        
        # Update agent config
        if 'agent' in updates:
            merged.agent = self._update_dataclass(merged.agent, updates['agent'])
        
        # Update runner config
        if 'runner' in updates:
            merged.runner = self._update_dataclass(merged.runner, updates['runner'])
        
        # Update model config
        if 'model' in updates:
            merged.model = self._update_dataclass(merged.model, updates['model'])
        
        # Update tools config
        if 'tools' in updates:
            merged.tools = self._update_dataclass(merged.tools, updates['tools'])
        
        # Update top-level attributes
        for key, value in updates.items():
            if key not in ['agent', 'runner', 'model', 'tools'] and hasattr(merged, key):
                setattr(merged, key, value)
        
        return merged
    
    def _update_dataclass(self, obj: T, updates: Dict[str, Any]) -> T:
        """Update dataclass instance with new values"""
        import copy
        updated = copy.deepcopy(obj)
        
        for key, value in updates.items():
            if hasattr(updated, key):
                current_value = getattr(updated, key)
                if hasattr(current_value, '__dataclass_fields__'):
                    # Nested dataclass
                    setattr(updated, key, self._update_dataclass(current_value, value))
                else:
                    setattr(updated, key, value)
        
        return updated
    
    def _apply_overrides(self, config: AIConfig, overrides: Dict[str, Any]) -> AIConfig:
        """Apply runtime configuration overrides"""
        return self._merge_configs(config, overrides)
    
    def save_config(self, config: AIConfig, config_name: str, config_format: str = 'yaml'):
        """Save configuration to file"""
        config_file = self.config_dir / f"{config_name}.{config_format}"
        
        # Convert to dictionary
        config_dict = self._config_to_dict(config)
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            if config_format == 'json':
                json.dump(config_dict, f, indent=2, default=str)
            else:  # YAML
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    def _config_to_dict(self, config: AIConfig) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        import dataclasses
        
        def convert_dataclass(obj) -> Any:
            if dataclasses.is_dataclass(obj):
                return {k: convert_dataclass(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, dict):
                return {k: convert_dataclass(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dataclass(item) for item in obj]
            else:
                return obj
        
        result = convert_dataclass(config)
        return result if isinstance(result, dict) else {}
    
    def validate_config(self, config: AIConfig) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate model config
        try:
            config.model.__post_init__()
        except Exception as e:
            errors.append(f"Model config error: {e}")
        
        # Validate agent config
        try:
            config.agent.__post_init__()
        except Exception as e:
            errors.append(f"Agent config error: {e}")
        
        # Validate runner config
        try:
            config.runner.__post_init__()
        except Exception as e:
            errors.append(f"Runner config error: {e}")
        
        # Check model compatibility
        required_capabilities = []
        if config.agent.code_execution.enabled:
            required_capabilities.append("functions")
        if config.runner.streaming.mode.value != "disabled":
            required_capabilities.append("streaming")
        
        if not config.model.is_compatible_with(required_capabilities):
            errors.append(f"Model {config.model.name} doesn't support required capabilities: {required_capabilities}")
        
        return errors
    
    def get_config_summary(self, config: AIConfig) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "agent_name": config.agent.name,
            "model_name": config.model.name,
            "provider": config.model.provider.provider.value,
            "streaming_enabled": config.runner.is_streaming_enabled(),
            "max_turns": config.runner.execution.max_turns,
            "tools_enabled": config.agent.get_enabled_tools(),
            "environment": config.environment,
            "debug_mode": config.debug_mode,
            "config_version": config.config_version,
        }
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()
        self._environment_configs.clear()


# Global configuration manager instance
config_manager = ConfigManager() 
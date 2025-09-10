from enum import Enum
from typing import Optional


class ModelVersion(Enum):
    """Enum for different model versions"""
    GPT_4 = "gpt_4"
    GPT_5 = "gpt_5"


def get_default_core_prompt(model_version: ModelVersion = ModelVersion.GPT_5) -> str:
    """Get the core prompt for the specified model version"""
    if model_version == ModelVersion.GPT_4:
        from app.aicore.instructions.prompts.gpt_4.v1.prompts import INITIAL_CORE_PROMPT
    else:  # default to GPT_5
        from app.aicore.instructions.prompts.gpt_5.v1.prompts import INITIAL_CORE_PROMPT
    return INITIAL_CORE_PROMPT


def get_default_all_tools_enabled_system_prompt(model_version: ModelVersion = ModelVersion.GPT_5) -> str:
    """Get the system prompt for the specified model version"""
    if model_version == ModelVersion.GPT_4:
        from app.aicore.instructions.prompts.gpt_4.v1.prompts import ALL_TOOLS_ENABLED_SYSTEM_PROMPT
    else:  # default to GPT_5
        from app.aicore.instructions.prompts.gpt_5.v1.prompts import ALL_TOOLS_ENABLED_SYSTEM_PROMPT
    return ALL_TOOLS_ENABLED_SYSTEM_PROMPT


def validate_prompt_imports(model_version: Optional[ModelVersion] = None) -> bool:
    """
    Validate that prompt imports work correctly for specified model version
    
    Args:
        model_version: Optional model version to test. If None, tests all versions.
        
    Returns:
        bool: True if all imports are valid, False otherwise
    """
    versions_to_test = [model_version] if model_version else list(ModelVersion)
    
    try:
        for version in versions_to_test:
            core = get_default_core_prompt(version)
            system = get_default_all_tools_enabled_system_prompt(version)
            
            if len(core) == 0 or len(system) == 0:
                return False
                
        return True
    except ImportError as e:
        print(f"Import error during validation: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during validation: {e}")
        return False
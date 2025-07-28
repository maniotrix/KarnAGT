#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Universal Serialization Module for FastAPI

This module provides industry-standard serialization capabilities for any Python object,
using a combination of ORJSON (high performance), Pydantic custom serializers, and
intelligent fallback mechanisms.

Features:
- High-performance JSON serialization with ORJSON
- Pydantic Annotated types for type safety
- Automatic handling of numpy, pandas, datetime, and custom objects
- Graceful fallbacks for unknown types
- Easy FastAPI integration
- Extensible design for custom types

Usage:
    from serialization import SerializableResponse, make_serializable
    
    # In FastAPI endpoint
    @app.post("/", response_class=SerializableResponse)
    async def endpoint():
        return {"data": numpy_array, "df": pandas_df}
    
    # Or manually serialize
    result = make_serializable(complex_object)
"""

import json
import logging
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import UUID

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    orjson = None
    HAS_ORJSON = False
    logging.warning("orjson not available, falling back to standard json")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

from fastapi import Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)


OUTPUT_TRUNCATION_LIMIT = 10000

class SerializationRegistry:
    """Registry for custom serialization handlers"""
    
    def __init__(self):
        self._handlers = {}
        self._register_default_handlers()
    
    def register(self, type_or_types, handler):
        """Register a custom serialization handler for a type or types"""
        if isinstance(type_or_types, (list, tuple)):
            for t in type_or_types:
                self._handlers[t] = handler
        else:
            self._handlers[type_or_types] = handler
    
    def get_handler(self, obj_type):
        """Get the handler for a specific type"""
        # Direct type match
        if obj_type in self._handlers:
            return self._handlers[obj_type]
        
        # Check inheritance hierarchy
        for registered_type, handler in self._handlers.items():
            if isinstance(registered_type, type) and issubclass(obj_type, registered_type):
                return handler
        
        return None
    
    def _register_default_handlers(self):
        """Register default handlers for common types"""
        
        # Date/time types
        self.register(datetime, lambda x: x.isoformat())
        self.register(date, lambda x: x.isoformat())
        self.register(time, lambda x: x.isoformat())
        self.register(timedelta, lambda x: str(x))
        
        # Numeric types
        self.register(Decimal, lambda x: float(x))
        self.register(complex, lambda x: {"real": x.real, "imag": x.imag})
        
        # Other built-ins
        self.register(UUID, lambda x: str(x))
        self.register(Path, lambda x: str(x))
        self.register(bytes, lambda x: x.decode('utf-8', errors='replace'))
        self.register(set, lambda x: list(x))
        self.register(frozenset, lambda x: list(x))
        self.register(Enum, lambda x: x.value)
        
        # Enhanced Numpy types handling (if available)
        if HAS_NUMPY:
            # Integer types - explicit handling for all variants
            integer_types = [
                np.integer, np.int8, np.int16, np.int32, np.int64,
                np.uint8, np.uint16, np.uint32, np.uint64,
                np.longlong, np.ulonglong  # Additional long types
            ]
            for int_type in integer_types:
                self.register(int_type, lambda x: int(x))
            
            # Floating point types
            float_types = [
                np.floating, np.float16, np.float32, np.float64,
                np.longdouble  # Extended precision
            ]
            for float_type in float_types:
                self.register(float_type, lambda x: float(x))
            
            # Boolean types
            self.register(np.bool_, lambda x: bool(x))
            
            # Array types
            self.register(np.ndarray, lambda x: x.tolist())
            self.register(np.matrix, lambda x: x.tolist())
            
            # Scalar types that might slip through
            self.register(np.number, lambda x: x.item() if hasattr(x, 'item') else float(x))
            
        # Enhanced Pandas types handling (if available)
        if HAS_PANDAS:
            self.register(pd.DataFrame, lambda x: x.to_dict('records'))
            self.register(pd.Series, lambda x: x.to_list())
            self.register(pd.Index, lambda x: x.to_list())
            self.register(pd.Timestamp, lambda x: x.isoformat())
            
            # Handle pandas nullable integer types
            if hasattr(pd, 'Int64Dtype'):
                self.register(pd.Int64Dtype, lambda x: int(x) if pd.notna(x) else None)
            if hasattr(pd, 'Float64Dtype'):
                self.register(pd.Float64Dtype, lambda x: float(x) if pd.notna(x) else None)


# Global registry instance
registry = SerializationRegistry()


def make_serializable(obj: Any) -> Any:
    """
    Convert any Python object to a JSON-serializable format.
    
    Enhanced to handle:
    - Built-in types (already serializable)
    - Registered types (via handlers)
    - Numpy types with explicit int64/float64 handling
    - Custom objects (via __dict__ or string representation)
    - Recursive structures (lists, dicts, tuples)
    - Edge cases and error recovery
    
    Args:
        obj: Any Python object
        
    Returns:
        JSON-serializable representation of the object
    """
    
    # Handle None
    if obj is None:
        return None
    
    # Handle basic JSON-serializable types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Enhanced numpy type handling before general checks
    if HAS_NUMPY and hasattr(obj, 'dtype'):
        try:
            # Handle numpy scalars explicitly
            if obj.ndim == 0:  # Scalar
                if 'int' in str(obj.dtype):
                    return int(obj.item())
                elif 'float' in str(obj.dtype):
                    return float(obj.item())
                elif 'bool' in str(obj.dtype):
                    return bool(obj.item())
                else:
                    return obj.item()  # Generic scalar extraction
            else:
                # Handle arrays
                return obj.tolist()
        except Exception as e:
            logger.warning(f"Numpy conversion failed for {type(obj)}: {e}")
            # Fall through to other handlers
    
    # Handle pandas types early to catch int64 issues
    if HAS_PANDAS:
        try:
            import pandas as pd
            if isinstance(obj, (pd.Int64Dtype, pd.Float64Dtype, pd.Timestamp)):
                try:
                    # Try item() method for extracting scalar values
                    return obj.item()  # type: ignore
                except (AttributeError, ValueError):
                    try:
                        if pd.isna(obj):  # type: ignore
                            return None
                    except (AttributeError, TypeError):
                        pass
                    return str(obj)  # Fallback to string
        except Exception as e:
            logger.warning(f"Pandas conversion failed for {type(obj)}: {e}")
    
    # Handle collections recursively
    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    
    if isinstance(obj, dict):
        serializable_dict = {}
        for k, v in obj.items():
            try:
                # Ensure keys are strings
                key = str(k) if not isinstance(k, str) else k
                serializable_dict[key] = make_serializable(v)
            except Exception as e:
                logger.warning(f"Failed to serialize dict item {k}: {e}")
                # Skip problematic items rather than failing entirely
                continue
        return serializable_dict
    
    # Check for registered handler
    obj_type = type(obj)
    handler = registry.get_handler(obj_type)
    if handler:
        try:
            return handler(obj)
        except Exception as e:
            logger.warning(f"Handler failed for {obj_type}: {e}")
    
    # Try Pydantic model serialization
    if isinstance(obj, BaseModel):
        try:
            return obj.model_dump()
        except Exception:
            try:
                return obj.dict()  # Fallback for older Pydantic versions
            except Exception as e:
                logger.warning(f"Pydantic serialization failed: {e}")
    
    # Try object with __dict__
    if hasattr(obj, '__dict__'):
        try:
            return {k: make_serializable(v) for k, v in obj.__dict__.items() 
                   if not k.startswith('_')}
        except Exception as e:
            logger.warning(f"__dict__ serialization failed: {e}")
    
    # Enhanced fallback handling - use try-catch for dynamic attributes
    try:
        # Try to extract value if it's a wrapper type
        try:
            return obj.item()  # type: ignore
        except (AttributeError, ValueError, TypeError):
            pass
        
        try:
            return make_serializable(obj.value)  # type: ignore
        except (AttributeError, ValueError, TypeError):
            pass
            
        try:
            return obj.tolist()  # type: ignore
        except (AttributeError, ValueError, TypeError):
            pass
            
        try:
            return obj.__json__()  # type: ignore
        except (AttributeError, ValueError, TypeError):
            pass
        
        # Last resort: string representation
        if hasattr(obj, '__str__'):
            str_repr = str(obj)
            # Avoid very long string representations
            if len(str_repr) > 1000:
                str_repr = str_repr[:997] + "..."
            return f"<{type(obj).__name__}: {str_repr}>"
        else:
            return f"<{type(obj).__name__} object>"
            
    except Exception as e:
        logger.error(f"All serialization attempts failed for {type(obj)}: {e}")
        return f"<unserializable {type(obj).__name__}>"


class SerializableResponse(Response):
    """
    High-performance JSON response class that can serialize any Python object.
    
    Uses ORJSON when available for maximum performance, falls back to standard json.
    Automatically handles complex objects through the make_serializable function.
    """
    
    media_type = "application/json"
    
    def render(self, content: Any) -> bytes:
        """Render content to JSON bytes"""
        
        # Make content serializable
        serializable_content = make_serializable(content)
        
        if HAS_ORJSON:
            # Use ORJSON for maximum performance
            try:
                return orjson.dumps(
                    serializable_content,
                    option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_UUID
                )
            except Exception as e:
                logger.error(f"ORJSON serialization failed: {e}")
                # Fall back to standard json
        
        # Standard json fallback
        try:
            return json.dumps(serializable_content, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            logger.error(f"Standard JSON serialization failed: {e}")
            # Last resort: error message
            error_response = {
                "error": "Serialization failed",
                "message": str(e),
                "type": str(type(content).__name__)
            }
            return json.dumps(error_response).encode('utf-8')


class SerializableJSONResponse(JSONResponse):
    """
    Standard JSONResponse that uses our serialization logic.
    Use this when you need standard JSONResponse features but with universal serialization.
    """
    
    def render(self, content: Any) -> bytes:
        serializable_content = make_serializable(content)
        
        if HAS_ORJSON:
            try:
                return orjson.dumps(
                    serializable_content,
                    option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_UUID
                )
            except Exception:
                pass
        
        return json.dumps(serializable_content, ensure_ascii=False).encode('utf-8')


def get_fastapi_json_encoders() -> Dict[Any, Callable]:
    """
    Get JSON encoders dict for FastAPI app initialization.
    
    Usage:
        app = FastAPI(json_encoders=get_fastapi_json_encoders())
    """
    encoders: Dict[Any, Callable] = {
        datetime: lambda v: v.isoformat(),
        date: lambda v: v.isoformat(),
        time: lambda v: v.isoformat(),
        timedelta: lambda v: str(v),
        Decimal: lambda v: float(v),
        UUID: lambda v: str(v),
        Path: lambda v: str(v),
        bytes: lambda v: v.decode('utf-8', errors='replace'),
        set: lambda v: list(v),
        frozenset: lambda v: list(v),
    }
    
    if HAS_NUMPY and np is not None:
        encoders[np.integer] = lambda v: int(v)
        encoders[np.floating] = lambda v: float(v)
        encoders[np.bool_] = lambda v: bool(v)
        encoders[np.ndarray] = lambda v: v.tolist()
    
    if HAS_PANDAS and pd is not None:
        encoders[pd.DataFrame] = lambda v: v.to_dict('records')
        encoders[pd.Series] = lambda v: v.to_list()
        encoders[pd.Timestamp] = lambda v: v.isoformat()
    
    return encoders


# Convenience functions for manual serialization
def to_json_string(obj: Any, **kwargs) -> str:
    """Convert any object to JSON string"""
    serializable_obj = make_serializable(obj)
    
    if HAS_ORJSON:
        try:
            return orjson.dumps(serializable_obj, **kwargs).decode('utf-8')
        except Exception:
            pass
    
    return json.dumps(serializable_obj, ensure_ascii=False, **kwargs)


def to_json_bytes(obj: Any, **kwargs) -> bytes:
    """Convert any object to JSON bytes"""
    serializable_obj = make_serializable(obj)
    
    if HAS_ORJSON:
        try:
            return orjson.dumps(serializable_obj, **kwargs)
        except Exception:
            pass
    
    return json.dumps(serializable_obj, ensure_ascii=False, **kwargs).encode('utf-8')


# Example custom type registration
def register_custom_type(custom_type: type, serializer: Callable):
    """
    Register a custom serialization handler.
    
    Example:
        register_custom_type(MyCustomClass, lambda x: {"id": x.id, "name": x.name})
    """
    registry.register(custom_type, serializer)


def get_serializable_response(content: Any) -> SerializableResponse:
    """
    Convenience function to create a SerializableResponse.
    
    Args:
        content: Any content to serialize
        
    Returns:
        SerializableResponse ready for FastAPI return
    """
    return SerializableResponse(content=content)


def safe_serialize_execution_result(result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely serialize execution result data with enhanced error handling.
    
    This function specifically handles common issues in execution results:
    - Numpy int64/float64 serialization errors
    - Complex nested data structures
    - Large output handling
    
    Args:
        result_data: Execution result dictionary
        
    Returns:
        JSON-serializable execution result
    """
    try:
        # Pre-process known problematic fields
        safe_result = {}
        
        for key, value in result_data.items():
            try:
                if key in ('result_data', 'outputs', 'generated_files'):
                    # These fields often contain complex objects
                    safe_result[key] = make_serializable(value)
                elif key in ('stdout', 'stderr'):
                    # Handle potentially large text output - keep limit small for LLM context
                    if isinstance(value, str) and len(value) > OUTPUT_TRUNCATION_LIMIT:  # Reduced from 50000 to 5000
                        safe_result[key] = value[:OUTPUT_TRUNCATION_LIMIT] + "\n... (output truncated)"
                        safe_result[f"{key}_truncated"] = True
                    else:
                        safe_result[key] = str(value) if value is not None else ""
                else:
                    # Standard fields
                    safe_result[key] = make_serializable(value)
            except Exception as e:
                logger.warning(f"Failed to serialize field '{key}': {e}")
                safe_result[key] = f"<serialization_error: {str(e)[:100]}>"
        
        return safe_result
        
    except Exception as e:
        logger.error(f"Complete serialization failure: {e}")
        return {
            "error": "Serialization failed",
            "message": str(e),
            "original_keys": list(result_data.keys()) if isinstance(result_data, dict) else "not_dict"
        }


if __name__ == "__main__":
    # Demo usage
    import sys
    
    # Create some test data
    test_data = {
        "datetime": datetime.now(),
        "uuid": UUID("12345678-1234-5678-1234-567812345678"),
        "path": Path("/some/path"),
        "decimal": Decimal("123.45"),
        "set": {1, 2, 3},
        "complex": complex(1, 2)
    }
    
    if HAS_NUMPY:
        test_data["numpy_array"] = np.array([1, 2, 3, 4, 5])
        test_data["numpy_int"] = np.int64(42)
        test_data["numpy_float"] = np.float32(3.14)
    
    if HAS_PANDAS:
        test_data["dataframe"] = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data["series"] = pd.Series([1, 2, 3, 4, 5])
    
    print("Original data:")
    for k, v in test_data.items():
        print(f"  {k}: {type(v)} = {v}")
    
    print("\nSerialized:")
    serialized = make_serializable(test_data)
    print(to_json_string(serialized, indent=2))
    
    print(f"\nUsing ORJSON: {HAS_ORJSON}")
    print(f"Using Numpy: {HAS_NUMPY}")
    print(f"Using Pandas: {HAS_PANDAS}") 
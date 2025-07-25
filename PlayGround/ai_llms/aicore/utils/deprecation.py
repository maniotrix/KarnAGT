#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Deprecation utilities for aicore
"""

import warnings
import functools
from typing import Optional, Callable, Any


def deprecated(
    reason: Optional[str] = None,
    version: Optional[str] = None,
    remove_in: Optional[str] = None,
    alternative: Optional[str] = None
) -> Callable:
    """
    Decorator to mark functions/classes as deprecated
    
    Args:
        reason: Reason for deprecation
        version: Version when deprecated
        remove_in: Version when it will be removed
        alternative: Suggested alternative to use
        
    Returns:
        Decorator function
    
    Example:
        @deprecated(
            reason="Use new_function instead",
            version="2.0.0",
            remove_in="3.0.0",
            alternative="new_function"
        )
        def old_function():
            pass
    """
    def decorator(func_or_class: Callable) -> Callable:
        # Build deprecation message
        name = getattr(func_or_class, '__name__', str(func_or_class))
        msg_parts = [f"{name} is deprecated"]
        
        if version:
            msg_parts.append(f"since version {version}")
        
        if remove_in:
            msg_parts.append(f"and will be removed in version {remove_in}")
        
        if reason:
            msg_parts.append(f"({reason})")
        
        if alternative:
            msg_parts.append(f"Use {alternative} instead.")
        
        warning_msg = " ".join(msg_parts) + "."
        
        # Check if it's a class
        if isinstance(func_or_class, type):
            # It's a class
            original_init = func_or_class.__init__
            
            def new_init(self, *args, **kwargs):
                warnings.warn(
                    warning_msg,
                    category=DeprecationWarning,
                    stacklevel=2
                )
                original_init(self, *args, **kwargs)
            
            func_or_class.__init__ = new_init
            return func_or_class
        else:
            # It's a function or method
            @functools.wraps(func_or_class)
            def wrapper(*args, **kwargs):
                warnings.warn(
                    warning_msg,
                    category=DeprecationWarning,
                    stacklevel=2
                )
                return func_or_class(*args, **kwargs)
            
            return wrapper
    
    return decorator


def warn_deprecated(
    message: str,
    category: type = DeprecationWarning,
    stacklevel: int = 2
) -> None:
    """
    Emit a deprecation warning
    
    Args:
        message: Warning message
        category: Warning category (default: DeprecationWarning)
        stacklevel: Stack level for the warning
    """
    warnings.warn(message, category=category, stacklevel=stacklevel) 
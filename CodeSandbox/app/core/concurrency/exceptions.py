#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Concurrency Exception Classes

Common exception classes used across concurrency modules.
Placed here to avoid circular dependencies.
"""


class ValidationError(Exception):
    """
    Base class for validation errors that should not trigger circuit breaker.
    
    Used for user input validation errors (invalid filenames, malformed requests, etc.)
    that should return HTTP 4xx responses but not count as system failures.
    """
    pass


class ExecutionValidationError(ValidationError):
    """
    Validation errors for code execution requests.
    
    Used for user input validation like:
    - Code too long
    - Invalid timeout values
    - Malformed execution requests
    """
    pass


class WorkspaceValidationError(ValidationError):
    """
    Validation errors for workspace management.
    
    Used for workspace-related validation like:
    - TTL limits exceeded
    - Workspace not ready
    - Invalid workspace parameters
    """
    pass


class WorkspaceNotFoundError(ValidationError):
    """
    Workspace not found error - this is a client error, not a system failure.
    
    Should return HTTP 404 but not trigger circuit breaker.
    """
    pass 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sandbox Client Exceptions

Custom exceptions for code execution client operations.
"""


class SandboxClientError(Exception):
    """Base exception for sandbox client errors"""
    pass


class WorkspaceError(SandboxClientError):
    """Workspace-related errors"""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Workspace not found error"""
    pass


class ExecutionError(SandboxClientError):
    """Code execution errors"""
    pass


class ExecutionTimeoutError(ExecutionError):
    """Code execution timeout error"""
    pass


class FileOperationError(SandboxClientError):
    """File operation errors"""
    pass


class NetworkError(SandboxClientError):
    """Network/HTTP communication errors"""
    pass


class AuthenticationError(SandboxClientError):
    """Authentication/authorization errors"""
    pass 
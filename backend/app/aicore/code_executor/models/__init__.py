#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code Executor Models - Exact Server Response Models

Centralized models that match the CodeSandbox server responses exactly.
These models should NEVER be modified without checking the server code first!

Import all models from here to ensure consistency across the codebase.
"""

# Workspace models - exact server response models
from .workspace_models import (
    WorkspaceStatus,
    WorkspaceInfo,
    WorkspaceCreateRequest,
    HealthCheck,
    # Client wrapper models
    WorkspaceGetResult,
    WorkspaceCreateResult,
    WorkspaceDeleteResult,
    WorkspaceTTLExtendResult,
    # Health service models
    HealthCheckResult,
    SystemStatsResult,
    SystemConfigResult
)

# File models - exact server response models  
from .file_models import (
    FileInfo,
    WorkspaceFilesResponse,
    # Client wrapper models
    FileUploadResult,
    FileDownloadResult,
    FileListResult
)

# Execution models - exact server response models
from .execution_models import (
    ExecutionStatus,
    ExecutionOutput,
    ExecutionRequest,
    ExecutionResult,
    # Client wrapper models
    ExecutionOperationResult,
    ExecutionGetResult,
    ExecutionSummary,
    ExecutionHistoryResult
)

__all__ = [
    # === EXACT SERVER MODELS (DO NOT MODIFY) ===
    
    # Workspace models
    "WorkspaceStatus",
    "WorkspaceInfo", 
    "WorkspaceCreateRequest",
    "HealthCheck",
    
    # File models
    "FileInfo",
    "WorkspaceFilesResponse",
    
    # Execution models
    "ExecutionStatus",
    "ExecutionOutput", 
    "ExecutionRequest",
    "ExecutionResult",
    
    # === CLIENT WRAPPER MODELS ===
    
    # Workspace wrapper models
    "WorkspaceGetResult",
    "WorkspaceCreateResult",
    "WorkspaceDeleteResult",
    "WorkspaceTTLExtendResult",
    
    # Health service models
    "HealthCheckResult",
    "SystemStatsResult", 
    "SystemConfigResult",
    
    # File wrapper models
    "FileUploadResult",
    "FileDownloadResult", 
    "FileListResult",
    
    # Execution wrapper models
    "ExecutionOperationResult",
    "ExecutionGetResult", 
    "ExecutionSummary",
    "ExecutionHistoryResult"
] 
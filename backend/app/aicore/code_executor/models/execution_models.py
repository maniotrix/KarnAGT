#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Models - Exact Server Response Models

These models match the CodeSandbox server responses exactly.
DO NOT modify these without checking the server code first!
"""

from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

from .file_models import FileInfo


class ExecutionStatus(str, Enum):
    """Code execution states - matches server"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionOutput(BaseModel):
    """Output from code execution - matches server"""
    type: str = Field(..., description="Output type: stdout, stderr, display_data, etc.")
    content: Union[str, Dict[str, Any]] = Field(..., description="Output content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionRequest(BaseModel):
    """Request for code execution - matches server"""
    workspace_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, description="Python code to execute")
    timeout: int = Field(30, ge=1, le=300, description="Execution timeout in seconds")


class ExecutionResult(BaseModel):
    """Result of code execution - HTTP response format"""
    execution_id: str
    workspace_id: str
    status: str  # Server returns enum as string in HTTP response
    started_at: str  # Server returns datetime as ISO string in HTTP response
    completed_at: Optional[str] = None  # Server returns datetime as ISO string in HTTP response
    
    # Output streams
    stdout: str = ""
    stderr: str = ""
    
    # Structured outputs (server formats these for HTTP)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Result data
    result_data: Optional[Any] = None
    
    # Generated files (server formats these for HTTP)
    generated_files: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Execution metadata
    execution_time_ms: Optional[int] = None


# Result wrapper models for client operations
class ExecutionOperationResult(BaseModel):
    """Result of code execution operation"""
    success: bool
    execution_result: Optional[ExecutionResult] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, execution_result: ExecutionResult) -> "ExecutionOperationResult":
        """Create a successful result"""
        return cls(success=True, execution_result=execution_result)
    
    @classmethod
    def error_result(cls, error: str) -> "ExecutionOperationResult":
        """Create an error result"""
        return cls(success=False, error=error)


class ExecutionGetResult(BaseModel):
    """Result of get execution operation"""
    success: bool
    execution_result: Optional[ExecutionResult] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, execution_result: ExecutionResult) -> "ExecutionGetResult":
        """Create a successful result"""
        return cls(success=True, execution_result=execution_result)
    
    @classmethod
    def error_result(cls, error: str) -> "ExecutionGetResult":
        """Create an error result"""
        return cls(success=False, error=error)


# Client wrapper models
class ExecutionSummary(BaseModel):
    """Summary of a single execution for history listing"""
    execution_id: str
    workspace_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    has_result_data: bool = False
    generated_files_count: int = 0
    has_stdout: bool = False
    has_stderr: bool = False

    @classmethod
    def from_execution_result(cls, result: ExecutionResult) -> "ExecutionSummary":
        """Create summary from ExecutionResult"""
        return cls(
            execution_id=result.execution_id,
            workspace_id=result.workspace_id,
            status=result.status,  # Already a string from HTTP response
            started_at=result.started_at,  # Already a string from HTTP response
            completed_at=result.completed_at,  # Already a string from HTTP response
            execution_time_ms=result.execution_time_ms,
            has_result_data=result.result_data is not None,
            generated_files_count=len(result.generated_files),
            has_stdout=bool(result.stdout.strip()),
            has_stderr=bool(result.stderr.strip())
        )


class ExecutionHistoryResult(BaseModel):
    """Result of execution history listing"""
    success: bool
    workspace_id: str
    executions: List[ExecutionSummary] = Field(default_factory=list)
    total_executions: int = 0
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, workspace_id: str, executions: List[ExecutionSummary]) -> "ExecutionHistoryResult":
        """Create a successful result"""
        return cls(
            success=True,
            workspace_id=workspace_id,
            executions=executions,
            total_executions=len(executions)
        )
    
    @classmethod
    def error_result(cls, workspace_id: str, error: str) -> "ExecutionHistoryResult":
        """Create an error result"""
        return cls(
            success=False,
            workspace_id=workspace_id,
            error=error
        ) 
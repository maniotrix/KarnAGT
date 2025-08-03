"""
Stream Events for Unified Streaming Architecture

This module defines typed events for the single-queue streaming system,
supporting both text tokens and tool call events with proper type safety.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union
from abc import ABC
from pydantic import BaseModel, Field


class EventType(Enum):
    """Event types for streaming events"""
    TEXT_TOKEN = "text_token"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_OUTPUT = "tool_call_output"
    TOOL_CALL_ERROR = "tool_call_error"
    COMPLETION = "completion"


class ToolType(Enum):
    """Supported tool types"""
    FUNCTION_CALL = "function_call"
    CODE_INTERPRETER = "code_interpreter"
    WEB_SEARCH = "web_search"
    FILE_SEARCH = "file_search"
    IMAGE_GENERATION = "image_generation"
    COMPUTER_TOOL = "computer_tool"
    MCP_CALL = "mcp_call"
    UNKNOWN = "unknown"


class ToolStatus(Enum):
    """Tool execution status"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    EXECUTING = "executing" 
    SEARCHING = "searching"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamEvent(BaseModel, ABC):
    """Base class for all streaming events"""
    event_type: EventType = Field(description="Event type")


class TextTokenEvent(StreamEvent):
    """Event for text token streaming"""
    token: str
    event_type: EventType = Field(default=EventType.TEXT_TOKEN, description="Event type")


class ToolCallStartEvent(StreamEvent):
    """Event when a tool call begins"""
    tool_name: str
    tool_type: ToolType
    tool_id: str
    arguments: Dict[str, Any]
    event_type: EventType = Field(default=EventType.TOOL_CALL_START, description="Event type")


class ToolCallProgressEvent(StreamEvent):
    """Event for tool call progress updates"""
    tool_id: str
    tool_name: str
    status: ToolStatus
    progress_data: Optional[Dict[str, Any]] = None
    event_type: EventType = Field(default=EventType.TOOL_CALL_PROGRESS, description="Event type")


class ToolCallOutputEvent(StreamEvent):
    """Event when a tool call produces output/completes"""
    tool_id: str
    tool_name: str
    tool_type: ToolType
    result: Any
    status: ToolStatus
    event_type: EventType = Field(default=EventType.TOOL_CALL_OUTPUT, description="Event type")


class ToolCallErrorEvent(StreamEvent):
    """Event when a tool call encounters an error"""
    tool_id: str
    tool_name: str
    tool_type: ToolType
    error: str
    error_details: Optional[Dict[str, Any]] = None
    event_type: EventType = Field(default=EventType.TOOL_CALL_ERROR, description="Event type")


class CompletionEvent(StreamEvent):
    """Event when the entire response is completed"""
    response_data: Dict[str, Any]
    event_type: EventType = Field(default=EventType.COMPLETION, description="Event type")


# Union type for all possible stream events
StreamEventUnion = Union[
    TextTokenEvent,
    ToolCallStartEvent, 
    ToolCallProgressEvent,
    ToolCallOutputEvent,
    ToolCallErrorEvent,
    CompletionEvent
]


def create_text_event(token: str) -> TextTokenEvent:
    """Factory function for text token events"""
    return TextTokenEvent(token=token)


def create_tool_start_event(
    tool_name: str,
    tool_type: ToolType,
    tool_id: str,
    arguments: Dict[str, Any]
) -> ToolCallStartEvent:
    """Factory function for tool start events"""
    return ToolCallStartEvent(
        tool_name=tool_name,
        tool_type=tool_type,
        tool_id=tool_id,
        arguments=arguments
    )


def create_tool_progress_event(
    tool_id: str,
    tool_name: str,
    status: ToolStatus,
    progress_data: Optional[Dict[str, Any]] = None
) -> ToolCallProgressEvent:
    """Factory function for tool progress events"""
    return ToolCallProgressEvent(
        tool_id=tool_id,
        tool_name=tool_name,
        status=status,
        progress_data=progress_data
    )


def create_tool_output_event(
    tool_id: str,
    tool_name: str,
    tool_type: ToolType,
    result: Any,
    status: ToolStatus
) -> ToolCallOutputEvent:
    """Factory function for tool output events"""
    return ToolCallOutputEvent(
        tool_id=tool_id,
        tool_name=tool_name,
        tool_type=tool_type,
        result=result,
        status=status
    )


def create_tool_error_event(
    tool_id: str,
    tool_name: str,
    tool_type: ToolType,
    error: str,
    error_details: Optional[Dict[str, Any]] = None
) -> ToolCallErrorEvent:
    """Factory function for tool error events"""
    return ToolCallErrorEvent(
        tool_id=tool_id,
        tool_name=tool_name,
        tool_type=tool_type,
        error=error,
        error_details=error_details
    )


def create_completion_event(response_data: Dict[str, Any]) -> CompletionEvent:
    """Factory function for completion events"""
    return CompletionEvent(response_data=response_data)
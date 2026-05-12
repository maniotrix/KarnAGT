"""
Event System

Clean event-driven architecture for service communication.
Follows industry standards for decoupled, maintainable systems.
"""

from .event_bus import EventBus, Event, get_event_bus
from .workspace_events import WorkspaceDeletedEvent, WorkspaceCreatedEvent
from .execution_events import ExecutionCompletedEvent, ExecutionTimeoutEvent

__all__ = [
    "EventBus",
    "Event", 
    "get_event_bus",
    "WorkspaceDeletedEvent", 
    "WorkspaceCreatedEvent",
    "ExecutionCompletedEvent",
    "ExecutionTimeoutEvent"
] 
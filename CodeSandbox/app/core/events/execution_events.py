#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Events

Clean event definitions for execution lifecycle events.
"""

from .event_bus import Event

class ExecutionCompletedEvent(Event):
    """Published when execution completes"""
    def __init__(self, workspace_id: str, execution_id: str, success: bool):
        super().__init__()
        self.workspace_id = workspace_id
        self.execution_id = execution_id
        self.success = success

class ExecutionTimeoutEvent(Event):
    """Published when execution times out"""
    def __init__(self, workspace_id: str, execution_id: str):
        super().__init__()
        self.workspace_id = workspace_id
        self.execution_id = execution_id 
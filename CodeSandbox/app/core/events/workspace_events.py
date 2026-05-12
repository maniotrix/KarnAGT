#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Events

Clean event definitions for workspace lifecycle events.
"""

from .event_bus import Event

class WorkspaceCreatedEvent(Event):
    """Published when a workspace is created"""
    def __init__(self, workspace_id: str):
        super().__init__()
        self.workspace_id = workspace_id

class WorkspaceDeletedEvent(Event):
    """Published when a workspace is deleted"""
    def __init__(self, workspace_id: str, reason: str = "manual"):
        super().__init__()
        self.workspace_id = workspace_id
        self.reason = reason 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Event Bus

Simple, clean event bus for decoupled service communication.
Follows industry standards for maintainable event-driven architecture.
"""

import asyncio
from typing import Dict, List, Type, Callable, Any
from datetime import datetime

from app.utils.logger import Loggers

class Event:
    """Base event class"""
    def __init__(self):
        self.timestamp = datetime.utcnow()

class EventBus:
    """
    Simple event bus for service decoupling
    
    Industry-standard publish-subscribe pattern.
    Services publish events, others subscribe without knowing about each other.
    """
    
    def __init__(self):
        self._subscribers: Dict[Type[Event], List[Callable]] = {}
        self.logger = Loggers.event_bus
        
        self.logger.info("Event bus initialized")
    
    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]):
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        
        self.logger.debug("Event handler subscribed",
                         event_type=event_type.__name__,
                         handler=handler.__name__)
    
    async def publish(self, event: Event):
        """
        Publish an event to all subscribers
        
        Args:
            event: Event instance to publish
        """
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])
        
        if not subscribers:
            self.logger.debug("No subscribers for event",
                            event_type=event_type.__name__)
            return
        
        self.logger.debug("Publishing event",
                         event_type=event_type.__name__,
                         subscriber_count=len(subscribers))
        
        # Call all subscribers (fire-and-forget for performance)
        tasks = []
        for handler in subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    handler(event)
            except Exception as e:
                self.logger.error("Event handler failed",
                                event_type=event_type.__name__,
                                handler=handler.__name__,
                                error=str(e))
        
        # Wait for async handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "total_event_types": len(self._subscribers),
            "total_subscribers": sum(len(handlers) for handlers in self._subscribers.values()),
            "event_types": list(self._subscribers.keys()),
            "subscribers_per_event": {
                event_type.__name__: len(handlers) 
                for event_type, handlers in self._subscribers.items()
            }
        }

# Global event bus instance for application-wide use
_global_event_bus: EventBus = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus 
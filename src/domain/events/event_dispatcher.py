# src/domain/events/event_dispatcher.py
import logging
from typing import Dict, List, Callable, Any, Type, Set

from .event_types import EventType, DomainEvent


class EventDispatcher:
    """
    Dispatches domain events to registered handlers.
    """
    def __init__(self):
        """Initialize the event dispatcher."""
        self.logger = logging.getLogger("domain.events.dispatcher")
        self.handlers = {}  # event_type -> list of handlers
        self.type_handlers = {}  # event class -> list of handlers
        
    def register(self, event_type: EventType, handler: Callable[[DomainEvent], None]):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Function to call when event occurs
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
            
        self.handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for event type: {event_type.name}")
        
    def register_for_class(self, event_class: Type[DomainEvent], handler: Callable[[DomainEvent], None]):
        """
        Register a handler for all events of a specific class.
        
        Args:
            event_class: Class of events to handle
            handler: Function to call when event occurs
        """
        class_name = event_class.__name__
        if class_name not in self.type_handlers:
            self.type_handlers[class_name] = []
            
        self.type_handlers[class_name].append(handler)
        self.logger.debug(f"Registered handler for event class: {class_name}")
        
    def dispatch(self, event: DomainEvent):
        """
        Dispatch an event to all registered handlers.
        
        Args:
            event: Event to dispatch
        """
        # Get handlers for this event type
        handlers = self.handlers.get(event.type, [])
        
        # Get handlers for this event class
        class_name = event.__class__.__name__
        class_handlers = self.type_handlers.get(class_name, [])
        
        # Combine handlers
        all_handlers = handlers + class_handlers
        
        if not all_handlers:
            self.logger.debug(f"No handlers registered for event: {event}")
            return
            
        self.logger.debug(f"Dispatching event {event} to {len(all_handlers)} handlers")
        
        # Call all handlers
        for handler in all_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {str(e)}")
                
    def unregister(self, event_type: EventType, handler: Callable[[DomainEvent], None]) -> bool:
        """
        Unregister a handler for a specific event type.
        
        Args:
            event_type: Type of event
            handler: Handler function to remove
            
        Returns:
            True if handler was removed, False if not found
        """
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            self.logger.debug(f"Unregistered handler for event type: {event_type.name}")
            return True
        return False
        
    def unregister_for_class(self, event_class: Type[DomainEvent], 
                           handler: Callable[[DomainEvent], None]) -> bool:
        """
        Unregister a handler for a specific event class.
        
        Args:
            event_class: Class of events
            handler: Handler function to remove
            
        Returns:
            True if handler was removed, False if not found
        """
        class_name = event_class.__name__
        if class_name in self.type_handlers and handler in self.type_handlers[class_name]:
            self.type_handlers[class_name].remove(handler)
            self.logger.debug(f"Unregistered handler for event class: {class_name}")
            return True
        return False
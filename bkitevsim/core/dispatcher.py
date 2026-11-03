"""Dispatcher bridge module for backwards-compatible API in bkitevsim."""
from bkitevsim.dispatchers.sequential_eventdispatcher import (
    SequentialEventDispatcher,
    DistributedEventDispatcher,
)

# Compatibility alias
Dispatcher = SequentialEventDispatcher

__all__ = ["Dispatcher", "SequentialEventDispatcher", "DistributedEventDispatcher"]

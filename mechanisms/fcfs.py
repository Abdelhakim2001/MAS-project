"""
FCFS (First-Come-First-Served) Mechanism
=========================================

Simple priority based on arrival order.
No bidding, no urgency - pure fairness.

Selection criteria:
1. First by barrier_time (when vehicle reached barrier)
2. Then by arrival_time (when vehicle was spawned)
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class FCFSMechanism(BaseMechanism):
    """
    First-Come-First-Served mechanism.
    
    Priority is determined strictly by arrival order:
    - Primary: barrier_time (when the vehicle reached the barrier)
    - Secondary: arrival_time (when the vehicle was spawned)
    
    This ensures fairness - whoever arrived first gets to go first.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "FCFS"
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Select winner by arrival order (first-come-first-served).
        
        Args:
            candidates: Vehicles waiting at barrier
            axis: Corridor axis (not used in FCFS)
            context: Additional context (not used in FCFS)
        
        Returns:
            SelectionResult with the earliest arriving vehicle
        """
        if not candidates:
            return None
        
        # Sort by barrier_time, then arrival_time
        # barrier_time may be None for vehicles not yet at barrier
        sorted_candidates = sorted(
            candidates,
            key=lambda v: (v.barrier_time or v.arrival_time, v.arrival_time)
        )
        
        winner = sorted_candidates[0]
        self.stats['selections'] += 1
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'fcfs',
                'barrier_time': winner.barrier_time,
                'arrival_time': winner.arrival_time,
                'num_candidates': len(candidates),
            }
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        At conflict zone, FCFS uses entry_time to corridor.
        """
        if not waiting:
            return None
        
        if len(waiting) == 1:
            return SelectionResult(winner=waiting[0], details={'method': 'single_vehicle'})
        
        # Sort by entry_time (when vehicle entered corridor)
        sorted_waiting = sorted(waiting, key=lambda v: v.entry_time or 0)
        winner = sorted_waiting[0]
        
        self.stats['conflict_selections'] += 1
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'fcfs_conflict',
                'entry_time': winner.entry_time,
                'num_waiting': len(waiting),
            }
        )
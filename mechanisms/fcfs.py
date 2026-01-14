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
    - Tertiary: vehicle_id (deterministic tie-breaker)
    """
    
    def __init__(self):
        super().__init__()
        self.name = "FCFS"
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Select winner by arrival order (first-come-first-served).
        """
        if not candidates:
            return None
        
        # Correction: Ajout de v.id pour le départage (Tie-Breaker)
        sorted_candidates = sorted(
            candidates,
            key=lambda v: (v.barrier_time or v.arrival_time, v.arrival_time, v.id)
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
        
        # Correction: Ajout de v.id pour le départage explicite
        # Si entry_time est égal, le véhicule avec le plus petit ID gagne
        sorted_waiting = sorted(waiting, key=lambda v: (v.entry_time or 0, v.id))
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
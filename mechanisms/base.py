"""
Base Mechanism Interface - Strategy Pattern
============================================

All selection mechanisms must implement this interface.
This allows easy addition of new mechanisms without modifying core code.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class SelectionResult:
    """Result of a mechanism selection"""
    
    def __init__(self, winner: 'Vehicle', details: Dict[str, Any] = None):
        self.winner = winner
        self.details = details or {}
    
    def __repr__(self):
        return f"SelectionResult(winner=V{self.winner.id}, details={self.details})"


class BaseMechanism(ABC):
    """
    Abstract base class for all selection mechanisms.
    
    Each mechanism must implement:
    - select(): Choose winner from candidates
    - select_at_conflict(): Handle conflict zone selection (may differ from barrier)
    """
    
    def __init__(self):
        self.name = "Base"
        self.stats = {
            'selections': 0,
            'conflict_selections': 0,
        }
    
    @abstractmethod
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Select a winner from candidates at the barrier.
        
        Args:
            candidates: List of vehicles waiting at barrier
            axis: The corridor axis (NS or EW)
            context: Additional context (current_step, etc.)
        
        Returns:
            SelectionResult with winner and details, or None if no candidates
        """
        pass
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Select a winner when multiple vehicles meet at conflict zone.
        
        Default implementation uses same logic as barrier selection.
        Override for mechanisms that need different conflict resolution.
        
        Args:
            waiting: List of vehicles waiting at intersection entrance
            context: Additional context
        
        Returns:
            SelectionResult with winner and details, or None
        """
        # Default: use same logic as barrier
        if not waiting:
            return None
        return self.select(waiting, None, context)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return mechanism statistics"""
        return self.stats.copy()
    
    def reset(self):
        """Reset mechanism state and statistics"""
        self.stats = {k: 0 for k in self.stats}
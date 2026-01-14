"""
Chicken Game Mechanism
======================

Game-theoretic approach to intersection crossing using the Chicken Game model.

Payoff Matrix:
              B: Yield    B: Go
    A: Yield    (1, 1)    (0, 3)
    A: Go       (3, 0)   (-10, -10)

Nash Equilibria:
- (Go, Yield) and (Yield, Go) are pure strategy Nash equilibria
- There's also a mixed strategy equilibrium

Properties:
- Anti-coordination game
- Both (Go, Yield) and (Yield, Go) are Pareto optimal
- (Go, Go) is catastrophic (collision)
- (Yield, Yield) is inefficient but safe
"""
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import random

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class ChickenAction(Enum):
    """Actions in the Chicken Game"""
    YIELD = "yield"
    GO = "go"


class ChickenStrategy(Enum):
    """Strategies for playing Chicken Game"""
    AGGRESSIVE = "aggressive"      # Always Go
    COOPERATIVE = "cooperative"    # Always Yield
    MIXED = "mixed"               # Probabilistic
    RATIONAL = "rational"         # Based on expected utility
    TIT_FOR_TAT = "tit_for_tat"   # Reciprocate opponent's last action


@dataclass
class ChickenGameOutcome:
    """Result of a Chicken Game interaction"""
    player_a_id: int
    player_b_id: int
    action_a: ChickenAction
    action_b: ChickenAction
    payoff_a: int
    payoff_b: int
    winner_id: Optional[int]
    is_collision: bool
    is_deadlock: bool


# Payoff Matrix
PAYOFF_MATRIX = {
    (ChickenAction.YIELD, ChickenAction.YIELD): (1, 1),    # Both wait - safe but slow
    (ChickenAction.YIELD, ChickenAction.GO): (0, 3),       # A yields, B goes
    (ChickenAction.GO, ChickenAction.YIELD): (3, 0),       # A goes, B yields
    (ChickenAction.GO, ChickenAction.GO): (-10, -10),      # COLLISION!
}


class ChickenGameMechanism(BaseMechanism):
    """
    Chicken Game mechanism for intersection priority.
    
    Each vehicle independently decides whether to GO or YIELD.
    The outcome is determined by the combination of actions.
    
    Game Theory Analysis:
    - Pure Strategy Nash Equilibria: (Go, Yield) and (Yield, Go)
    - Mixed Strategy Equilibrium: Each player randomizes
    - No dominant strategy exists
    """
    
    def __init__(self, default_strategy: ChickenStrategy = ChickenStrategy.RATIONAL):
        super().__init__()
        self.name = "Chicken Game"
        self.default_strategy = default_strategy
        
        self.stats.update({
            'games_played': 0,
            'collisions': 0,  # Should always be 0!
            'near_misses': 0,  # Both chose GO but collision avoided
            'deadlocks': 0,   # Both chose YIELD
            'clean_passes': 0,  # Exactly one GO, one YIELD
            'total_payoff_a': 0,
            'total_payoff_b': 0,
            'go_count': 0,
            'yield_count': 0,
        })
        
        self.history: List[ChickenGameOutcome] = []
        self.last_outcome: Optional[ChickenGameOutcome] = None
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Selection at barrier using Chicken Game.
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return SelectionResult(
                winner=candidates[0],
                details={'method': 'single_candidate'}
            )
        
        # Play Chicken Game between first two candidates
        v1, v2 = candidates[0], candidates[1]
        outcome = self._play_chicken_game(v1, v2)
        
        # Determine winner
        if outcome.winner_id is not None:
            winner = v1 if outcome.winner_id == v1.id else v2
        else:
            # Deadlock or collision - use urgency as tiebreaker
            winner = v1 if v1.urgency >= v2.urgency else v2
        
        # Update stats
        self._update_stats(outcome)
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'chicken_game',
                'action_a': outcome.action_a.value,
                'action_b': outcome.action_b.value,
                'payoff_a': outcome.payoff_a,
                'payoff_b': outcome.payoff_b,
                'is_collision': outcome.is_collision,
                'is_deadlock': outcome.is_deadlock,
            }
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Conflict resolution using Chicken Game.
        """
        return self.select(waiting, None, context)
    
    def _play_chicken_game(self, v1: 'Vehicle', v2: 'Vehicle') -> ChickenGameOutcome:
        """
        Play one round of Chicken Game between two vehicles.
        """
        # Get actions from each vehicle
        action1 = self._get_action(v1, v2.urgency)
        action2 = self._get_action(v2, v1.urgency)
        
        # Look up payoffs
        payoff1, payoff2 = PAYOFF_MATRIX[(action1, action2)]
        
        # Determine outcome
        is_collision = (action1 == ChickenAction.GO and action2 == ChickenAction.GO)
        is_deadlock = (action1 == ChickenAction.YIELD and action2 == ChickenAction.YIELD)
        
        # Determine winner
        winner_id = None
        if action1 == ChickenAction.GO and action2 == ChickenAction.YIELD:
            winner_id = v1.id
        elif action1 == ChickenAction.YIELD and action2 == ChickenAction.GO:
            winner_id = v2.id
        elif is_collision:
            # COLLISION PREVENTION: Override to avoid actual collision
            # In reality, we prevent this by having one yield
            # This simulates the "near miss" scenario
            if v1.urgency >= v2.urgency:
                action2 = ChickenAction.YIELD  # Force v2 to yield
                winner_id = v1.id
            else:
                action1 = ChickenAction.YIELD  # Force v1 to yield
                winner_id = v2.id
            payoff1, payoff2 = -5, -5  # Near miss penalty
        
        outcome = ChickenGameOutcome(
            player_a_id=v1.id,
            player_b_id=v2.id,
            action_a=action1,
            action_b=action2,
            payoff_a=payoff1,
            payoff_b=payoff2,
            winner_id=winner_id,
            is_collision=is_collision,
            is_deadlock=is_deadlock
        )
        
        self.history.append(outcome)
        self.last_outcome = outcome
        
        return outcome
    
    def _get_action(self, vehicle: 'Vehicle', other_urgency: int) -> ChickenAction:
        """
        Determine vehicle's action based on strategy.
        """
        # Use vehicle's BDI if available
        if hasattr(vehicle, 'chicken_game_decision'):
            decision = vehicle.chicken_game_decision(other_urgency)
            return ChickenAction.GO if decision == 'go' else ChickenAction.YIELD
        
        # Otherwise use default strategy
        return self._apply_strategy(vehicle.urgency, other_urgency)
    
    def _apply_strategy(self, own_urgency: int, other_urgency: int) -> ChickenAction:
        """
        Apply strategy to determine action.
        """
        if self.default_strategy == ChickenStrategy.AGGRESSIVE:
            return ChickenAction.GO
        
        elif self.default_strategy == ChickenStrategy.COOPERATIVE:
            return ChickenAction.YIELD
        
        elif self.default_strategy == ChickenStrategy.MIXED:
            # Mixed strategy: probability of GO proportional to urgency
            p_go = own_urgency / 10.0
            return ChickenAction.GO if random.random() < p_go else ChickenAction.YIELD
        
        elif self.default_strategy == ChickenStrategy.RATIONAL:
            # Rational: based on expected utility
            p_other_go = other_urgency / 10.0
            
            eu_yield = 1 * (1 - p_other_go) + 0 * p_other_go
            eu_go = 3 * (1 - p_other_go) + (-10) * p_other_go
            
            # Adjust for own urgency
            eu_go += own_urgency * 0.3
            
            return ChickenAction.GO if eu_go > eu_yield else ChickenAction.YIELD
        
        elif self.default_strategy == ChickenStrategy.TIT_FOR_TAT:
            # Start cooperative, then mirror opponent's last action
            if self.history:
                last = self.history[-1]
                # Mirror what opponent did
                return last.action_b  # Assuming we're player A
            return ChickenAction.YIELD  # Start cooperative
        
        return ChickenAction.YIELD  # Default to safe
    
    def _update_stats(self, outcome: ChickenGameOutcome):
        """Update statistics after a game"""
        self.stats['games_played'] += 1
        
        if outcome.is_collision:
            self.stats['near_misses'] += 1  # We prevent actual collisions
        elif outcome.is_deadlock:
            self.stats['deadlocks'] += 1
        else:
            self.stats['clean_passes'] += 1
        
        self.stats['total_payoff_a'] += outcome.payoff_a
        self.stats['total_payoff_b'] += outcome.payoff_b
        
        if outcome.action_a == ChickenAction.GO:
            self.stats['go_count'] += 1
        else:
            self.stats['yield_count'] += 1
        
        if outcome.action_b == ChickenAction.GO:
            self.stats['go_count'] += 1
        else:
            self.stats['yield_count'] += 1
    
    def get_nash_equilibria(self) -> List[Tuple[ChickenAction, ChickenAction]]:
        """
        Return the Nash Equilibria of the Chicken Game.
        
        Pure Strategy NE: (Go, Yield) and (Yield, Go)
        """
        return [
            (ChickenAction.GO, ChickenAction.YIELD),
            (ChickenAction.YIELD, ChickenAction.GO),
        ]
    
    def get_pareto_optimal(self) -> List[Tuple[ChickenAction, ChickenAction]]:
        """
        Return the Pareto Optimal outcomes.
        
        (Go, Yield), (Yield, Go), and (Yield, Yield) are Pareto optimal.
        (Go, Go) is NOT Pareto optimal (both could be better off).
        """
        return [
            (ChickenAction.GO, ChickenAction.YIELD),
            (ChickenAction.YIELD, ChickenAction.GO),
            (ChickenAction.YIELD, ChickenAction.YIELD),
        ]
    
    def get_game_theory_analysis(self) -> Dict[str, Any]:
        """
        Return complete game theory analysis.
        """
        return {
            'game_name': 'Chicken Game (Hawk-Dove)',
            'players': ['Vehicle A', 'Vehicle B'],
            'strategies': ['Yield', 'Go'],
            'payoff_matrix': {
                '(Yield, Yield)': (1, 1),
                '(Yield, Go)': (0, 3),
                '(Go, Yield)': (3, 0),
                '(Go, Go)': (-10, -10),
            },
            'nash_equilibria': {
                'pure_strategy': ['(Go, Yield)', '(Yield, Go)'],
                'mixed_strategy': 'Each player plays Go with probability 3/13',
            },
            'pareto_optimal': ['(Go, Yield)', '(Yield, Go)', '(Yield, Yield)'],
            'dominant_strategy': 'None - No dominant strategy exists',
            'social_optimum': '(Yield, Yield) is safe but inefficient',
            'properties': {
                'anti_coordination': True,
                'symmetric': True,
                'zero_sum': False,
            },
            'empirical_results': {
                'games_played': self.stats['games_played'],
                'clean_passes': self.stats['clean_passes'],
                'deadlocks': self.stats['deadlocks'],
                'near_misses': self.stats['near_misses'],
                'go_percentage': self.stats['go_count'] / max(1, self.stats['go_count'] + self.stats['yield_count']) * 100,
            }
        }
    
    def get_last_game(self) -> Optional[Dict]:
        """Return last game outcome"""
        if not self.last_outcome:
            return None
        
        o = self.last_outcome
        return {
            'player_a': o.player_a_id,
            'player_b': o.player_b_id,
            'action_a': o.action_a.value,
            'action_b': o.action_b.value,
            'payoff_a': o.payoff_a,
            'payoff_b': o.payoff_b,
            'winner': o.winner_id,
            'outcome_type': 'collision' if o.is_collision else 'deadlock' if o.is_deadlock else 'clean',
        }
    
    def reset(self):
        """Reset mechanism"""
        super().reset()
        self.stats.update({
            'games_played': 0,
            'collisions': 0,
            'near_misses': 0,
            'deadlocks': 0,
            'clean_passes': 0,
            'total_payoff_a': 0,
            'total_payoff_b': 0,
            'go_count': 0,
            'yield_count': 0,
        })
        self.history.clear()
        self.last_outcome = None
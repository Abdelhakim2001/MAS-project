"""
Multi-Agent Negotiation Mechanism
=================================

Vehicles negotiate when they meet at barriers or conflict zone.
Multiple negotiation strategies available.

Negotiation Types:
1. STOCHASTIC: Dice-rolling with bid-weighted probabilities
2. MARGINAL_UTILITY: Compare utility functions
3. TOKEN_BASED: Exchange tokens (future use)
"""
import random
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class NegotiationType(Enum):
    """Types of negotiation protocols"""
    STOCHASTIC = "Stochastic (Dice Roll)"
    MARGINAL_UTILITY = "Marginal Utility"
    TOKEN_BASED = "Token-Based"


@dataclass
class NegotiationResult:
    """Result of a negotiation between two vehicles"""
    winner_id: int
    loser_id: int
    method: NegotiationType
    rounds: int
    details: Dict[str, Any]


class NegotiationMechanism(BaseMechanism):
    """
    Multi-Agent Negotiation mechanism.
    
    When 2+ vehicles compete, they engage in negotiation.
    The protocol determines how the winner is selected.
    
    Supported protocols:
    - STOCHASTIC: Random with bid-weighted probability
    - MARGINAL_UTILITY: Deterministic utility comparison
    - TOKEN_BASED: Token exchange system
    """
    
    def __init__(self, method: NegotiationType = NegotiationType.STOCHASTIC):
        super().__init__()
        self.name = "Negotiation"
        self.method = method
        self.stats.update({
            'negotiations_held': 0,
            'stochastic_wins': 0,
            'utility_wins': 0,
            'token_wins': 0,
            'rounds_total': 0,
        })
        self.negotiation_history: List[NegotiationResult] = []
        
        # Active negotiation state (for visualization)
        self.active_negotiation: Optional[tuple] = None
        self.last_result: Optional[NegotiationResult] = None
    
    def negotiate(self, v1: 'Vehicle', v2: 'Vehicle', 
                  context: Dict[str, Any] = None) -> NegotiationResult:
        """
        Run negotiation between two vehicles.
        
        Args:
            v1, v2: The two competing vehicles
            context: Additional context (current_step, location, etc.)
        
        Returns:
            NegotiationResult with winner and details
        """
        context = context or {}
        
        # Mark vehicles as negotiating
        v1.start_negotiation()
        v2.start_negotiation()
        self.active_negotiation = (v1.id, v2.id)
        
        # Run appropriate protocol
        if self.method == NegotiationType.STOCHASTIC:
            result = self._negotiate_stochastic(v1, v2, context)
        elif self.method == NegotiationType.MARGINAL_UTILITY:
            result = self._negotiate_utility(v1, v2, context)
        elif self.method == NegotiationType.TOKEN_BASED:
            result = self._negotiate_tokens(v1, v2, context)
        else:
            result = self._negotiate_stochastic(v1, v2, context)
        
        # Update vehicles
        winner = v1 if result.winner_id == v1.id else v2
        loser = v2 if result.winner_id == v1.id else v1
        winner.end_negotiation(won=True)
        loser.end_negotiation(won=False)
        
        # Record result
        self.stats['negotiations_held'] += 1
        self.stats['rounds_total'] += result.rounds
        self.negotiation_history.append(result)
        self.last_result = result
        self.active_negotiation = None
        
        return result
    
    def _negotiate_stochastic(self, v1: 'Vehicle', v2: 'Vehicle',
                              context: Dict[str, Any]) -> NegotiationResult:
        """
        Stochastic negotiation: dice-roll weighted by bids.
        
        Higher bid = higher probability of winning.
        Multiple rounds possible.
        """
        max_rounds = 3
        rounds = 0
        
        bid1 = v1.calculate_bid()
        bid2 = v2.calculate_bid()
        total = bid1 + bid2
        
        rolls_v1 = []
        rolls_v2 = []
        
        for _ in range(max_rounds):
            rounds += 1
            
            # Weighted probability
            if total > 0:
                p1 = bid1 / total
            else:
                p1 = 0.5
            
            # Each vehicle rolls
            roll1 = random.random()
            roll2 = random.random()
            rolls_v1.append(round(roll1, 3))
            rolls_v2.append(round(roll2, 3))
            
            # Weighted comparison
            score1 = roll1 * p1
            score2 = roll2 * (1 - p1)
            
            if abs(score1 - score2) > 0.1:  # Clear winner
                break
        
        # Determine winner
        avg1 = sum(rolls_v1) / len(rolls_v1) * (bid1 + 1)
        avg2 = sum(rolls_v2) / len(rolls_v2) * (bid2 + 1)
        
        winner_id = v1.id if avg1 >= avg2 else v2.id
        loser_id = v2.id if winner_id == v1.id else v1.id
        
        self.stats['stochastic_wins'] += 1
        
        return NegotiationResult(
            winner_id=winner_id,
            loser_id=loser_id,
            method=NegotiationType.STOCHASTIC,
            rounds=rounds,
            details={
                'v1_id': v1.id,
                'v2_id': v2.id,
                'v1_bid': bid1,
                'v2_bid': bid2,
                'v1_rolls': rolls_v1,
                'v2_rolls': rolls_v2,
                'v1_score': round(avg1, 3),
                'v2_score': round(avg2, 3),
            }
        )
    
    def _negotiate_utility(self, v1: 'Vehicle', v2: 'Vehicle',
                           context: Dict[str, Any]) -> NegotiationResult:
        """
        Marginal Utility negotiation: compare utility functions.
        
        Utility = f(urgency, fuel, distance, wait_time)
        Higher utility vehicle wins.
        """
        current_step = context.get('current_step', 0)
        
        # Calculate utility for each vehicle
        utility1 = self._calculate_utility(v1, current_step)
        utility2 = self._calculate_utility(v2, current_step)
        
        winner_id = v1.id if utility1 >= utility2 else v2.id
        loser_id = v2.id if winner_id == v1.id else v1.id
        
        self.stats['utility_wins'] += 1
        
        return NegotiationResult(
            winner_id=winner_id,
            loser_id=loser_id,
            method=NegotiationType.MARGINAL_UTILITY,
            rounds=1,
            details={
                'v1_id': v1.id,
                'v2_id': v2.id,
                'v1_utility': round(utility1, 2),
                'v2_utility': round(utility2, 2),
                'v1_components': self._get_utility_components(v1, current_step),
                'v2_components': self._get_utility_components(v2, current_step),
            }
        )
    
    def _calculate_utility(self, v: 'Vehicle', current_step: int) -> float:
        """
        Calculate marginal utility for a vehicle.
        
        Components:
        - Urgency weight: 40%
        - Fuel urgency: 30% (low fuel = high priority)
        - Wait time: 20% (longer wait = higher priority)
        - Distance: 10% (shorter remaining = higher priority)
        """
        # Urgency component (0-10 normalized to 0-1)
        urgency_score = v.urgency / 10.0
        
        # Fuel urgency (inverted: low fuel = high score)
        fuel_score = 1.0 - (v.fuel_level / 100.0)
        
        # Wait time component
        wait_time = current_step - v.arrival_time
        wait_score = min(wait_time / 50.0, 1.0)  # Cap at 50 steps
        
        # Distance component (inverted: short distance = high score)
        distance_score = 1.0 - (v.distance_remaining / 10.0)
        
        # Weighted sum
        utility = (
            0.40 * urgency_score +
            0.30 * fuel_score +
            0.20 * wait_score +
            0.10 * distance_score
        )
        
        return utility * 100  # Scale to 0-100
    
    def _get_utility_components(self, v: 'Vehicle', current_step: int) -> Dict:
        """Return individual utility components for debugging"""
        wait_time = current_step - v.arrival_time
        return {
            'urgency': v.urgency,
            'fuel': v.fuel_level,
            'wait_time': wait_time,
            'distance': v.distance_remaining,
        }
    
    def _negotiate_tokens(self, v1: 'Vehicle', v2: 'Vehicle',
                          context: Dict[str, Any]) -> NegotiationResult:
        """
        Token-based negotiation: vehicles exchange tokens.
        
        Placeholder implementation - returns bid-based winner.
        Future: implement token exchange protocol.
        """
        bid1 = v1.calculate_bid()
        bid2 = v2.calculate_bid()
        
        winner_id = v1.id if bid1 >= bid2 else v2.id
        loser_id = v2.id if winner_id == v1.id else v1.id
        
        self.stats['token_wins'] += 1
        
        return NegotiationResult(
            winner_id=winner_id,
            loser_id=loser_id,
            method=NegotiationType.TOKEN_BASED,
            rounds=1,
            details={
                'v1_id': v1.id,
                'v2_id': v2.id,
                'v1_bid': bid1,
                'v2_bid': bid2,
                'resolution': 'bid_comparison',
            }
        )
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Select winner via negotiation.
        
        If only 1 candidate: no negotiation needed.
        If 2+ candidates: negotiate between top 2.
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return SelectionResult(
                winner=candidates[0],
                details={'method': 'single_candidate'}
            )
        
        # Sort by bid to select top 2 negotiators
        sorted_candidates = sorted(
            candidates, 
            key=lambda v: v.calculate_bid(), 
            reverse=True
        )
        
        v1, v2 = sorted_candidates[0], sorted_candidates[1]
        
        # Run negotiation
        neg_result = self.negotiate(v1, v2, context)
        
        # Find winner vehicle
        winner = v1 if neg_result.winner_id == v1.id else v2
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'negotiation',
                'negotiation_type': self.method.value,
                'winner_id': neg_result.winner_id,
                'loser_id': neg_result.loser_id,
                'rounds': neg_result.rounds,
                'negotiation_details': neg_result.details,
            }
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Negotiate at conflict zone.
        """
        return self.select(waiting, None, context)
    
    def get_last_negotiation(self) -> Optional[Dict]:
        """Return the most recent negotiation result"""
        if not self.last_result:
            return None
        return {
            'winner_id': self.last_result.winner_id,
            'loser_id': self.last_result.loser_id,
            'method': self.last_result.method.value,
            'rounds': self.last_result.rounds,
            'details': self.last_result.details,
        }
    
    def get_negotiation_stats(self) -> Dict:
        """Return negotiation statistics"""
        stats = self.stats.copy()
        if stats['negotiations_held'] > 0:
            stats['avg_rounds'] = stats['rounds_total'] / stats['negotiations_held']
        else:
            stats['avg_rounds'] = 0
        return stats
    
    def reset(self):
        """Reset negotiation state"""
        super().reset()
        self.stats.update({
            'negotiations_held': 0,
            'stochastic_wins': 0,
            'utility_wins': 0,
            'token_wins': 0,
            'rounds_total': 0,
        })
        self.negotiation_history.clear()
        self.active_negotiation = None
        self.last_result = None
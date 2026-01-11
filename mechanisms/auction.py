"""
Auction Mechanism (Vickrey / Second-Price)
==========================================

Vehicles bid for priority based on urgency.
Winner pays the second-highest bid (incentive compatible).

Bid calculation:
- Normal vehicles: urgency × 10
- Urgent vehicles: 1000 + urgency

This ensures urgent vehicles (ambulance, fire truck) get priority
while normal vehicles can still compete via their urgency level.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class AuctionMechanism(BaseMechanism):
    """
    Vickrey (Second-Price) Auction mechanism.
    
    Properties:
    - Truthful: Optimal strategy is to bid true value
    - Winner pays 2nd highest bid (not their own bid)
    - Urgent vehicles have significant bid advantage
    
    Statistics tracked:
    - auctions_held: Number of auctions conducted
    - total_revenue: Sum of all prices paid
    - urgent_wins: Times urgent vehicles won
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Auction"
        self.stats.update({
            'auctions_held': 0,
            'total_revenue': 0,
            'urgent_wins': 0,
            'avg_price': 0.0,
        })
        self.auction_history: List[Dict] = []
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Run Vickrey auction to select winner.
        
        Args:
            candidates: Vehicles bidding for corridor access
            axis: Corridor axis (for logging)
            context: Should contain 'current_step' for history
        
        Returns:
            SelectionResult with auction winner and payment details
        """
        if not candidates:
            return None
        
        context = context or {}
        current_step = context.get('current_step', 0)
        
        # Calculate all bids
        bids = [(v, v.calculate_bid()) for v in candidates]
        
        # Sort by bid (highest first)
        bids.sort(key=lambda x: x[1], reverse=True)
        
        winner, winning_bid = bids[0]
        
        # Second-price: winner pays the 2nd highest bid
        # If only one bidder, they pay 0
        price = bids[1][1] if len(bids) > 1 else 0
        winner.price_paid = price
        
        # Record auction
        auction_record = {
            'step': current_step,
            'axis': axis.value if axis else 'conflict',
            'winner_id': winner.id,
            'winner_urgency': winner.urgency,
            'is_urgent': winner.is_urgent(),
            'winning_bid': winning_bid,
            'price_paid': price,
            'num_bidders': len(candidates),
            'all_bids': [(v.id, v.urgency, b) for v, b in bids],
        }
        self.auction_history.append(auction_record)
        
        # Update stats
        self.stats['auctions_held'] += 1
        self.stats['total_revenue'] += price
        if winner.is_urgent():
            self.stats['urgent_wins'] += 1
        if self.stats['auctions_held'] > 0:
            self.stats['avg_price'] = self.stats['total_revenue'] / self.stats['auctions_held']
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'vickrey_auction',
                'winning_bid': winning_bid,
                'price_paid': price,
                'num_bidders': len(candidates),
                'is_urgent': winner.is_urgent(),
                'all_bids': auction_record['all_bids'],
            }
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        At conflict zone, highest bid wins (no payment at conflict).
        """
        if not waiting:
            return None
        
        if len(waiting) == 1:
            return SelectionResult(winner=waiting[0], details={'method': 'single_vehicle'})
        
        # Sort by bid
        sorted_waiting = sorted(waiting, key=lambda v: v.calculate_bid(), reverse=True)
        winner = sorted_waiting[0]
        
        self.stats['conflict_selections'] += 1
        
        return SelectionResult(
            winner=winner,
            details={
                'method': 'auction_conflict',
                'winning_bid': winner.calculate_bid(),
                'num_waiting': len(waiting),
            }
        )
    
    def get_last_auction(self) -> Optional[Dict]:
        """Return the most recent auction record"""
        return self.auction_history[-1] if self.auction_history else None
    
    def get_auction_history(self) -> List[Dict]:
        """Return full auction history"""
        return self.auction_history.copy()
    
    def reset(self):
        """Reset auction state"""
        super().reset()
        self.stats.update({
            'auctions_held': 0,
            'total_revenue': 0,
            'urgent_wins': 0,
            'avg_price': 0.0,
        })
        self.auction_history.clear()
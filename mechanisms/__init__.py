"""
Mechanisms Package
==================

Contains all selection mechanisms for the intersection simulation.

Available mechanisms:
- FCFS: First-Come-First-Served
- Auction: English Auction OR Vickrey (Second-Price) Auction
- Negotiation: Multi-Round Negotiation with Marginal Utility
- Chicken Game: Game-Theoretic approach (Hawk-Dove game)

To add a new mechanism:
1. Create a new file in this directory (e.g., my_mechanism.py)
2. Implement BaseMechanism interface
3. Register it in the factory below
"""

from mechanisms.base import BaseMechanism, SelectionResult
from mechanisms.fcfs import FCFSMechanism
from mechanisms.auction import AuctionMechanism, AuctionType
from mechanisms.negotiation import NegotiationMechanism
from mechanisms.chicken_game import ChickenGameMechanism, ChickenStrategy, ChickenAction

from constants import Mechanism


# Deprecated - kept for backward compatibility
class NegotiationType:
    """Deprecated - only Marginal Utility is used now"""
    STOCHASTIC = "stochastic"
    MARGINAL_UTILITY = "marginal_utility"
    TOKEN_BASED = "token_based"


def create_mechanism(mechanism_type: Mechanism, 
                     auction_type: AuctionType = AuctionType.VICKREY,
                     chicken_strategy: ChickenStrategy = ChickenStrategy.RATIONAL,
                     **kwargs) -> BaseMechanism:
    """
    Factory function to create mechanism instances.
    
    Args:
        mechanism_type: The type of mechanism to create
        auction_type: For AUCTION, choose ENGLISH or VICKREY
        chicken_strategy: For CHICKEN, choose strategy
        **kwargs: Additional arguments (ignored)
    
    Returns:
        Instance of the requested mechanism
    
    Example:
        >>> mechanism = create_mechanism(Mechanism.AUCTION, AuctionType.ENGLISH)
        >>> mechanism = create_mechanism(Mechanism.AUCTION, AuctionType.VICKREY)
        >>> mechanism = create_mechanism(Mechanism.NEGOTIATION)
        >>> mechanism = create_mechanism(Mechanism.CHICKEN)
    """
    if mechanism_type == Mechanism.FCFS:
        return FCFSMechanism()
    
    elif mechanism_type == Mechanism.AUCTION:
        return AuctionMechanism(auction_type=auction_type)
    
    elif mechanism_type == Mechanism.NEGOTIATION:
        return NegotiationMechanism()
    
    elif mechanism_type == Mechanism.CHICKEN:
        return ChickenGameMechanism(default_strategy=chicken_strategy)
    
    else:
        raise ValueError(f"Unknown mechanism type: {mechanism_type}")


__all__ = [
    'BaseMechanism',
    'SelectionResult',
    'FCFSMechanism',
    'AuctionMechanism',
    'AuctionType',
    'NegotiationMechanism',
    'NegotiationType',
    'ChickenGameMechanism',
    'ChickenStrategy',
    'ChickenAction',
    'create_mechanism',
]
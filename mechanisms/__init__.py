"""
Mechanisms Package
==================

Contains all selection mechanisms for the intersection simulation.

Available mechanisms:
- FCFS: First-Come-First-Served
- Auction: Vickrey (Second-Price) Auction
- Negotiation: Multi-Agent Negotiation

To add a new mechanism:
1. Create a new file in this directory (e.g., my_mechanism.py)
2. Implement BaseMechanism interface
3. Register it in the factory below
"""

from mechanisms.base import BaseMechanism, SelectionResult
from mechanisms.fcfs import FCFSMechanism
from mechanisms.auction import AuctionMechanism
from mechanisms.negotiation import NegotiationMechanism, NegotiationType

from constants import Mechanism


def create_mechanism(mechanism_type: Mechanism, **kwargs) -> BaseMechanism:
    """
    Factory function to create mechanism instances.
    
    Args:
        mechanism_type: The type of mechanism to create
        **kwargs: Additional arguments for specific mechanisms
    
    Returns:
        Instance of the requested mechanism
    
    Example:
        >>> mechanism = create_mechanism(Mechanism.AUCTION)
        >>> mechanism = create_mechanism(Mechanism.NEGOTIATION, 
        ...                               negotiation_type=NegotiationType.STOCHASTIC)
    """
    if mechanism_type == Mechanism.FCFS:
        return FCFSMechanism()
    
    elif mechanism_type == Mechanism.AUCTION:
        return AuctionMechanism()
    
    elif mechanism_type == Mechanism.NEGOTIATION:
        neg_type = kwargs.get('negotiation_type', NegotiationType.STOCHASTIC)
        return NegotiationMechanism(method=neg_type)
    
    else:
        raise ValueError(f"Unknown mechanism type: {mechanism_type}")


__all__ = [
    'BaseMechanism',
    'SelectionResult',
    'FCFSMechanism',
    'AuctionMechanism',
    'NegotiationMechanism',
    'NegotiationType',
    'create_mechanism',
]
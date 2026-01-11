"""
Negotiation Module - Compatibility Layer
========================================

This file provides backward compatibility for code that imports from 'negotiation'.
All actual implementation is in mechanisms/negotiation.py
"""

# Re-export everything from mechanisms.negotiation for compatibility
from mechanisms.negotiation import (
    NegotiationType,
    NegotiationResult,
    NegotiationMechanism as NegotiationProtocol,  # Alias for compatibility
)

__all__ = ['NegotiationType', 'NegotiationResult', 'NegotiationProtocol']
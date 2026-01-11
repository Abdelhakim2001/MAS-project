"""
Constants for Intersection Model with Negotiation
"""
from enum import Enum, auto

GRID_SIZE = 15
CENTER = 7
INTERSECTION_POS = (7, 7)

PARKING_ZONES = {
    'N': {'start': (6, 0), 'end': (8, 2)},
    'S': {'start': (6, 12), 'end': (8, 14)},
    'E': {'start': (12, 6), 'end': (14, 8)},
    'W': {'start': (0, 6), 'end': (2, 8)},
}

BARRIER_POSITIONS = {
    'N': (7, 3),
    'S': (7, 11),
    'E': (11, 7),
    'W': (3, 7),
}

ENTRY_POINTS = {
    'N': (7, 4),
    'S': (7, 10),
    'E': (10, 7),
    'W': (4, 7),
}

EXIT_POINTS = {
    'N': (7, 10),
    'S': (7, 4),
    'E': (4, 7),
    'W': (10, 7),
}

MOVE_DIRECTION = {
    'N': (0, 1),
    'S': (0, -1),
    'E': (-1, 0),
    'W': (1, 0),
}

# Positions just BEFORE the intersection (where vehicles wait)
WAITING_POSITIONS = {
    'N': (7, 6),
    'S': (7, 8),
    'E': (8, 7),
    'W': (6, 7),
}


class VehicleState(Enum):
    IN_PARKING = auto()
    AT_BARRIER = auto()
    IN_CORRIDOR = auto()
    IN_CONFLICT = auto()
    NEGOTIATING = auto()
    EXITED = auto()


class CorridorAxis(Enum):
    NS = "North-South"
    EW = "East-West"


class Mechanism(Enum):
    FCFS = "First-Come-First-Served"
    AUCTION = "Auction (Vickrey)"
    NEGOTIATION = "Multi-Agent Negotiation"


class VehicleType(Enum):
    NORMAL = "Normal"
    URGENT = "Urgent"


DIRECTION_AXIS = {
    'N': CorridorAxis.NS,
    'S': CorridorAxis.NS,
    'E': CorridorAxis.EW,
    'W': CorridorAxis.EW,
}

MIN_URGENCY = 1
MAX_URGENCY = 10
URGENT_THRESHOLD = 9
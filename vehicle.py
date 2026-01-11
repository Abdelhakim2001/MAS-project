"""
Vehicle Class with Negotiation Support
======================================

Represents a vehicle in the intersection simulation.
Supports FCFS, Auction, and Negotiation mechanisms.
"""
import random
from constants import (
    VehicleState, VehicleType, Mechanism,
    ENTRY_POINTS, EXIT_POINTS, MOVE_DIRECTION, DIRECTION_AXIS,
    PARKING_ZONES, BARRIER_POSITIONS,
    MIN_URGENCY, MAX_URGENCY, URGENT_THRESHOLD
)


class Vehicle:
    """
    A vehicle that navigates through the intersection.
    
    Attributes:
        id: Unique vehicle identifier
        direction: Cardinal direction (N, S, E, W)
        urgency: Priority level (1-10)
        vehicle_type: NORMAL or URGENT
        state: Current state in simulation
        
    Positions:
        pos: Current grid position
        parking_pos: Starting position in parking
        entry_pos: Entry point to corridor
        exit_pos: Exit point from corridor
        barrier_pos: Barrier gate position
    
    Timing:
        arrival_time: Step when spawned
        barrier_time: Step when reached barrier
        entry_time: Step when entered corridor
        exit_time: Step when exited grid
    """
    
    def __init__(self, vehicle_id: int, direction: str, arrival_time: int, 
                 urgency: int = None, is_urgent: bool = False,
                 mechanism: Mechanism = Mechanism.FCFS):
        self.id = vehicle_id
        self.direction = direction
        self.axis = DIRECTION_AXIS[direction]
        self.mechanism = mechanism
        
        # Positions
        self.pos = None
        self.parking_pos = None
        self.entry_pos = ENTRY_POINTS[direction]
        self.exit_pos = EXIT_POINTS[direction]
        self.barrier_pos = BARRIER_POSITIONS[direction]
        
        # State and timing
        self.state = VehicleState.IN_PARKING
        self.arrival_time = arrival_time
        self.barrier_time = None
        self.entry_time = None
        self.exit_time = None
        
        # Initialize urgency based on mechanism
        self._init_urgency(urgency, is_urgent)
        
        # Auction attributes
        self.bid_amount = 0
        self.price_paid = 0
        
        # Negotiation attributes
        self.fuel_level = random.randint(30, 100)
        self.distance_remaining = 10
        self.negotiation_wins = 0
        self.negotiation_losses = 0
        self.is_negotiating = False
    
    def _init_urgency(self, urgency: int, is_urgent: bool):
        """Initialize urgency based on mechanism type"""
        if self.mechanism in [Mechanism.AUCTION, Mechanism.NEGOTIATION]:
            if is_urgent:
                # Forced urgent (e.g., emergency vehicle)
                self.urgency = MAX_URGENCY
                self.vehicle_type = VehicleType.URGENT
            elif urgency is not None:
                # Use provided urgency
                self.urgency = max(MIN_URGENCY, min(urgency, MAX_URGENCY))
                self.vehicle_type = (VehicleType.URGENT 
                                     if self.urgency >= URGENT_THRESHOLD 
                                     else VehicleType.NORMAL)
            else:
                # Random urgency
                self.urgency = random.randint(MIN_URGENCY, MAX_URGENCY)
                self.vehicle_type = (VehicleType.URGENT 
                                     if self.urgency >= URGENT_THRESHOLD 
                                     else VehicleType.NORMAL)
        else:
            # FCFS: no urgency
            self.urgency = 0
            self.vehicle_type = VehicleType.NORMAL
    
    def is_urgent(self) -> bool:
        """Check if vehicle is urgent type"""
        if self.mechanism == Mechanism.FCFS:
            return False
        return self.vehicle_type == VehicleType.URGENT
    
    def calculate_bid(self) -> int:
        """
        Calculate bid amount based on urgency.
        
        For FCFS: returns 0
        For AUCTION/NEGOTIATION:
            - Normal: urgency × 10
            - Urgent: 1000 + urgency
        """
        if self.mechanism == Mechanism.FCFS:
            self.bid_amount = 0
            return 0
        
        if self.is_urgent():
            self.bid_amount = 1000 + self.urgency
        else:
            self.bid_amount = self.urgency * 10
        return self.bid_amount
    
    def set_parking_position(self, pos: tuple):
        """Set initial parking position"""
        self.parking_pos = pos
        self.pos = pos
    
    def move_to_barrier(self, current_time: int):
        """Move vehicle to barrier queue"""
        self.pos = self.barrier_pos
        self.state = VehicleState.AT_BARRIER
        self.barrier_time = current_time
    
    def enter_corridor(self, current_time: int):
        """Enter the corridor from barrier"""
        self.pos = self.entry_pos
        self.state = VehicleState.IN_CORRIDOR
        self.entry_time = current_time
        self.distance_remaining = 6  # Reset distance
    
    def get_next_position(self):
        """Calculate next position based on direction"""
        if self.pos is None:
            return self.entry_pos
        
        dx, dy = MOVE_DIRECTION[self.direction]
        new_x = self.pos[0] + dx
        new_y = self.pos[1] + dy
        
        # Check bounds (15x15 grid)
        if not (0 <= new_x < 15 and 0 <= new_y < 15):
            return None  # Exit the grid
        
        return (new_x, new_y)
    
    def move(self):
        """Move vehicle one step forward"""
        if self.state not in [VehicleState.IN_CORRIDOR, VehicleState.IN_CONFLICT]:
            return False
        
        next_pos = self.get_next_position()
        
        if next_pos is None:
            # Exiting the grid
            self.pos = None
            self.state = VehicleState.EXITED
            return True
        
        self.pos = next_pos
        self.distance_remaining = max(0, self.distance_remaining - 1)
        self.fuel_level = max(0, self.fuel_level - 1)
        return True
    
    def has_exited(self) -> bool:
        """Check if vehicle has exited the grid"""
        return self.state == VehicleState.EXITED
    
    # Negotiation methods
    def start_negotiation(self):
        """Mark vehicle as currently negotiating"""
        self.is_negotiating = True
    
    def end_negotiation(self, won: bool):
        """End negotiation and record result"""
        self.is_negotiating = False
        if won:
            self.negotiation_wins += 1
        else:
            self.negotiation_losses += 1
    
    def get_negotiation_data(self) -> dict:
        """Get data needed for negotiation"""
        return {
            'id': self.id,
            'urgency': self.urgency,
            'fuel_level': self.fuel_level,
            'distance_remaining': self.distance_remaining,
            'arrival_time': self.arrival_time,
            'wait_time': self.barrier_time - self.arrival_time if self.barrier_time else 0,
        }
    
    def __repr__(self):
        if self.mechanism == Mechanism.NEGOTIATION:
            return f"V{self.id}({self.direction}, bid={self.calculate_bid()}, fuel={self.fuel_level})"
        elif self.mechanism == Mechanism.AUCTION:
            return f"V{self.id}({self.direction}, bid={self.calculate_bid()})"
        else:
            return f"V{self.id}({self.direction})"
"""
Vehicle Class with BDI Architecture and Negotiation Support
===========================================================

Represents a vehicle agent in the intersection simulation.
Implements BDI (Beliefs-Desires-Intentions) architecture as required.

BDI Components:
- Beliefs: Knowledge about environment and other vehicles
- Desires: Goals the agent wants to achieve
- Intentions: Current plan of action
"""
import random
from typing import Dict, List, Any, Optional
from constants import (
    VehicleState, VehicleType, Mechanism,
    ENTRY_POINTS, EXIT_POINTS, MOVE_DIRECTION, DIRECTION_AXIS,
    PARKING_ZONES, BARRIER_POSITIONS,
    MIN_URGENCY, MAX_URGENCY, URGENT_THRESHOLD
)


class BDIComponent:
    """
    BDI (Beliefs-Desires-Intentions) component for cognitive behavior.
    
    This implements the cognitive architecture required for autonomous agents.
    """
    
    def __init__(self, vehicle_id: int):
        self.vehicle_id = vehicle_id
        
        # BELIEFS: What the agent knows/perceives about the world
        self.beliefs = {
            'own_position': None,
            'own_urgency': 0,
            'own_fuel': 100,
            'intersection_state': 'unknown',  # free, occupied, contested
            'other_vehicles': {},  # id -> {position, direction, urgency}
            'conflict_zone_free': True,
            'corridor_reserved': False,
            'waiting_vehicles': [],
            'estimated_wait_time': 0,
        }
        
        # DESIRES: Goals the agent wants to achieve (priority ordered)
        self.desires = [
            {'goal': 'cross_safely', 'priority': 1.0, 'achieved': False},
            {'goal': 'minimize_wait_time', 'priority': 0.8, 'achieved': False},
            {'goal': 'avoid_collision', 'priority': 1.0, 'achieved': True},  # Always active
            {'goal': 'conserve_fuel', 'priority': 0.3, 'achieved': False},
        ]
        
        # INTENTIONS: Current plan of action
        self.intentions = {
            'current_plan': 'wait',  # wait, negotiate, cross, yield
            'strategy': 'cooperative',  # cooperative, aggressive, defensive
            'next_action': None,
            'committed_until': None,  # Step until which intention is locked
        }
    
    def update_beliefs(self, perception: Dict[str, Any]):
        """Update beliefs based on new perceptions"""
        for key, value in perception.items():
            if key in self.beliefs:
                self.beliefs[key] = value
    
    def add_other_vehicle(self, vehicle_id: int, position: tuple, 
                          direction: str, urgency: int):
        """Add or update belief about another vehicle"""
        self.beliefs['other_vehicles'][vehicle_id] = {
            'position': position,
            'direction': direction,
            'urgency': urgency,
            'threat_level': self._assess_threat(position, direction)
        }
    
    def _assess_threat(self, other_pos: tuple, other_dir: str) -> float:
        """Assess threat level of another vehicle (0-1)"""
        if other_pos is None or self.beliefs['own_position'] is None:
            return 0.0
        
        # Higher threat if on perpendicular path near intersection
        own_pos = self.beliefs['own_position']
        distance = abs(own_pos[0] - other_pos[0]) + abs(own_pos[1] - other_pos[1])
        
        if distance < 3:
            return 0.9  # Very close = high threat
        elif distance < 5:
            return 0.5  # Medium distance
        return 0.1  # Far away
    
    def deliberate(self) -> str:
        """
        Deliberation process: Select intention based on beliefs and desires.
        
        Returns the action to take: 'wait', 'negotiate', 'cross', 'yield'
        """
        # Check highest priority desires
        if not self.beliefs['conflict_zone_free']:
            return 'wait'  # Safety first
        
        if self.beliefs['waiting_vehicles']:
            # Other vehicles waiting - need to negotiate
            return 'negotiate'
        
        if self.beliefs['corridor_reserved'] and not self.beliefs.get('has_reservation'):
            return 'wait'
        
        # Clear to proceed
        return 'cross'
    
    def form_intention(self, action: str, strategy: str = None):
        """Form a new intention"""
        self.intentions['current_plan'] = action
        if strategy:
            self.intentions['strategy'] = strategy
        self.intentions['next_action'] = action
    
    def get_negotiation_strategy(self) -> str:
        """
        Determine negotiation strategy based on beliefs.
        
        Returns: 'aggressive', 'cooperative', or 'defensive'
        """
        own_urgency = self.beliefs['own_urgency']
        own_fuel = self.beliefs['own_fuel']
        
        if own_urgency >= 9:  # Emergency vehicle
            return 'aggressive'
        elif own_fuel < 30:  # Low fuel
            return 'aggressive'
        elif own_urgency <= 3:
            return 'cooperative'  # Low urgency = willing to yield
        else:
            return 'defensive'  # Moderate urgency
    
    def should_yield(self, other_urgency: int) -> bool:
        """
        Decide whether to yield to another vehicle.
        
        Based on urgency comparison and strategy.
        """
        own_urgency = self.beliefs['own_urgency']
        strategy = self.intentions['strategy']
        
        if strategy == 'aggressive':
            return other_urgency > own_urgency + 3
        elif strategy == 'cooperative':
            return other_urgency >= own_urgency
        else:  # defensive
            return other_urgency > own_urgency


class Vehicle:
    """
    A vehicle agent that navigates through the intersection.
    
    Implements both reactive and cognitive (BDI) behaviors.
    
    Attributes:
        id: Unique vehicle identifier
        direction: Cardinal direction (N, S, E, W)
        urgency: Priority level (1-10)
        vehicle_type: NORMAL or URGENT
        state: Current state in simulation
        bdi: BDI cognitive component
        
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
        
        # BDI Cognitive Component
        self.bdi = BDIComponent(vehicle_id)
        self._init_bdi()
    
    def _init_bdi(self):
        """Initialize BDI component with vehicle's attributes"""
        self.bdi.update_beliefs({
            'own_urgency': self.urgency,
            'own_fuel': self.fuel_level,
            'own_position': self.pos,
        })
        
        # Set initial strategy based on urgency
        strategy = self.bdi.get_negotiation_strategy()
        self.bdi.form_intention('wait', strategy)
    
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
    
    # =========================================================================
    # BDI COGNITIVE BEHAVIORS
    # =========================================================================
    
    def perceive(self, environment_state: Dict[str, Any]):
        """
        Perception: Update beliefs based on environment.
        
        This is the first step in the BDI cycle.
        """
        self.bdi.update_beliefs({
            'own_position': self.pos,
            'own_fuel': self.fuel_level,
            'conflict_zone_free': environment_state.get('conflict_zone_free', True),
            'corridor_reserved': environment_state.get('corridor_reserved', False),
            'waiting_vehicles': environment_state.get('waiting_vehicles', []),
            'intersection_state': environment_state.get('intersection_state', 'unknown'),
        })
        
        # Update beliefs about other vehicles
        for v_info in environment_state.get('other_vehicles', []):
            self.bdi.add_other_vehicle(
                v_info['id'], v_info['position'], 
                v_info['direction'], v_info['urgency']
            )
    
    def deliberate(self) -> str:
        """
        Deliberation: Decide what to do based on beliefs and desires.
        
        Returns the intended action.
        """
        return self.bdi.deliberate()
    
    def act(self, intended_action: str) -> bool:
        """
        Action: Execute the intended action.
        
        Returns True if action was successful.
        """
        if intended_action == 'cross':
            return self.move()
        elif intended_action == 'wait':
            return True  # Successfully waited
        elif intended_action == 'yield':
            return True  # Successfully yielded
        elif intended_action == 'negotiate':
            self.start_negotiation()
            return True
        return False
    
    def bdi_cycle(self, environment_state: Dict[str, Any]) -> str:
        """
        Complete BDI cycle: Perceive -> Deliberate -> Act
        
        Returns the action taken.
        """
        # 1. Perceive
        self.perceive(environment_state)
        
        # 2. Deliberate
        action = self.deliberate()
        
        # 3. Form intention
        self.bdi.form_intention(action)
        
        # 4. Act
        self.act(action)
        
        return action
    
    # =========================================================================
    # REACTIVE BEHAVIORS (Emergency responses)
    # =========================================================================
    
    def emergency_stop(self) -> bool:
        """
        Reactive behavior: Emergency stop to avoid collision.
        
        Triggered when immediate danger is detected.
        """
        # Update intention immediately
        self.bdi.form_intention('wait', 'defensive')
        return True
    
    def collision_avoidance(self, other_vehicle_pos: tuple) -> bool:
        """
        Reactive behavior: Avoid collision with another vehicle.
        
        Returns True if evasive action taken.
        """
        if self.pos is None or other_vehicle_pos is None:
            return False
        
        # Calculate distance
        distance = abs(self.pos[0] - other_vehicle_pos[0]) + \
                   abs(self.pos[1] - other_vehicle_pos[1])
        
        if distance < 2:  # Imminent collision
            self.emergency_stop()
            return True
        return False
    
    def speed_adjustment(self, traffic_density: float) -> float:
        """
        Reactive behavior: Adjust speed based on traffic.
        
        Returns speed multiplier (0.0 to 1.0).
        """
        if traffic_density > 0.8:
            return 0.5  # Slow down significantly
        elif traffic_density > 0.5:
            return 0.75  # Moderate slowdown
        return 1.0  # Normal speed
    
    # =========================================================================
    # GAME THEORY: Chicken Game Decision
    # =========================================================================
    
    def chicken_game_decision(self, other_urgency: int, 
                               own_history: List[str] = None) -> str:
        """
        Make decision in Chicken Game scenario.
        
        Payoff Matrix:
                    B: Yield    B: Go
        A: Yield     (1, 1)    (0, 3)
        A: Go        (3, 0)   (-10, -10)
        
        Returns: 'yield' or 'go'
        """
        own_urgency = self.urgency
        strategy = self.bdi.intentions['strategy']
        
        # Calculate expected utility for each action
        # Assume other vehicle's probability of 'go' based on their urgency
        p_other_go = other_urgency / 10.0
        
        # Expected utility of 'yield': 1 * (1 - p_other_go) + 0 * p_other_go
        eu_yield = 1 * (1 - p_other_go) + 0 * p_other_go
        
        # Expected utility of 'go': 3 * (1 - p_other_go) + (-10) * p_other_go
        eu_go = 3 * (1 - p_other_go) + (-10) * p_other_go
        
        # Adjust based on own urgency
        eu_go += own_urgency * 0.5  # Higher urgency = more willing to risk
        
        # Strategy modifier
        if strategy == 'aggressive':
            eu_go += 2
        elif strategy == 'cooperative':
            eu_yield += 2
        
        # Decision
        if eu_go > eu_yield:
            return 'go'
        return 'yield'

    def __repr__(self):
        if self.mechanism == Mechanism.NEGOTIATION:
            return f"V{self.id}({self.direction}, bid={self.calculate_bid()}, fuel={self.fuel_level})"
        elif self.mechanism == Mechanism.AUCTION:
            return f"V{self.id}({self.direction}, bid={self.calculate_bid()})"
        else:
            return f"V{self.id}({self.direction})"
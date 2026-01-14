"""
Intersection Model with Multi-Agent Support
============================================
"""
import random
from typing import Optional, List, Dict
from collections import deque

from constants import (
    GRID_SIZE, INTERSECTION_POS, PARKING_ZONES, BARRIER_POSITIONS,
    WAITING_POSITIONS, VehicleState, VehicleType, CorridorAxis, 
    DIRECTION_AXIS, Mechanism
)
from vehicle import Vehicle
# AJOUT DE AuctionType DANS L'IMPORT
from mechanisms import create_mechanism, NegotiationType, AuctionType
from debug import logger


class SimpleIntersection:
    """
    Intersection simulation with pluggable selection mechanisms.
    """
    
    def __init__(self, mechanism: Mechanism = Mechanism.FCFS,
                 negotiation_type: NegotiationType = NegotiationType.STOCHASTIC,
                 # AJOUT DU PARAMÈTRE AUCTION_TYPE
                 auction_type: AuctionType = AuctionType.VICKREY,
                 spawn_rate: float = 0.1, urgent_probability: float = 0.05,
                 seed: int = None):
        if seed:
            random.seed(seed)
        
        self.mechanism_type = mechanism
        self.spawn_rate = spawn_rate
        self.urgent_probability = urgent_probability if mechanism != Mechanism.FCFS else 0.0
        self.step_count = 0
        self.vehicle_counter = 0
        
        # Create mechanism using factory WITH AUCTION TYPE
        self.mechanism = create_mechanism(mechanism, 
                                        negotiation_type=negotiation_type,
                                        auction_type=auction_type)
        
        # Vehicle storage
        self.parking_zones: Dict[str, List[Vehicle]] = {
            'N': [], 'S': [], 'E': [], 'W': []
        }
        self.barrier_queues: Dict[str, deque] = {
            'N': deque(), 'S': deque(), 'E': deque(), 'W': deque()
        }
        self.corridor_reserved = {
            CorridorAxis.NS: None,
            CorridorAxis.EW: None,
        }
        self.corridor_vehicles: Dict[int, Vehicle] = {}
        self.conflict_zone_vehicle = None
        self.exited_vehicles: List[Vehicle] = []
        
        # Statistics
        self.stats = {
            'total_spawned': 0,
            'total_crossed': 0,
            'urgent_crossed': 0,
            'total_wait_time': 0,
            'collisions_avoided': 0,
        }
        
        logger.clear()
        # Log the specific name of the mechanism (e.g. "Auction (English)")
        logger.log('state', f"Simulation started: {self.mechanism.name}", {})
    
    # ... LE RESTE DE LA CLASSE RESTE INCHANGÉ ...
    # (Copiez ici le reste des méthodes spawn_vehicle, move_parking_to_barrier, etc.
    #  depuis votre version précédente corrigée)

    # =========================================================================
    # SPAWNING
    # =========================================================================
    def spawn_vehicle(self, direction: str) -> Vehicle:
        """Spawn a new vehicle in the parking zone"""
        self.vehicle_counter += 1
        
        is_urgent = (self.mechanism_type != Mechanism.FCFS and 
                     random.random() < self.urgent_probability)
        
        vehicle = Vehicle(
            vehicle_id=self.vehicle_counter,
            direction=direction,
            arrival_time=self.step_count,
            is_urgent=is_urgent,
            mechanism=self.mechanism_type
        )
        
        # Calculate parking position
        parking = PARKING_ZONES[direction]
        idx = len(self.parking_zones[direction])
        if direction in ['N', 'S']:
            px = parking['start'][0] + (idx % 3)
            py = parking['start'][1] + (idx // 3)
        else:
            px = parking['start'][0] + (idx // 3)
            py = parking['start'][1] + (idx % 3)
        
        vehicle.set_parking_position((px, py))
        self.parking_zones[direction].append(vehicle)
        self.stats['total_spawned'] += 1
        
        logger.log_spawn(vehicle.id, direction, vehicle.urgency)
        return vehicle
    
    def try_spawn_vehicles(self):
        """Attempt to spawn vehicles based on spawn rate"""
        for direction in ['N', 'S', 'E', 'W']:
            if random.random() < self.spawn_rate:
                if len(self.parking_zones[direction]) < 9:
                    self.spawn_vehicle(direction)
    
    # =========================================================================
    # PARKING TO BARRIER
    # =========================================================================
    def move_parking_to_barrier(self):
        """Move highest priority vehicle from parking to barrier"""
        for direction in ['N', 'S', 'E', 'W']:
            parking = self.parking_zones[direction]
            barrier_queue = self.barrier_queues[direction]
            
            if not parking or len(barrier_queue) >= 3:
                continue
            
            # Sort based on mechanism
            if self.mechanism_type == Mechanism.FCFS:
                parking.sort(key=lambda v: v.arrival_time)
            else:
                # Auction/Negotiation: sort by bid
                parking.sort(key=lambda v: v.calculate_bid(), reverse=True)
            
            vehicle = parking.pop(0)
            vehicle.move_to_barrier(self.step_count)
            barrier_queue.append(vehicle)
            
            logger.log('enter_corridor', 
                      f"V{vehicle.id} → BARRIER ({direction})", 
                      {'vehicle_id': vehicle.id, 'direction': direction})
    
    # =========================================================================
    # BARRIER TO CORRIDOR
    # =========================================================================
    def process_barrier(self, axis: CorridorAxis):
        """Process barrier queue for an axis"""
        if self.corridor_reserved[axis] is not None:
            return
        
        directions = ['N', 'S'] if axis == CorridorAxis.NS else ['E', 'W']
        
        # Collect all candidates
        candidates = []
        for d in directions:
            candidates.extend(list(self.barrier_queues[d]))
        
        if not candidates:
            return
        
        # Use mechanism to select winner
        context = {'current_step': self.step_count, 'axis': axis}
        result = self.mechanism.select(candidates, axis, context)
        
        if result and result.winner:
            winner = result.winner
            
            # Remove from barrier queue
            self.barrier_queues[winner.direction].remove(winner)
            
            # Reserve corridor and enter
            self.corridor_reserved[axis] = winner.id
            winner.enter_corridor(self.step_count)
            self.corridor_vehicles[winner.id] = winner
            
            # Record wait time
            wait_time = self.step_count - winner.arrival_time
            self.stats['total_wait_time'] += wait_time
            
            # Log based on mechanism type
            logger.log_enter_corridor(
                winner.id, winner.direction, 
                axis.value, self.mechanism.name
            )
            
            # Log mechanism-specific details
            if hasattr(self.mechanism, 'get_last_auction'):
                method = result.details.get('method', '')
                if 'auction' in method:
                    details = result.details
                    logger.log_auction(
                        axis.value, winner.id, winner.urgency,
                        details.get('winning_bid', 0),
                        details.get('price_paid', 0),
                        len(details.get('all_bids', {})),
                        details.get('all_bids', {}),
                        auction_type=method.replace('_auction', ''),
                        total_rounds=details.get('total_rounds', 1)
                    )
            elif result.details.get('method') == 'negotiation':
                neg_details = result.details.get('negotiation_details', {})
                logger.log_negotiation(
                    result.details.get('winner_id'),
                    result.details.get('loser_id'),
                    result.details.get('negotiation_type', 'unknown'),
                    neg_details
                )
    
    # =========================================================================
    # CORRIDOR MOVEMENT & CONFLICT ZONE (CORRECTED)
    # =========================================================================
    def move_corridor_vehicles(self):
        """Move vehicles in corridor and handle conflict zone"""
        exited_ids = []
        
        # Step 1: Identify vehicles waiting at THEIR SPECIFIC intersection line
        waiting = []
        for v in self.corridor_vehicles.values():
            # Check strictly against the waiting position for THIS vehicle's direction
            if (v.pos == WAITING_POSITIONS[v.direction] and 
                v.state != VehicleState.IN_CONFLICT):
                waiting.append(v)
        
        # Step 2: Handle conflict resolution if the zone is free
        conflict_winner = None
        
        if self.conflict_zone_vehicle is None:
            if len(waiting) >= 2:
                # Multiple vehicles - use mechanism to resolve
                context = {'current_step': self.step_count, 'location': 'conflict'}
                result = self.mechanism.select_at_conflict(waiting, context)
                if result:
                    conflict_winner = result.winner
                    self._log_conflict_resolution(result, waiting)
            elif len(waiting) == 1:
                # Single vehicle - automatic winner
                conflict_winner = waiting[0]
        
        # Step 3: Move vehicles
        for vehicle in list(self.corridor_vehicles.values()):
            current_pos = vehicle.pos
            
            # --- Logic for vehicles at Waiting Position ---
            if current_pos == WAITING_POSITIONS[vehicle.direction]:
                # If this vehicle is already crossing (won previously), just move
                if vehicle.state == VehicleState.IN_CONFLICT:
                    self._move_vehicle_safely(vehicle, exited_ids)
                    continue
                
                # If someone else is in the zone -> Wait
                if self.conflict_zone_vehicle is not None:
                    self.stats['collisions_avoided'] += 1
                    continue
                
                # If this vehicle is the winner of this turn -> Enter
                if conflict_winner and vehicle.id == conflict_winner.id:
                    self.conflict_zone_vehicle = vehicle.id
                    vehicle.state = VehicleState.IN_CONFLICT
                    self._move_vehicle_safely(vehicle, exited_ids)
                    logger.log_enter_conflict_zone(
                        vehicle.id, vehicle.direction, vehicle.urgency
                    )
                    continue
                
                # Otherwise -> Lost conflict, Wait
                self.stats['collisions_avoided'] += 1
                continue
            
            # --- Logic for vehicles exiting Conflict Zone ---
            if current_pos == INTERSECTION_POS:
                # Vehicle moves out of intersection
                self._move_vehicle_safely(vehicle, exited_ids)
                
                # Free the zone AFTER the move
                self.conflict_zone_vehicle = None
                vehicle.state = VehicleState.IN_CORRIDOR
                logger.log_exit_conflict_zone(vehicle.id, vehicle.direction)
                continue
            
            # --- Normal Movement ---
            self._move_vehicle_safely(vehicle, exited_ids)
        
        # Clean up exited vehicles
        for vid in exited_ids:
            del self.corridor_vehicles[vid]

    def _move_vehicle_safely(self, vehicle: Vehicle, exited_ids: List[int]):
        """Helper to move vehicle and check exit conditions"""
        vehicle.move()
        
        if vehicle.has_exited():
            vehicle.exit_time = self.step_count
            total_time = vehicle.exit_time - vehicle.arrival_time
            wait_time = (vehicle.entry_time - vehicle.arrival_time 
                        if vehicle.entry_time else 0)
            
            self.corridor_reserved[vehicle.axis] = None
            
            # Double check to free conflict zone if vehicle exited directly from it
            if self.conflict_zone_vehicle == vehicle.id:
                self.conflict_zone_vehicle = None
            
            self.exited_vehicles.append(vehicle)
            exited_ids.append(vehicle.id)
            self.stats['total_crossed'] += 1
            if vehicle.is_urgent():
                self.stats['urgent_crossed'] += 1
            
            logger.log_exit_grid(
                vehicle.id, vehicle.direction, total_time, wait_time
            )

    def _log_conflict_resolution(self, result, waiting):
        """Helper for logging detailed conflict info"""
        method = result.details.get('method', 'unknown')
        conflict_winner = result.winner
        
        if 'Marginal Utility' in method or 'negotiation' in method.lower():
            loser = waiting[1] if conflict_winner.id == waiting[0].id else waiting[0]
            logger.log_negotiation(
                winner_id=conflict_winner.id,
                loser_id=loser.id,
                method=method,
                details=result.details
            )
        elif 'auction' in method.lower():
            logger.log_auction(
                axis='conflict',
                winner_id=conflict_winner.id,
                winner_urgency=conflict_winner.urgency,
                winning_bid=result.details.get('winning_bid', 0),
                price_paid=result.details.get('price_paid', 0),
                num_bidders=len(waiting),
                all_bids=result.details.get('all_bids', {}),
                auction_type=method.replace('_auction', ''),
                total_rounds=result.details.get('total_rounds', 1)
            )
        else:
            # FCFS Log
            logger.log('negotiation', 
                      f"CONFLICT: V{waiting[0].id} vs V{waiting[1].id} → V{conflict_winner.id} WINS",
                      {'method': method})

    # =========================================================================
    # MAIN STEP
    # =========================================================================
    def step(self):
        """Execute one simulation step"""
        self.step_count += 1
        logger.set_step(self.step_count)
        
        self.try_spawn_vehicles()
        self.move_parking_to_barrier()
        
        for axis in [CorridorAxis.NS, CorridorAxis.EW]:
            self.process_barrier(axis)
        
        self.move_corridor_vehicles()
    
    # =========================================================================
    # GETTERS (UNCHANGED)
    # =========================================================================
    def get_all_vehicles_positions(self) -> List[Dict]:
        """Get positions of all vehicles for visualization"""
        result = []
        for direction, vehicles in self.parking_zones.items():
            for i, v in enumerate(vehicles):
                result.append(self._vehicle_to_dict(v, 'parking', i))
        for direction, queue in self.barrier_queues.items():
            for i, v in enumerate(queue):
                result.append(self._vehicle_to_dict(v, 'barrier', i))
        for v in self.corridor_vehicles.values():
            is_waiting = v.pos in WAITING_POSITIONS.values()
            if v.state == VehicleState.IN_CONFLICT:
                state = 'conflict'
            elif is_waiting:
                state = 'waiting'
            elif v.is_negotiating:
                state = 'negotiating'
            else:
                state = 'corridor'
            result.append(self._vehicle_to_dict(v, state, None, is_waiting))
        return result
    
    def _vehicle_to_dict(self, v: Vehicle, state: str, queue_pos: int = None,
                         waiting_at_intersection: bool = False) -> Dict:
        return {
            'id': v.id,
            'direction': v.direction,
            'pos': v.pos,
            'state': state,
            'urgency': v.urgency if self.mechanism_type != Mechanism.FCFS else None,
            'bid': v.calculate_bid() if self.mechanism_type != Mechanism.FCFS else None,
            'is_urgent': v.is_urgent(),
            'is_negotiating': v.is_negotiating,
            'fuel': v.fuel_level,
            'queue_pos': queue_pos,
            'waiting_at_intersection': waiting_at_intersection,
        }
    
    def get_stats(self) -> Dict:
        """Get simulation statistics"""
        avg_wait = 0
        if self.stats['total_crossed'] > 0:
            avg_wait = self.stats['total_wait_time'] / self.stats['total_crossed']
        
        mech_stats = self.mechanism.get_stats()
        waiting_count = sum(1 for v in self.corridor_vehicles.values() 
                           if v.pos in WAITING_POSITIONS.values())
        
        result = {
            'step': self.step_count,
            'mechanism': self.mechanism_type.value,
            'total_spawned': self.stats['total_spawned'],
            'total_crossed': self.stats['total_crossed'],
            'urgent_crossed': self.stats['urgent_crossed'],
            'parking_count': sum(len(p) for p in self.parking_zones.values()),
            'barrier_count': sum(len(q) for q in self.barrier_queues.values()),
            'corridor_count': len(self.corridor_vehicles),
            'waiting_at_intersection': waiting_count,
            'avg_wait_time': avg_wait,
            'ns_corridor': 'RESERVED' if self.corridor_reserved[CorridorAxis.NS] else 'FREE',
            'ew_corridor': 'RESERVED' if self.corridor_reserved[CorridorAxis.EW] else 'FREE',
            'conflict_zone': 'OCCUPIED' if self.conflict_zone_vehicle else 'FREE',
            'collisions_avoided': self.stats['collisions_avoided'],
        }
        
        if hasattr(self.mechanism, 'stats'):
            result.update(mech_stats)
        
        if hasattr(self.mechanism, 'method'):
            result['negotiation_method'] = self.mechanism.method.value
        
        return result
    
    def get_last_auction(self) -> Optional[Dict]:
        if hasattr(self.mechanism, 'get_last_auction'):
            return self.mechanism.get_last_auction()
        return None
    
    def get_last_negotiation(self) -> Optional[Dict]:
        if hasattr(self.mechanism, 'get_last_negotiation'):
            return self.mechanism.get_last_negotiation()
        return None
    
    def get_negotiation_stats(self) -> Dict:
        if hasattr(self.mechanism, 'get_negotiation_stats'):
            return self.mechanism.get_negotiation_stats()
        return {}
    
    def reset(self):
        self.step_count = 0
        self.vehicle_counter = 0
        for p in self.parking_zones.values():
            p.clear()
        for q in self.barrier_queues.values():
            q.clear()
        self.corridor_reserved = {CorridorAxis.NS: None, CorridorAxis.EW: None}
        self.corridor_vehicles.clear()
        self.conflict_zone_vehicle = None
        self.exited_vehicles.clear()
        self.stats = {k: 0 for k in self.stats}
        self.mechanism.reset()
        logger.clear()
        logger.log('state', f"RESET: {self.mechanism_type.value}", {})
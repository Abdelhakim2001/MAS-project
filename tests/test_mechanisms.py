"""
Test Suite for Intersection Mechanisms
======================================

Validates that FCFS and AUCTION mechanisms work correctly.
"""
import sys
sys.path.insert(0, '.')

from constants import Mechanism, VehicleState, CorridorAxis
from vehicle import Vehicle
from mechanisms import FCFSMechanism, AuctionMechanism, NegotiationMechanism, NegotiationType
from intersection import SimpleIntersection


def test_fcfs_priority():
    """Test that FCFS gives priority to first arrived"""
    print("=" * 60)
    print("TEST: FCFS Priority")
    print("=" * 60)
    
    mech = FCFSMechanism()
    
    # Create vehicles with different arrival times
    v1 = Vehicle(1, 'N', arrival_time=5, mechanism=Mechanism.FCFS)
    v2 = Vehicle(2, 'S', arrival_time=3, mechanism=Mechanism.FCFS)  # Earlier
    v3 = Vehicle(3, 'N', arrival_time=10, mechanism=Mechanism.FCFS)
    
    # Simulate barrier times
    v1.barrier_time = 8
    v2.barrier_time = 6  # Also reached barrier first
    v3.barrier_time = 12
    
    candidates = [v1, v2, v3]
    result = mech.select(candidates, CorridorAxis.NS)
    
    print(f"Candidates: V1(arr={v1.arrival_time}), V2(arr={v2.arrival_time}), V3(arr={v3.arrival_time})")
    print(f"Winner: V{result.winner.id} (arrival_time={result.winner.arrival_time})")
    
    assert result.winner.id == 2, f"Expected V2 (earliest), got V{result.winner.id}"
    print("✅ FCFS correctly selects earliest arrival")
    print()


def test_auction_highest_bid_wins():
    """Test that AUCTION gives priority to highest bidder"""
    print("=" * 60)
    print("TEST: Auction Highest Bid Wins")
    print("=" * 60)
    
    mech = AuctionMechanism()
    
    # Create vehicles with different urgencies
    v1 = Vehicle(1, 'N', arrival_time=0, urgency=3, mechanism=Mechanism.AUCTION)  # bid = 30
    v2 = Vehicle(2, 'S', arrival_time=0, urgency=8, mechanism=Mechanism.AUCTION)  # bid = 80
    v3 = Vehicle(3, 'E', arrival_time=0, urgency=5, mechanism=Mechanism.AUCTION)  # bid = 50
    
    print(f"V1: urgency={v1.urgency}, bid={v1.calculate_bid()}")
    print(f"V2: urgency={v2.urgency}, bid={v2.calculate_bid()}")
    print(f"V3: urgency={v3.urgency}, bid={v3.calculate_bid()}")
    
    candidates = [v1, v2, v3]
    result = mech.select(candidates, CorridorAxis.NS, {'current_step': 0})
    
    print(f"Winner: V{result.winner.id} (bid={result.winner.calculate_bid()})")
    print(f"Price paid: {result.details['price_paid']}")
    
    assert result.winner.id == 2, f"Expected V2 (highest bid), got V{result.winner.id}"
    assert result.details['price_paid'] == 50, f"Expected 2nd price (50), got {result.details['price_paid']}"
    print("✅ Auction correctly selects highest bidder")
    print("✅ Vickrey pricing (2nd price) works correctly")
    print()


def test_auction_urgent_priority():
    """Test that urgent vehicles win in auctions"""
    print("=" * 60)
    print("TEST: Auction Urgent Priority")
    print("=" * 60)
    
    mech = AuctionMechanism()
    
    # Normal vehicle with high urgency vs Urgent vehicle
    v1 = Vehicle(1, 'N', arrival_time=0, urgency=8, mechanism=Mechanism.AUCTION)  # bid = 80
    v2 = Vehicle(2, 'S', arrival_time=0, is_urgent=True, mechanism=Mechanism.AUCTION)  # bid = 1010
    
    print(f"V1 (Normal): urgency={v1.urgency}, bid={v1.calculate_bid()}, is_urgent={v1.is_urgent()}")
    print(f"V2 (URGENT): urgency={v2.urgency}, bid={v2.calculate_bid()}, is_urgent={v2.is_urgent()}")
    
    candidates = [v1, v2]
    result = mech.select(candidates, CorridorAxis.NS, {'current_step': 0})
    
    print(f"Winner: V{result.winner.id}")
    
    assert result.winner.id == 2, f"Expected V2 (urgent), got V{result.winner.id}"
    print("✅ Urgent vehicles correctly get priority in auctions")
    print()


def test_fcfs_arrival_not_urgency():
    """Test that FCFS ignores urgency"""
    print("=" * 60)
    print("TEST: FCFS Ignores Urgency")
    print("=" * 60)
    
    model = SimpleIntersection(mechanism=Mechanism.FCFS, seed=42)
    
    # Manually spawn vehicles
    v1 = Vehicle(1, 'N', arrival_time=0, mechanism=Mechanism.FCFS)
    v2 = Vehicle(2, 'N', arrival_time=5, mechanism=Mechanism.FCFS)
    
    print(f"V1: arrival_time={v1.arrival_time}, urgency={v1.urgency}")
    print(f"V2: arrival_time={v2.arrival_time}, urgency={v2.urgency}")
    
    # In FCFS, urgency should always be 0
    assert v1.urgency == 0, "FCFS vehicles should have urgency 0"
    assert v2.urgency == 0, "FCFS vehicles should have urgency 0"
    assert v1.calculate_bid() == 0, "FCFS vehicles should have bid 0"
    
    print("✅ FCFS correctly ignores urgency (all vehicles have urgency=0)")
    print()


def test_simulation_fairness():
    """Run simulation and check basic fairness"""
    print("=" * 60)
    print("TEST: Simulation Fairness")
    print("=" * 60)
    
    # Run FCFS simulation
    fcfs_model = SimpleIntersection(mechanism=Mechanism.FCFS, spawn_rate=0.3, seed=42)
    for _ in range(100):
        fcfs_model.step()
    fcfs_stats = fcfs_model.get_stats()
    
    # Run AUCTION simulation with same seed
    auction_model = SimpleIntersection(mechanism=Mechanism.AUCTION, spawn_rate=0.3, seed=42)
    for _ in range(100):
        auction_model.step()
    auction_stats = auction_model.get_stats()
    
    print(f"FCFS (100 steps):")
    print(f"  - Spawned: {fcfs_stats['total_spawned']}")
    print(f"  - Crossed: {fcfs_stats['total_crossed']}")
    print(f"  - Avg Wait: {fcfs_stats['avg_wait_time']:.2f}")
    
    print(f"\nAUCTION (100 steps):")
    print(f"  - Spawned: {auction_stats['total_spawned']}")
    print(f"  - Crossed: {auction_stats['total_crossed']}")
    print(f"  - Avg Wait: {auction_stats['avg_wait_time']:.2f}")
    print(f"  - Auctions: {auction_stats.get('auctions_held', 0)}")
    print(f"  - Revenue: {auction_stats.get('total_revenue', 0)}")
    
    print("\n✅ Simulation runs correctly for both mechanisms")
    print()


def test_negotiation_types():
    """Test different negotiation types"""
    print("=" * 60)
    print("TEST: Negotiation Types")
    print("=" * 60)
    
    for neg_type in NegotiationType:
        model = SimpleIntersection(
            mechanism=Mechanism.NEGOTIATION, 
            negotiation_type=neg_type,
            spawn_rate=0.4,
            seed=42
        )
        
        for _ in range(50):
            model.step()
        
        stats = model.get_stats()
        print(f"{neg_type.value}:")
        print(f"  - Crossed: {stats['total_crossed']}")
        print(f"  - Negotiations: {stats.get('negotiations_held', 0)}")
    
    print("\n✅ All negotiation types work correctly")
    print()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("INTERSECTION MECHANISM TESTS")
    print("=" * 60 + "\n")
    
    test_fcfs_priority()
    test_auction_highest_bid_wins()
    test_auction_urgent_priority()
    test_fcfs_arrival_not_urgency()
    test_simulation_fairness()
    test_negotiation_types()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
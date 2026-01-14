"""
Comparaison: English Auction vs Vickrey Auction
================================================

Ce script compare les deux types d'enchères:
- English: Prix ascendant, multi-rounds
- Vickrey: Enchère scellée, 2nd price
"""
import sys
sys.path.insert(0, '.')

from intersection import SimpleIntersection
from constants import Mechanism
from mechanisms import AuctionType, create_mechanism

def run_comparison(steps=200, spawn_rate=0.25, seed=42):
    """Compare English et Vickrey sur les mêmes conditions."""
    
    results = {}
    
    for auction_type in [AuctionType.ENGLISH, AuctionType.VICKREY]:
        print(f"\n{'='*50}")
        print(f"Running: {auction_type.value.upper()} AUCTION")
        print('='*50)
        
        # Créer le mécanisme
        mechanism = create_mechanism(Mechanism.AUCTION, auction_type=auction_type)
        
        # Créer la simulation
        model = SimpleIntersection(
            mechanism=Mechanism.AUCTION,
            spawn_rate=spawn_rate,
            urgent_probability=0.15,
            seed=seed
        )
        # Remplacer le mécanisme par celui avec le bon type
        model.mechanism = mechanism
        
        # Exécuter
        for _ in range(steps):
            model.step()
        
        stats = model.get_stats()
        auction_stats = mechanism.stats
        
        results[auction_type.value] = {
            'total_crossed': stats['total_crossed'],
            'avg_wait_time': stats['avg_wait_time'],
            'urgent_crossed': stats.get('urgent_crossed', 0),
            'auctions_held': auction_stats['auctions_held'],
            'total_revenue': auction_stats['total_revenue'],
            'avg_price': auction_stats['avg_price'],
            'total_rounds': auction_stats['total_rounds'],
            'avg_rounds': auction_stats['total_rounds'] / max(1, auction_stats['auctions_held']),
        }
        
        print(f"\nRésultats {auction_type.value}:")
        for k, v in results[auction_type.value].items():
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")
    
    # Comparaison
    print("\n" + "="*60)
    print("COMPARAISON ENGLISH vs VICKREY")
    print("="*60)
    
    eng = results['english']
    vic = results['vickrey']
    
    print(f"""
┌─────────────────────┬──────────────┬──────────────┐
│ Métrique            │   ENGLISH    │   VICKREY    │
├─────────────────────┼──────────────┼──────────────┤
│ Véhicules sortis    │ {eng['total_crossed']:12} │ {vic['total_crossed']:12} │
│ Temps attente moyen │ {eng['avg_wait_time']:12.1f} │ {vic['avg_wait_time']:12.1f} │
│ Urgents sortis      │ {eng['urgent_crossed']:12} │ {vic['urgent_crossed']:12} │
│ Enchères tenues     │ {eng['auctions_held']:12} │ {vic['auctions_held']:12} │
│ Revenue total       │ {eng['total_revenue']:12} │ {vic['total_revenue']:12} │
│ Prix moyen          │ {eng['avg_price']:12.1f} │ {vic['avg_price']:12.1f} │
│ Rounds moyens       │ {eng['avg_rounds']:12.1f} │ {vic['avg_rounds']:12.1f} │
└─────────────────────┴──────────────┴──────────────┘
""")
    
    # Analyse
    print("ANALYSE:")
    print("-" * 40)
    
    if eng['avg_wait_time'] < vic['avg_wait_time']:
        print(f"✓ English a un temps d'attente plus bas (-{vic['avg_wait_time']-eng['avg_wait_time']:.1f})")
    else:
        print(f"✓ Vickrey a un temps d'attente plus bas (-{eng['avg_wait_time']-vic['avg_wait_time']:.1f})")
    
    print(f"✓ English utilise {eng['avg_rounds']:.1f} rounds en moyenne (vs 1 pour Vickrey)")
    
    if eng['total_revenue'] > vic['total_revenue']:
        print(f"✓ English génère plus de revenus (+{eng['total_revenue']-vic['total_revenue']})")
    else:
        print(f"✓ Vickrey génère plus de revenus (+{vic['total_revenue']-eng['total_revenue']})")
    
    print("\nPropriétés théoriques:")
    print("  - Vickrey: Truthful (stratégie dominante = vraie valeur)")
    print("  - English: Information révélée publiquement pendant l'enchère")
    
    return results


if __name__ == '__main__':
    results = run_comparison(steps=200)
"""
Auction Mechanisms: English vs Vickrey
======================================

Deux types d'enchères implémentés:

1. ENGLISH AUCTION (Enchère Anglaise)
   - Prix ascendant, enchères publiques
   - Plusieurs rounds jusqu'à ce qu'un seul reste
   - Le gagnant paie son propre bid

2. VICKREY AUCTION (Second-Price Sealed-Bid)
   - Enchère scellée (un seul round)
   - Le gagnant paie le 2ème prix le plus élevé
   - Stratégie dominante = révéler vraie valeur (truthful)
"""
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class AuctionType(Enum):
    ENGLISH = "english"
    VICKREY = "vickrey"


@dataclass
class AuctionRound:
    """Un round d'enchère"""
    round_num: int
    bids: Dict[int, int]  # vehicle_id -> bid
    active_bidders: List[int]
    current_price: int
    eliminated: List[int] = field(default_factory=list)


@dataclass
class AuctionResult:
    """Résultat complet d'une enchère"""
    auction_type: AuctionType
    winner_id: int
    winning_bid: int
    price_paid: int
    rounds: List[AuctionRound]
    total_rounds: int
    all_bids: Dict[int, int]


class AuctionMechanism(BaseMechanism):
    """
    Mécanisme d'enchères avec support English et Vickrey.
    
    Par défaut: Vickrey (plus efficace pour simulation)
    Peut être changé via set_auction_type()
    """
    
    def __init__(self, auction_type: AuctionType = AuctionType.VICKREY):
        super().__init__()
        self.auction_type = auction_type
        self.name = f"Auction ({auction_type.value.title()})"
        
        self.stats.update({
            'auctions_held': 0,
            'total_revenue': 0,
            'avg_price': 0,
            'total_rounds': 0,
            'english_auctions': 0,
            'vickrey_auctions': 0,
        })
        
        self.last_auction: Optional[AuctionResult] = None
        self.auction_history: List[AuctionResult] = []
    
    def set_auction_type(self, auction_type: AuctionType):
        """Change le type d'enchère"""
        self.auction_type = auction_type
        self.name = f"Auction ({auction_type.value.title()})"
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Sélection à la barrière par enchère.
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            winner = candidates[0]
            return SelectionResult(
                winner=winner,
                details={
                    'method': 'single_candidate',
                    'winning_bid': winner.calculate_bid(),
                    'price_paid': 0
                }
            )
        
        # Exécuter l'enchère selon le type
        if self.auction_type == AuctionType.ENGLISH:
            result = self._run_english_auction(candidates)
        else:
            result = self._run_vickrey_auction(candidates)
        
        # Trouver le véhicule gagnant
        winner = next(v for v in candidates if v.id == result.winner_id)
        
        # Mettre à jour les stats
        self._update_stats(result)
        
        # Sauvegarder le résultat
        self.last_auction = result
        self.auction_history.append(result)
        
        return SelectionResult(
            winner=winner,
            details={
                'method': f'{result.auction_type.value}_auction',
                'winning_bid': result.winning_bid,
                'price_paid': result.price_paid,
                'total_rounds': result.total_rounds,
                'all_bids': result.all_bids,
                'rounds': [
                    {
                        'round': r.round_num,
                        'current_price': r.current_price,
                        'active': r.active_bidders,
                        'eliminated': r.eliminated
                    }
                    for r in result.rounds
                ]
            }
        )
    
    def _run_english_auction(self, candidates: List['Vehicle']) -> AuctionResult:
        """
        Enchère Anglaise (English Auction)
        
        Protocol:
        1. Prix de départ = 0
        2. Chaque round: incrément de 10
        3. Véhicules se retirent si prix > leur bid
        4. Continue jusqu'à 1 seul restant
        5. Gagnant paie le prix final
        """
        # Collecter les bids initiaux (valeurs privées)
        all_bids = {v.id: v.calculate_bid() for v in candidates}
        active_bidders = list(all_bids.keys())
        
        rounds = []
        current_price = 0
        increment = 10
        round_num = 0
        
        while len(active_bidders) > 1:
            round_num += 1
            current_price += increment
            
            # Déterminer qui reste
            eliminated = []
            new_active = []
            
            for vid in active_bidders:
                if all_bids[vid] >= current_price:
                    new_active.append(vid)
                else:
                    eliminated.append(vid)
            
            # Enregistrer le round
            round_bids = {vid: min(all_bids[vid], current_price) for vid in active_bidders}
            rounds.append(AuctionRound(
                round_num=round_num,
                bids=round_bids,
                active_bidders=new_active.copy(),
                current_price=current_price,
                eliminated=eliminated
            ))
            
            active_bidders = new_active
            
            # Sécurité: max 100 rounds
            if round_num >= 100:
                break
        
        # Le gagnant est le dernier restant
        winner_id = active_bidders[0] if active_bidders else max(all_bids, key=all_bids.get)
        winning_bid = all_bids[winner_id]
        
        # English: le gagnant paie le prix final (son propre bid effectif)
        price_paid = current_price
        
        return AuctionResult(
            auction_type=AuctionType.ENGLISH,
            winner_id=winner_id,
            winning_bid=winning_bid,
            price_paid=price_paid,
            rounds=rounds,
            total_rounds=round_num,
            all_bids=all_bids
        )
    
    def _run_vickrey_auction(self, candidates: List['Vehicle']) -> AuctionResult:
        """
        Enchère de Vickrey (Second-Price Sealed-Bid)
        
        Protocol:
        1. Chaque véhicule soumet son bid (scellé)
        2. Plus haute enchère gagne
        3. Gagnant paie la 2ème plus haute enchère
        
        Propriété: Truthful (révéler vraie valeur = optimal)
        """
        # Collecter tous les bids
        all_bids = {v.id: v.calculate_bid() for v in candidates}
        
        # Trier par bid décroissant
        sorted_bids = sorted(all_bids.items(), key=lambda x: x[1], reverse=True)
        
        # Gagnant = plus haute enchère
        winner_id, winning_bid = sorted_bids[0]
        
        # Prix = 2ème plus haute enchère
        if len(sorted_bids) > 1:
            price_paid = sorted_bids[1][1]
        else:
            price_paid = 0
        
        # Un seul round pour Vickrey
        round_data = AuctionRound(
            round_num=1,
            bids=all_bids,
            active_bidders=list(all_bids.keys()),
            current_price=winning_bid,
            eliminated=[]
        )
        
        return AuctionResult(
            auction_type=AuctionType.VICKREY,
            winner_id=winner_id,
            winning_bid=winning_bid,
            price_paid=price_paid,
            rounds=[round_data],
            total_rounds=1,
            all_bids=all_bids
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Résolution de conflit à la zone d'attente par enchère.
        """
        if not waiting:
            return None
        
        if len(waiting) == 1:
            return SelectionResult(
                winner=waiting[0],
                details={'method': 'single_vehicle'}
            )
        
        # Utiliser le même mécanisme d'enchère
        return self.select(waiting, None, context)
    
    def _update_stats(self, result: AuctionResult):
        """Met à jour les statistiques"""
        self.stats['auctions_held'] += 1
        self.stats['total_revenue'] += result.price_paid
        self.stats['total_rounds'] += result.total_rounds
        
        if result.auction_type == AuctionType.ENGLISH:
            self.stats['english_auctions'] += 1
        else:
            self.stats['vickrey_auctions'] += 1
        
        if self.stats['auctions_held'] > 0:
            self.stats['avg_price'] = self.stats['total_revenue'] / self.stats['auctions_held']
    
    def get_last_auction(self) -> Optional[Dict]:
        """Retourne le dernier résultat d'enchère"""
        if not self.last_auction:
            return None
        
        return {
            'type': self.last_auction.auction_type.value,
            'winner_id': self.last_auction.winner_id,
            'winning_bid': self.last_auction.winning_bid,
            'price_paid': self.last_auction.price_paid,
            'total_rounds': self.last_auction.total_rounds,
            'all_bids': self.last_auction.all_bids,
        }
    
    def reset(self):
        """Reset le mécanisme"""
        super().reset()
        self.stats.update({
            'auctions_held': 0,
            'total_revenue': 0,
            'avg_price': 0,
            'total_rounds': 0,
            'english_auctions': 0,
            'vickrey_auctions': 0,
        })
        self.last_auction = None
        self.auction_history.clear()
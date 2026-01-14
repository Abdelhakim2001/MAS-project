"""
Multi-Round Negotiation Mechanism
=================================

Négociation réaliste entre véhicules avec communication visible:

Protocol Multi-Rounds:
  Round 1: ANNOUNCE - Chaque véhicule annonce son intention
  Round 2: PROPOSE  - Échange des scores de priorité  
  Round 3: COUNTER  - Contre-propositions si scores proches
  Round 4: DECIDE   - Décision finale (YIELD ou INSIST)

Critères équilibrés:
  - Urgency (40%): Niveau d'urgence du véhicule
  - Fairness (35%): Temps d'attente (équité)
  - Fuel (15%): Niveau de carburant
  - Tiebreaker (10%): Facteur aléatoire
"""
import random
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from mechanisms.base import BaseMechanism, SelectionResult

if TYPE_CHECKING:
    from vehicle import Vehicle
    from constants import CorridorAxis


class MessageType(Enum):
    """Types de messages dans le protocole de négociation"""
    ANNOUNCE = "announce"     # Round 1: Annonce d'intention
    PROPOSE = "propose"       # Round 2: Proposition de priorité
    COUNTER = "counter"       # Round 3: Contre-proposition
    YIELD = "yield"           # Round 4: Céder le passage
    INSIST = "insist"         # Round 4: Insister sur la priorité
    ACCEPT = "accept"         # Finalisation


@dataclass
class Message:
    """Message échangé entre véhicules"""
    round: int
    sender_id: int
    receiver_id: int
    msg_type: MessageType
    content: Dict[str, Any]
    timestamp: int = 0


@dataclass
class NegotiationRound:
    """Un round de négociation"""
    round_num: int
    messages: List[Message]
    scores: Dict[int, float]  # vehicle_id -> score
    description: str


@dataclass
class NegotiationResult:
    """Résultat complet d'une négociation"""
    winner_id: int
    loser_id: int
    winner_score: float
    loser_score: float
    total_rounds: int
    total_messages: int
    rounds: List[NegotiationRound]
    winner_components: Dict[str, Any]
    loser_components: Dict[str, Any]


class NegotiationMechanism(BaseMechanism):
    """
    Mécanisme de négociation multi-rounds avec communication visible.
    
    Équilibre entre URGENCE et ÉQUITÉ (fairness):
    - Urgence: véhicules prioritaires (ambulances) passent plus vite
    - Équité: véhicules qui attendent longtemps gagnent en priorité
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Negotiation"
        
        self.stats.update({
            'negotiations_held': 0,
            'total_rounds': 0,
            'total_messages': 0,
            'avg_rounds': 0,
            'yields': 0,
            'insists': 0,
            'close_negotiations': 0,  # Scores proches (<10%)
        })
        
        self.last_negotiation: Optional[NegotiationResult] = None
        self.negotiation_history: List[NegotiationResult] = []
    
    def select(self, candidates: List['Vehicle'], axis: 'CorridorAxis', 
               context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Sélection à la barrière par négociation.
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return SelectionResult(
                winner=candidates[0],
                details={'method': 'single_candidate'}
            )
        
        context = context or {}
        current_step = context.get('current_step', 0)
        
        # Prendre les 2 meilleurs candidats par bid
        sorted_candidates = sorted(
            candidates, 
            key=lambda v: v.calculate_bid(), 
            reverse=True
        )
        v1, v2 = sorted_candidates[0], sorted_candidates[1]
        
        # Exécuter la négociation multi-rounds
        result = self._run_negotiation(v1, v2, current_step)
        
        # Trouver le gagnant
        winner = v1 if result.winner_id == v1.id else v2
        
        # Mettre à jour les stats
        self._update_stats(result)
        
        # Sauvegarder
        self.last_negotiation = result
        self.negotiation_history.append(result)
        
        return SelectionResult(
            winner=winner,
            details=self._result_to_dict(result)
        )
    
    def select_at_conflict(self, waiting: List['Vehicle'], 
                           context: Dict[str, Any] = None) -> Optional[SelectionResult]:
        """
        Négociation à la zone d'attente (conflit).
        """
        if not waiting:
            return None
        
        if len(waiting) == 1:
            return SelectionResult(
                winner=waiting[0],
                details={'method': 'single_vehicle'}
            )
        
        context = context or {}
        current_step = context.get('current_step', 0)
        
        v1, v2 = waiting[0], waiting[1]
        
        # Exécuter la négociation
        result = self._run_negotiation(v1, v2, current_step)
        
        winner = v1 if result.winner_id == v1.id else v2
        
        self._update_stats(result)
        self.last_negotiation = result
        self.negotiation_history.append(result)
        
        return SelectionResult(
            winner=winner,
            details=self._result_to_dict(result)
        )
    
    def _run_negotiation(self, v1: 'Vehicle', v2: 'Vehicle', 
                         current_step: int) -> NegotiationResult:
        """
        Exécute une négociation complète multi-rounds.
        
        Rounds:
        1. ANNOUNCE: Les véhicules annoncent leur intention de passer
        2. PROPOSE: Échange des scores de priorité
        3. COUNTER: Si scores proches (<10%), contre-propositions
        4. DECIDE: YIELD (céder) ou INSIST (insister)
        """
        all_rounds = []
        all_messages = []
        
        # Calculer les scores initiaux
        score1, comp1 = self._calculate_priority_score(v1, current_step)
        score2, comp2 = self._calculate_priority_score(v2, current_step)
        
        # =============== ROUND 1: ANNOUNCE ===============
        msg1 = Message(
            round=1, sender_id=v1.id, receiver_id=v2.id,
            msg_type=MessageType.ANNOUNCE,
            content={
                'intention': 'request_passage',
                'direction': v1.direction,
                'urgency': v1.urgency,
            },
            timestamp=current_step
        )
        msg2 = Message(
            round=1, sender_id=v2.id, receiver_id=v1.id,
            msg_type=MessageType.ANNOUNCE,
            content={
                'intention': 'request_passage',
                'direction': v2.direction,
                'urgency': v2.urgency,
            },
            timestamp=current_step
        )
        all_messages.extend([msg1, msg2])
        
        round1 = NegotiationRound(
            round_num=1,
            messages=[msg1, msg2],
            scores={v1.id: score1, v2.id: score2},
            description=f"V{v1.id} et V{v2.id} annoncent leur intention de passer"
        )
        all_rounds.append(round1)
        
        # =============== ROUND 2: PROPOSE ===============
        msg3 = Message(
            round=2, sender_id=v1.id, receiver_id=v2.id,
            msg_type=MessageType.PROPOSE,
            content={
                'priority_score': score1,
                'urgency_factor': comp1['urgency_score'],
                'fairness_factor': comp1['wait_score'],
                'fuel_factor': comp1['fuel_score'],
            },
            timestamp=current_step
        )
        msg4 = Message(
            round=2, sender_id=v2.id, receiver_id=v1.id,
            msg_type=MessageType.PROPOSE,
            content={
                'priority_score': score2,
                'urgency_factor': comp2['urgency_score'],
                'fairness_factor': comp2['wait_score'],
                'fuel_factor': comp2['fuel_score'],
            },
            timestamp=current_step
        )
        all_messages.extend([msg3, msg4])
        
        round2 = NegotiationRound(
            round_num=2,
            messages=[msg3, msg4],
            scores={v1.id: score1, v2.id: score2},
            description=f"V{v1.id} propose {score1:.1f}, V{v2.id} propose {score2:.1f}"
        )
        all_rounds.append(round2)
        
        # =============== ROUND 3: COUNTER (si scores proches) ===============
        diff_percent = abs(score1 - score2) / max(score1, score2, 1) * 100
        
        if diff_percent < 10:
            # Scores proches - contre-propositions
            self.stats['close_negotiations'] += 1
            
            # V1 contre-propose avec bonus équité
            wait1 = current_step - v1.arrival_time
            adjusted_score1 = score1 + (wait1 * 0.3)
            
            wait2 = current_step - v2.arrival_time
            adjusted_score2 = score2 + (wait2 * 0.3)
            
            msg5 = Message(
                round=3, sender_id=v1.id, receiver_id=v2.id,
                msg_type=MessageType.COUNTER,
                content={
                    'adjusted_score': adjusted_score1,
                    'wait_time_bonus': wait1 * 0.3,
                    'argument': 'fairness_bonus',
                },
                timestamp=current_step
            )
            msg6 = Message(
                round=3, sender_id=v2.id, receiver_id=v1.id,
                msg_type=MessageType.COUNTER,
                content={
                    'adjusted_score': adjusted_score2,
                    'wait_time_bonus': wait2 * 0.3,
                    'argument': 'fairness_bonus',
                },
                timestamp=current_step
            )
            all_messages.extend([msg5, msg6])
            
            round3 = NegotiationRound(
                round_num=3,
                messages=[msg5, msg6],
                scores={v1.id: adjusted_score1, v2.id: adjusted_score2},
                description=f"Scores proches! V{v1.id}→{adjusted_score1:.1f}, V{v2.id}→{adjusted_score2:.1f}"
            )
            all_rounds.append(round3)
            
            # Utiliser les scores ajustés
            score1, score2 = adjusted_score1, adjusted_score2
        
        # =============== ROUND 4: DECIDE ===============
        if score1 >= score2:
            winner_id, loser_id = v1.id, v2.id
            winner_score, loser_score = score1, score2
            winner_comp, loser_comp = comp1, comp2
            
            # Le perdant cède (YIELD)
            msg_yield = Message(
                round=4, sender_id=v2.id, receiver_id=v1.id,
                msg_type=MessageType.YIELD,
                content={
                    'decision': 'yield_passage',
                    'my_score': score2,
                    'winner_score': score1,
                    'reason': 'lower_priority'
                },
                timestamp=current_step
            )
            self.stats['yields'] += 1
            
            # Le gagnant accepte
            msg_accept = Message(
                round=4, sender_id=v1.id, receiver_id=v2.id,
                msg_type=MessageType.ACCEPT,
                content={
                    'decision': 'proceed',
                    'final_score': score1
                },
                timestamp=current_step
            )
        else:
            winner_id, loser_id = v2.id, v1.id
            winner_score, loser_score = score2, score1
            winner_comp, loser_comp = comp2, comp1
            
            msg_yield = Message(
                round=4, sender_id=v1.id, receiver_id=v2.id,
                msg_type=MessageType.YIELD,
                content={
                    'decision': 'yield_passage',
                    'my_score': score1,
                    'winner_score': score2,
                    'reason': 'lower_priority'
                },
                timestamp=current_step
            )
            self.stats['yields'] += 1
            
            msg_accept = Message(
                round=4, sender_id=v2.id, receiver_id=v1.id,
                msg_type=MessageType.ACCEPT,
                content={
                    'decision': 'proceed',
                    'final_score': score2
                },
                timestamp=current_step
            )
        
        all_messages.extend([msg_yield, msg_accept])
        
        round4 = NegotiationRound(
            round_num=4,
            messages=[msg_yield, msg_accept],
            scores={v1.id: score1, v2.id: score2},
            description=f"V{loser_id} YIELD → V{winner_id} PROCEED"
        )
        all_rounds.append(round4)
        
        return NegotiationResult(
            winner_id=winner_id,
            loser_id=loser_id,
            winner_score=winner_score,
            loser_score=loser_score,
            total_rounds=len(all_rounds),
            total_messages=len(all_messages),
            rounds=all_rounds,
            winner_components=winner_comp,
            loser_components=loser_comp
        )
    
    def _calculate_priority_score(self, v: 'Vehicle', current_step: int) -> tuple:
        """
        Calcule le score de priorité équilibrant URGENCE et ÉQUITÉ.
        
        Formule:
        Score = 40% × Urgency + 35% × Fairness + 15% × Fuel + 10% × Random
        
        - Urgency: niveau d'urgence (0-10)
        - Fairness: temps d'attente (plus on attend, plus on a priorité)
        - Fuel: urgence carburant (moins de fuel = plus prioritaire)
        """
        # Urgency score (40%)
        urgency_normalized = v.urgency / 10.0
        urgency_score = urgency_normalized * 40
        
        # Fairness score (35%) - basé sur temps d'attente
        wait_time = current_step - v.arrival_time
        wait_normalized = min(wait_time / 50.0, 1.0)
        wait_score = wait_normalized * 35
        
        # Fuel score (15%) - moins de fuel = plus prioritaire
        fuel_urgency = 1.0 - (v.fuel_level / 100.0)
        fuel_score = fuel_urgency * 15
        
        # Random tiebreaker (10%)
        random_score = random.random() * 10
        
        total_score = urgency_score + wait_score + fuel_score + random_score
        
        components = {
            'urgency': v.urgency,
            'urgency_score': round(urgency_score, 1),
            'wait_time': wait_time,
            'wait_score': round(wait_score, 1),
            'fuel_level': v.fuel_level,
            'fuel_score': round(fuel_score, 1),
            'random_score': round(random_score, 1),
        }
        
        return round(total_score, 1), components
    
    def _update_stats(self, result: NegotiationResult):
        """Met à jour les statistiques"""
        self.stats['negotiations_held'] += 1
        self.stats['total_rounds'] += result.total_rounds
        self.stats['total_messages'] += result.total_messages
        
        if self.stats['negotiations_held'] > 0:
            self.stats['avg_rounds'] = round(
                self.stats['total_rounds'] / self.stats['negotiations_held'], 1
            )
    
    def _result_to_dict(self, result: NegotiationResult) -> Dict:
        """Convertit le résultat en dictionnaire"""
        return {
            'method': 'Marginal Utility',
            'winner_id': result.winner_id,
            'loser_id': result.loser_id,
            'winner_score': result.winner_score,
            'loser_score': result.loser_score,
            'total_rounds': result.total_rounds,
            'total_messages': result.total_messages,
            'winner_components': result.winner_components,
            'loser_components': result.loser_components,
            'rounds_detail': [
                {
                    'round': r.round_num,
                    'description': r.description,
                    'messages': len(r.messages),
                }
                for r in result.rounds
            ]
        }
    
    def get_last_negotiation(self) -> Optional[Dict]:
        """Retourne le dernier résultat de négociation"""
        if not self.last_negotiation:
            return None
        return self._result_to_dict(self.last_negotiation)
    
    def get_negotiation_stats(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats.copy()
    
    def reset(self):
        """Reset le mécanisme"""
        super().reset()
        self.stats.update({
            'negotiations_held': 0,
            'total_rounds': 0,
            'total_messages': 0,
            'avg_rounds': 0,
            'yields': 0,
            'insists': 0,
            'close_negotiations': 0,
        })
        self.last_negotiation = None
        self.negotiation_history.clear()
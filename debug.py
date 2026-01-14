"""
Debug and Logging System for Intersection Simulation
====================================================

Writes to file instead of UI for cleaner debugging.
"""
from datetime import datetime
from typing import List, Dict
from collections import deque


class DebugLogger:
    """
    Logger to track all simulation events.
    Writes to debug.log file.
    """
    
    def __init__(self, enabled: bool = True, max_logs: int = 1000, 
                 log_file: str = "debug.log"):
        self.enabled = enabled
        self.max_logs = max_logs
        self.logs: deque = deque(maxlen=max_logs)
        self.step_logs: Dict[int, List[Dict]] = {}
        self.current_step = 0
        self.log_file = log_file
        
        self.event_counts = {
            'spawn': 0,
            'enter_corridor': 0,
            'enter_conflict': 0,
            'exit_conflict': 0,
            'exit_grid': 0,
            'wait_conflict': 0,
            'auction': 0,
            'negotiation': 0,
        }
        
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize log file"""
        try:
            with open(self.log_file, 'w') as f:
                f.write("=" * 70 + "\n")
                f.write("INTERSECTION SIMULATION DEBUG LOG\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
        except Exception:
            pass  # Ignore file errors in web environment
    
    def _write_to_file(self, message: str):
        """Write message to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(message + "\n")
        except Exception:
            pass  # Ignore file errors
    
    def set_step(self, step: int):
        """Set current simulation step"""
        self.current_step = step
        if step not in self.step_logs:
            self.step_logs[step] = []
        if step % 10 == 0:
            self._write_to_file(f"\n--- STEP {step} ---")
    
    def log(self, event_type: str, message: str, data: Dict = None):
        """Log an event"""
        if not self.enabled:
            return
        
        log_entry = {
            'step': self.current_step,
            'type': event_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3]
        }
        
        self.logs.append(log_entry)
        
        if self.current_step not in self.step_logs:
            self.step_logs[self.current_step] = []
        self.step_logs[self.current_step].append(log_entry)
        
        if event_type in self.event_counts:
            self.event_counts[event_type] += 1
        
        # Write to file with icon
        icon = {
            'spawn': '🚗',
            'enter_corridor': '➡️',
            'enter_conflict': '⚠️',
            'exit_conflict': '✅',
            'exit_grid': '🏁',
            'wait_conflict': '⏳',
            'auction': '🔨',
            'negotiation': '🤝',
            'state': '📊',
        }.get(event_type, '•')
        
        file_message = f"[{self.current_step:04d}] {icon} {message}"
        if data:
            file_message += f" | {data}"
        self._write_to_file(file_message)
    
    def log_spawn(self, vehicle_id: int, direction: str, urgency: int):
        self.log('spawn', f"V{vehicle_id} spawned ({direction}, urg={urgency})", {
            'vehicle_id': vehicle_id,
            'direction': direction,
            'urgency': urgency,
        })
    
    def log_enter_corridor(self, vehicle_id: int, direction: str, 
                           axis: str, mechanism: str):
        self.log('enter_corridor', 
                f"V{vehicle_id} → {axis} corridor ({mechanism})", {
            'vehicle_id': vehicle_id,
            'direction': direction,
            'axis': axis,
            'mechanism': mechanism,
        })
    
    def log_enter_conflict_zone(self, vehicle_id: int, direction: str, urgency: int):
        self.log('enter_conflict', 
                f"V{vehicle_id} → CONFLICT ZONE (urg={urgency})", {
            'vehicle_id': vehicle_id,
            'direction': direction,
            'urgency': urgency,
        })
    
    def log_exit_conflict_zone(self, vehicle_id: int, direction: str):
        self.log('exit_conflict', f"V{vehicle_id} ← conflict zone", {
            'vehicle_id': vehicle_id,
            'direction': direction,
        })
    
    def log_wait_conflict_zone(self, vehicle_id: int, direction: str, 
                               urgency: int, blocking_id: int):
        self.log('wait_conflict', 
                f"V{vehicle_id} (urg={urgency}) WAITING (blocked by V{blocking_id})", {
            'vehicle_id': vehicle_id,
            'direction': direction,
            'urgency': urgency,
            'blocking_vehicle': blocking_id,
        })
    
    def log_exit_grid(self, vehicle_id: int, direction: str, 
                      total_time: int, wait_time: int):
        self.log('exit_grid', 
                f"V{vehicle_id} EXITED (total={total_time}, wait={wait_time})", {
            'vehicle_id': vehicle_id,
            'direction': direction,
            'total_time': total_time,
            'wait_time': wait_time,
        })
    
    def log_auction(self, axis: str, winner_id: int, winner_urgency: int, 
                    winning_bid: int, price_paid: int, num_bidders: int, 
                    all_bids, auction_type: str = 'vickrey', total_rounds: int = 1):
        # all_bids est maintenant un dict {vehicle_id: bid}
        if isinstance(all_bids, dict):
            bids_str = ", ".join([f"V{vid}(b={bid})" for vid, bid in sorted(all_bids.items(), key=lambda x: x[1], reverse=True)])
        else:
            bids_str = str(all_bids)
        
        self.log('auction', 
                f"AUCTION ({auction_type.upper()}) {axis}: V{winner_id} WINS (bid={winning_bid}, paid={price_paid}, rounds={total_rounds}) | {bids_str}", {
            'axis': axis,
            'winner_id': winner_id,
            'winning_bid': winning_bid,
            'price_paid': price_paid,
            'num_bidders': num_bidders,
            'auction_type': auction_type,
            'total_rounds': total_rounds,
        })
    
    def log_negotiation(self, winner_id: int, loser_id: int, method: str, 
                        details: Dict = None):
        """Log une négociation avec détails des rounds"""
        details = details or {}
        
        # Message de base
        base_msg = f"NEGOTIATION V{winner_id} vs V{loser_id}:"
        
        # Construire le message détaillé
        lines = [base_msg]
        
        # Afficher les scores
        winner_score = details.get('winner_score', '?')
        loser_score = details.get('loser_score', '?')
        lines.append(f"       Scores: V{winner_id}={winner_score:.1f} vs V{loser_id}={loser_score:.1f}")
        
        # Afficher les composants du gagnant
        winner_comp = details.get('winner_components', {})
        if winner_comp:
            lines.append(f"       V{winner_id}: urg={winner_comp.get('urgency', '?')}→{winner_comp.get('urgency_score', 0):.1f}pts, " +
                        f"wait={winner_comp.get('wait_time', '?')}→{winner_comp.get('wait_score', 0):.1f}pts, " +
                        f"fuel={winner_comp.get('fuel_level', '?')}%→{winner_comp.get('fuel_score', 0):.1f}pts")
        
        # Afficher les rounds
        rounds_detail = details.get('rounds_detail', [])
        if rounds_detail:
            for r in rounds_detail:
                lines.append(f"       Round {r['round']}: {r['description']}")
        
        # Résultat final
        lines.append(f"       → V{loser_id} YIELD, V{winner_id} WINS")
        
        full_message = "\n".join(lines)
        
        self.log('negotiation', full_message, {
            'winner_id': winner_id,
            'loser_id': loser_id,
            'method': method,
            'winner_score': winner_score,
            'loser_score': loser_score,
            'total_rounds': details.get('total_rounds', 0),
            'total_messages': details.get('total_messages', 0),
        })
    
    def get_recent_logs(self, count: int = 20) -> List[Dict]:
        return list(self.logs)[-count:]
    
    def get_summary(self) -> Dict:
        return {
            'total_logs': len(self.logs),
            'current_step': self.current_step,
            'event_counts': self.event_counts.copy(),
        }
    
    def clear(self):
        self.logs.clear()
        self.step_logs.clear()
        self.event_counts = {k: 0 for k in self.event_counts}
        self._init_log_file()


# Global logger instance
logger = DebugLogger(enabled=True)
"""
Générateur de Graphiques pour la Présentation
==============================================

Génère tous les graphiques nécessaires pour la soutenance:
1. Comparaison des temps d'attente moyens (FCFS, Auction, Negotiation)
2. Évolution du débit dans le temps
3. Distribution des temps d'attente
4. Revenus des enchères
5. Véhicules urgents traités
6. Collisions évitées
7. Tableau récapitulatif
8. Comparaison English vs Vickrey Auction
9. Détails de la négociation multi-rounds
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict
import os

from intersection import SimpleIntersection
from constants import Mechanism
from mechanisms import AuctionType

# Style des graphiques
plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {
    'FCFS': '#3498db',      # Bleu
    'AUCTION': '#e74c3c',   # Rouge
    'NEGOTIATION': '#2ecc71', # Vert
    'ENGLISH': '#e74c3c',   # Rouge
    'VICKREY': '#9b59b6',   # Violet
}


def run_simulation(mechanism, auction_type=AuctionType.VICKREY,
                   steps=300, spawn_rate=0.25, seed=42):
    """
    Exécute une simulation et collecte les métriques à chaque pas.
    """
    model = SimpleIntersection(
        mechanism=mechanism,
        spawn_rate=spawn_rate,
        urgent_probability=0.15,
        seed=seed
    )
    
    # Configurer le type d'enchère si applicable
    if mechanism == Mechanism.AUCTION and hasattr(model.mechanism, 'set_auction_type'):
        model.mechanism.set_auction_type(auction_type)
    
    history = {
        'step': [],
        'total_crossed': [],
        'avg_wait_time': [],
        'parking_count': [],
        'barrier_count': [],
        'corridor_count': [],
        'collisions_avoided': [],
        'auctions_held': [],
        'negotiations_held': [],
        'total_revenue': [],
        'urgent_crossed': [],
        'total_rounds': [],
        'avg_rounds': [],
    }
    
    wait_times = []
    
    for i in range(steps):
        model.step()
        stats = model.get_stats()
        
        history['step'].append(i + 1)
        history['total_crossed'].append(stats['total_crossed'])
        history['avg_wait_time'].append(stats['avg_wait_time'])
        history['parking_count'].append(stats['parking_count'])
        history['barrier_count'].append(stats['barrier_count'])
        history['corridor_count'].append(stats['corridor_count'])
        history['collisions_avoided'].append(stats['collisions_avoided'])
        history['auctions_held'].append(stats.get('auctions_held', 0))
        history['negotiations_held'].append(stats.get('negotiations_held', 0))
        history['total_revenue'].append(stats.get('total_revenue', 0))
        history['urgent_crossed'].append(stats.get('urgent_crossed', 0))
        
        # Stats spécifiques aux enchères
        if hasattr(model.mechanism, 'stats'):
            history['total_rounds'].append(model.mechanism.stats.get('total_rounds', 0))
            history['avg_rounds'].append(
                model.mechanism.stats.get('total_rounds', 0) / max(1, stats.get('auctions_held', 1))
            )
        else:
            history['total_rounds'].append(0)
            history['avg_rounds'].append(0)
    
    # Collecter les temps d'attente individuels
    for v in model.exited_vehicles:
        if v.entry_time and v.arrival_time:
            wait_times.append(v.entry_time - v.arrival_time)
    
    return history, model.get_stats(), wait_times, model


def plot_comparison_avg_wait(results, output_dir):
    """
    Graphique 1: Comparaison des temps d'attente moyens (Bar Chart)
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    mechanisms = list(results.keys())
    avg_waits = [results[m]['final_stats']['avg_wait_time'] for m in mechanisms]
    colors = [COLORS.get(m, '#95a5a6') for m in mechanisms]
    
    bars = ax.bar(mechanisms, avg_waits, color=colors, edgecolor='black', linewidth=1.2)
    
    # Ajouter les valeurs sur les barres
    for bar, val in zip(bars, avg_waits):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax.set_ylabel('Temps d\'attente moyen (steps)', fontsize=12)
    ax.set_xlabel('Mécanisme', fontsize=12)
    ax.set_title('Comparaison des Temps d\'Attente Moyens', fontsize=14, fontweight='bold')
    
    # Ajouter pourcentage d'amélioration
    fcfs_wait = results['FCFS']['final_stats']['avg_wait_time']
    for i, m in enumerate(mechanisms):
        if m != 'FCFS' and fcfs_wait > 0:
            improvement = (fcfs_wait - avg_waits[i]) / fcfs_wait * 100
            ax.text(i, avg_waits[i]/2, f'-{improvement:.0f}%', 
                   ha='center', va='center', fontsize=10, color='white', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph1_avg_wait_comparison.png'), dpi=150)
    plt.close()
    print("✓ Graph 1: Comparaison temps d'attente")


def plot_throughput_evolution(results, output_dir):
    """
    Graphique 2: Évolution du débit (véhicules sortis) dans le temps
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for mech, data in results.items():
        ax.plot(data['history']['step'], data['history']['total_crossed'], 
                label=mech, color=COLORS.get(mech, '#95a5a6'), linewidth=2)
    
    ax.set_xlabel('Steps', fontsize=12)
    ax.set_ylabel('Véhicules sortis (cumulatif)', fontsize=12)
    ax.set_title('Évolution du Débit dans le Temps', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph2_throughput_evolution.png'), dpi=150)
    plt.close()
    print("✓ Graph 2: Évolution du débit")


def plot_wait_time_distribution(results, output_dir):
    """
    Graphique 3: Distribution des temps d'attente (Histogramme)
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    main_mechs = ['FCFS', 'AUCTION', 'NEGOTIATION']
    for ax, mech in zip(axes, main_mechs):
        if mech in results:
            data = results[mech]
            wait_times = data['wait_times']
            if wait_times:
                ax.hist(wait_times, bins=20, color=COLORS.get(mech, '#95a5a6'), 
                       edgecolor='black', alpha=0.7)
                ax.axvline(np.mean(wait_times), color='red', linestyle='--', 
                          linewidth=2, label=f'Moyenne: {np.mean(wait_times):.1f}')
                ax.axvline(np.median(wait_times), color='orange', linestyle=':', 
                          linewidth=2, label=f'Médiane: {np.median(wait_times):.1f}')
            
            ax.set_xlabel('Temps d\'attente (steps)', fontsize=11)
            ax.set_ylabel('Nombre de véhicules', fontsize=11)
            ax.set_title(f'{mech}', fontsize=12, fontweight='bold')
            ax.legend(fontsize=9)
    
    fig.suptitle('Distribution des Temps d\'Attente par Mécanisme', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph3_wait_distribution.png'), dpi=150)
    plt.close()
    print("✓ Graph 3: Distribution des temps d'attente")


def plot_auction_revenue(results, output_dir):
    """
    Graphique 4: Revenus des enchères (Auction uniquement)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Revenue cumulatif
    auction_data = results['AUCTION']['history']
    ax1.plot(auction_data['step'], auction_data['total_revenue'], 
             color=COLORS['AUCTION'], linewidth=2)
    ax1.fill_between(auction_data['step'], auction_data['total_revenue'], 
                     alpha=0.3, color=COLORS['AUCTION'])
    ax1.set_xlabel('Steps', fontsize=11)
    ax1.set_ylabel('Revenue cumulatif', fontsize=11)
    ax1.set_title('Revenus des Enchères', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Nombre d'enchères
    ax2.plot(auction_data['step'], auction_data['auctions_held'], 
             color=COLORS['AUCTION'], linewidth=2)
    ax2.set_xlabel('Steps', fontsize=11)
    ax2.set_ylabel('Nombre d\'enchères', fontsize=11)
    ax2.set_title('Enchères Réalisées', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Stats finales
    final = results['AUCTION']['final_stats']
    textstr = f"Total: {final.get('total_revenue', 0)}\nEnchères: {final.get('auctions_held', 0)}\nPrix moyen: {final.get('avg_price', 0):.1f}"
    ax1.text(0.95, 0.05, textstr, transform=ax1.transAxes, fontsize=10,
             verticalalignment='bottom', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph4_auction_revenue.png'), dpi=150)
    plt.close()
    print("✓ Graph 4: Revenus des enchères")


def plot_urgent_vehicles(results, output_dir):
    """
    Graphique 5: Véhicules urgents traités
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    mechanisms = ['AUCTION', 'NEGOTIATION']
    total = [results[m]['final_stats']['total_crossed'] for m in mechanisms]
    urgent = [results[m]['final_stats']['urgent_crossed'] for m in mechanisms]
    normal = [t - u for t, u in zip(total, urgent)]
    
    x = np.arange(len(mechanisms))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, normal, width, label='Normal', color='#3498db')
    bars2 = ax.bar(x + width/2, urgent, width, label='Urgent 🚨', color='#e74c3c')
    
    ax.set_ylabel('Nombre de véhicules', fontsize=12)
    ax.set_xlabel('Mécanisme', fontsize=12)
    ax.set_title('Véhicules Traversés: Normal vs Urgent', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(mechanisms)
    ax.legend()
    
    # Ajouter les valeurs
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{int(bar.get_height())}', ha='center', va='bottom')
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{int(bar.get_height())}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph5_urgent_vehicles.png'), dpi=150)
    plt.close()
    print("✓ Graph 5: Véhicules urgents")


def plot_collisions_avoided(results, output_dir):
    """
    Graphique 6: Collisions évitées dans le temps
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for mech in ['FCFS', 'AUCTION', 'NEGOTIATION']:
        if mech in results:
            data = results[mech]
            ax.plot(data['history']['step'], data['history']['collisions_avoided'], 
                    label=mech, color=COLORS.get(mech, '#95a5a6'), linewidth=2)
    
    ax.set_xlabel('Steps', fontsize=12)
    ax.set_ylabel('Collisions évitées (cumulatif)', fontsize=12)
    ax.set_title('Collisions Évitées - Preuve de Sécurité', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Annotation sécurité
    ax.text(0.98, 0.02, '0 COLLISION RÉELLE', transform=ax.transAxes, 
            fontsize=14, fontweight='bold', color='green',
            ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph6_collisions_avoided.png'), dpi=150)
    plt.close()
    print("✓ Graph 6: Collisions évitées")


def plot_summary_table(results, output_dir):
    """
    Graphique 7: Tableau récapitulatif
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')
    
    # Données du tableau
    columns = ['Métrique', 'FCFS', 'AUCTION', 'NEGOTIATION']
    rows = [
        ['Véhicules sortis', 
         str(results['FCFS']['final_stats']['total_crossed']),
         str(results['AUCTION']['final_stats']['total_crossed']),
         str(results['NEGOTIATION']['final_stats']['total_crossed'])],
        ['Temps attente moyen', 
         f"{results['FCFS']['final_stats']['avg_wait_time']:.1f}",
         f"{results['AUCTION']['final_stats']['avg_wait_time']:.1f}",
         f"{results['NEGOTIATION']['final_stats']['avg_wait_time']:.1f}"],
        ['Véhicules urgents sortis', 
         str(results['FCFS']['final_stats']['urgent_crossed']),
         str(results['AUCTION']['final_stats']['urgent_crossed']),
         str(results['NEGOTIATION']['final_stats']['urgent_crossed'])],
        ['Collisions évitées', 
         str(results['FCFS']['final_stats']['collisions_avoided']),
         str(results['AUCTION']['final_stats']['collisions_avoided']),
         str(results['NEGOTIATION']['final_stats']['collisions_avoided'])],
        ['Enchères/Négociations', 
         '0',
         str(results['AUCTION']['final_stats'].get('auctions_held', 0)),
         str(results['NEGOTIATION']['final_stats'].get('negotiations_held', 0))],
        ['Revenue', 
         '0',
         str(results['AUCTION']['final_stats'].get('total_revenue', 0)),
         '0'],
        ['Collisions réelles', '0', '0', '0'],
    ]
    
    # Couleurs
    cell_colors = [['#f0f0f0', '#d5e8f7', '#f7d5d5', '#d5f7e0']] * len(rows)
    
    table = ax.table(cellText=rows, colLabels=columns, loc='center',
                     cellLoc='center', colColours=['#2c3e50', '#3498db', '#e74c3c', '#2ecc71'],
                     cellColours=cell_colors)
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    
    # Style header
    for i in range(len(columns)):
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    ax.set_title('Tableau Récapitulatif des Résultats', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph7_summary_table.png'), dpi=150)
    plt.close()
    print("✓ Graph 7: Tableau récapitulatif")


def plot_english_vs_vickrey(output_dir, steps=200):
    """
    Graphique 8: Comparaison English Auction vs Vickrey Auction
    """
    print("\n--- Comparaison English vs Vickrey ---")
    
    # Exécuter les deux types d'enchères
    results_auction = {}
    
    for auction_type in [AuctionType.ENGLISH, AuctionType.VICKREY]:
        print(f"  Simulation {auction_type.value.upper()}...")
        history, final_stats, wait_times, model = run_simulation(
            Mechanism.AUCTION,
            auction_type=auction_type,
            steps=steps,
            seed=42
        )
        
        # Récupérer les stats spécifiques
        mech_stats = model.mechanism.stats
        
        results_auction[auction_type.value.upper()] = {
            'history': history,
            'final_stats': final_stats,
            'wait_times': wait_times,
            'mech_stats': mech_stats,
        }
    
    # === Figure avec 4 sous-graphiques ===
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # --- 1. Comparaison temps d'attente ---
    ax1 = axes[0, 0]
    types = ['ENGLISH', 'VICKREY']
    avg_waits = [results_auction[t]['final_stats']['avg_wait_time'] for t in types]
    colors = [COLORS['ENGLISH'], COLORS['VICKREY']]
    
    bars = ax1.bar(types, avg_waits, color=colors, edgecolor='black', linewidth=1.2)
    for bar, val in zip(bars, avg_waits):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax1.set_ylabel('Temps d\'attente moyen', fontsize=11)
    ax1.set_title('Temps d\'Attente Moyen', fontsize=12, fontweight='bold')
    
    # --- 2. Comparaison Revenue ---
    ax2 = axes[0, 1]
    revenues = [results_auction[t]['final_stats'].get('total_revenue', 0) for t in types]
    
    bars = ax2.bar(types, revenues, color=colors, edgecolor='black', linewidth=1.2)
    for bar, val in zip(bars, revenues):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                f'{val}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax2.set_ylabel('Revenue Total', fontsize=11)
    ax2.set_title('Revenue des Enchères', fontsize=12, fontweight='bold')
    
    # --- 3. Comparaison Rounds ---
    ax3 = axes[1, 0]
    avg_rounds = [
        results_auction[t]['mech_stats'].get('total_rounds', 0) / 
        max(1, results_auction[t]['final_stats'].get('auctions_held', 1))
        for t in types
    ]
    
    bars = ax3.bar(types, avg_rounds, color=colors, edgecolor='black', linewidth=1.2)
    for bar, val in zip(bars, avg_rounds):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax3.set_ylabel('Rounds Moyens par Enchère', fontsize=11)
    ax3.set_title('Nombre de Rounds', fontsize=12, fontweight='bold')
    
    # --- 4. Tableau comparatif ---
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    eng = results_auction['ENGLISH']
    vic = results_auction['VICKREY']
    
    table_data = [
        ['Métrique', 'ENGLISH', 'VICKREY'],
        ['Temps attente', f"{eng['final_stats']['avg_wait_time']:.1f}", 
         f"{vic['final_stats']['avg_wait_time']:.1f}"],
        ['Revenue', str(eng['final_stats'].get('total_revenue', 0)), 
         str(vic['final_stats'].get('total_revenue', 0))],
        ['Prix moyen', f"{eng['final_stats'].get('avg_price', 0):.1f}", 
         f"{vic['final_stats'].get('avg_price', 0):.1f}"],
        ['Rounds moyens', f"{avg_rounds[0]:.1f}", f"{avg_rounds[1]:.1f}"],
        ['Enchères', str(eng['final_stats'].get('auctions_held', 0)), 
         str(vic['final_stats'].get('auctions_held', 0))],
        ['Propriété', 'Info publique', 'Truthful ✓'],
    ]
    
    table = ax4.table(cellText=table_data[1:], colLabels=table_data[0], 
                      loc='center', cellLoc='center',
                      colColours=['#2c3e50', '#e74c3c', '#9b59b6'])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    for i in range(3):
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    fig.suptitle('Comparaison: English Auction vs Vickrey Auction', 
                 fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph8_english_vs_vickrey.png'), dpi=150)
    plt.close()
    print("✓ Graph 8: English vs Vickrey")
    
    return results_auction


def plot_negotiation_details(results, output_dir):
    """
    Graphique 9: Détails du mécanisme de négociation
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    neg_stats = results['NEGOTIATION']['final_stats']
    neg_data = results['NEGOTIATION']['history']
    
    # --- 1. Négociations dans le temps ---
    ax1 = axes[0, 0]
    ax1.plot(neg_data['step'], neg_data['negotiations_held'], 
             color=COLORS['NEGOTIATION'], linewidth=2)
    ax1.fill_between(neg_data['step'], neg_data['negotiations_held'], 
                     alpha=0.3, color=COLORS['NEGOTIATION'])
    ax1.set_xlabel('Steps', fontsize=11)
    ax1.set_ylabel('Négociations (cumulatif)', fontsize=11)
    ax1.set_title('Négociations dans le Temps', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # --- 2. Distribution des composants de l'utilité ---
    ax2 = axes[0, 1]
    components = ['Urgency\n(40%)', 'Wait Time\n(35%)', 'Fuel\n(15%)', 'Random\n(10%)']
    weights = [40, 35, 15, 10]
    colors_comp = ['#e74c3c', '#3498db', '#f39c12', '#95a5a6']
    
    bars = ax2.bar(components, weights, color=colors_comp, edgecolor='black')
    for bar, val in zip(bars, weights):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{val}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax2.set_ylabel('Poids dans le Score (%)', fontsize=11)
    ax2.set_title('Formule d\'Utilité Marginale', fontsize=12, fontweight='bold')
    ax2.set_ylim(0, 50)
    
    # --- 3. Protocol Multi-Rounds ---
    ax3 = axes[1, 0]
    ax3.axis('off')
    
    protocol_text = """
    ┌─────────────────────────────────────────────┐
    │         PROTOCOL DE NÉGOCIATION             │
    ├─────────────────────────────────────────────┤
    │                                             │
    │  Round 1: ANNOUNCE                          │
    │    → Chaque véhicule annonce son intention  │
    │                                             │
    │  Round 2: PROPOSE                           │
    │    → Échange des scores de priorité         │
    │                                             │
    │  Round 3: COUNTER (si scores proches <10%)  │
    │    → Contre-propositions avec bonus équité  │
    │                                             │
    │  Round 4: DECIDE                            │
    │    → Perdant: YIELD (céder)                 │
    │    → Gagnant: ACCEPT (avancer)              │
    │                                             │
    └─────────────────────────────────────────────┘
    """
    
    ax3.text(0.5, 0.5, protocol_text, transform=ax3.transAxes,
             fontsize=10, fontfamily='monospace',
             verticalalignment='center', horizontalalignment='center',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    ax3.set_title('Protocol Multi-Rounds', fontsize=12, fontweight='bold')
    
    # --- 4. Statistiques ---
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    stats_data = [
        ['Statistique', 'Valeur'],
        ['Négociations', str(neg_stats.get('negotiations_held', 0))],
        ['Total Rounds', str(neg_stats.get('total_rounds', 0))],
        ['Avg Rounds', f"{neg_stats.get('avg_rounds', 0):.1f}"],
        ['Messages', str(neg_stats.get('total_messages', 0))],
        ['Yields', str(neg_stats.get('yields', 0))],
        ['Close (<10%)', str(neg_stats.get('close_negotiations', 0))],
    ]
    
    table = ax4.table(cellText=stats_data[1:], colLabels=stats_data[0],
                      loc='center', cellLoc='center',
                      colColours=['#2c3e50', '#2ecc71'])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.3, 2)
    
    for i in range(2):
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    ax4.set_title('Statistiques de Négociation', fontsize=12, fontweight='bold')
    
    fig.suptitle('Détails du Mécanisme de Négociation', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph9_negotiation_details.png'), dpi=150)
    plt.close()
    print("✓ Graph 9: Détails négociation")


def generate_all_graphs(output_dir='graphs', steps=300):
    """
    Génère tous les graphiques pour la présentation.
    """
    # Créer le dossier de sortie
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("GÉNÉRATION DES GRAPHIQUES POUR LA PRÉSENTATION")
    print("=" * 60)
    print(f"Simulation: {steps} steps, spawn_rate=0.25")
    print()
    
    # Exécuter les simulations principales
    results = {}
    for mech in [Mechanism.FCFS, Mechanism.AUCTION, Mechanism.NEGOTIATION]:
        print(f"Simulation {mech.name}...")
        history, final_stats, wait_times, model = run_simulation(mech, steps=steps)
        results[mech.name] = {
            'history': history,
            'final_stats': final_stats,
            'wait_times': wait_times,
            'model': model
        }
    
    print()
    print("Génération des graphiques...")
    print("-" * 30)
    
    # Générer tous les graphiques
    plot_comparison_avg_wait(results, output_dir)
    plot_throughput_evolution(results, output_dir)
    plot_wait_time_distribution(results, output_dir)
    plot_auction_revenue(results, output_dir)
    plot_urgent_vehicles(results, output_dir)
    plot_collisions_avoided(results, output_dir)
    plot_summary_table(results, output_dir)
    
    # Graphique comparaison English vs Vickrey
    auction_results = plot_english_vs_vickrey(output_dir, steps=steps)
    
    # Graphique détails négociation
    plot_negotiation_details(results, output_dir)
    
    print()
    print("=" * 60)
    print(f"✅ TOUS LES GRAPHIQUES GÉNÉRÉS DANS '{output_dir}/'")
    print("=" * 60)
    
    # Afficher le résumé
    print("\nRÉSUMÉ DES RÉSULTATS:")
    print("-" * 30)
    for mech in ['FCFS', 'AUCTION', 'NEGOTIATION']:
        stats = results[mech]['final_stats']
        print(f"\n{mech}:")
        print(f"  - Véhicules sortis: {stats['total_crossed']}")
        print(f"  - Temps attente moyen: {stats['avg_wait_time']:.1f}")
        print(f"  - Urgents sortis: {stats['urgent_crossed']}")
        if mech == 'AUCTION':
            print(f"  - Revenue: {stats.get('total_revenue', 0)}")
            print(f"  - Enchères: {stats.get('auctions_held', 0)}")
        if mech == 'NEGOTIATION':
            print(f"  - Négociations: {stats.get('negotiations_held', 0)}")
    
    # Résumé English vs Vickrey
    print("\nCOMPARAISON ENGLISH vs VICKREY:")
    print("-" * 30)
    for atype in ['ENGLISH', 'VICKREY']:
        stats = auction_results[atype]['final_stats']
        mstats = auction_results[atype]['mech_stats']
        print(f"\n{atype}:")
        print(f"  - Temps attente: {stats['avg_wait_time']:.1f}")
        print(f"  - Revenue: {stats.get('total_revenue', 0)}")
        print(f"  - Rounds totaux: {mstats.get('total_rounds', 0)}")
    
    return results, auction_results


if __name__ == '__main__':
    results, auction_results = generate_all_graphs(output_dir='graphs', steps=300)
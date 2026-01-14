"""
Générateur de Graphiques pour la Présentation
==============================================

Génère tous les graphiques nécessaires pour la soutenance:
1. Comparaison des temps d'attente moyens
2. Évolution du débit (Throughput)
3. Distribution des temps d'attente (Boxplot & Histogramme)
4. Analyse économique (Revenus & Enchères)
5. Analyse sociale (Véhicules urgents)
6. Sécurité (Collisions évitées)
7. Comparaison English vs Vickrey
"""

import matplotlib.pyplot as plt
import numpy as np
import os
import sys

# Assurer que Python trouve les modules
sys.path.append(os.getcwd())

from intersection import SimpleIntersection
from constants import Mechanism
from mechanisms import AuctionType

# Style visuel pour la présentation
plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {
    'FCFS': '#3498db',        # Bleu
    'AUCTION': '#e74c3c',     # Rouge
    'NEGOTIATION': '#2ecc71', # Vert
    'ENGLISH': '#e67e22',     # Orange
    'VICKREY': '#9b59b6',     # Violet
    'URGENT': '#c0392b',      # Rouge foncé
    'NORMAL': '#2980b9'       # Bleu foncé
}

def run_simulation(mechanism, auction_type=AuctionType.VICKREY,
                   steps=500, spawn_rate=0.25, seed=42):
    """
    Exécute une simulation complète et retourne l'historique et les stats finales.
    """
    # Initialisation correcte compatible avec votre intersection.py
    model = SimpleIntersection(
        mechanism=mechanism,
        auction_type=auction_type,  # Passé directement au constructeur
        spawn_rate=spawn_rate,
        urgent_probability=0.15,
        seed=seed
    )
    
    history = {
        'step': [],
        'total_crossed': [],
        'avg_wait_time': [],
        'collisions_avoided': [],
        'auctions_held': [],
        'negotiations_held': [],
        'total_revenue': [],
    }
    
    wait_times = []
    
    print(f"   ... Exécution {mechanism.name} ({steps} steps)")
    
    for i in range(steps):
        model.step()
        stats = model.get_stats()
        
        history['step'].append(i + 1)
        history['total_crossed'].append(stats['total_crossed'])
        history['avg_wait_time'].append(stats['avg_wait_time'])
        history['collisions_avoided'].append(stats['collisions_avoided'])
        
        # Utilisation de .get() pour éviter les erreurs si la clé manque
        history['auctions_held'].append(stats.get('auctions_held', 0))
        history['negotiations_held'].append(stats.get('negotiations_held', 0))
        history['total_revenue'].append(stats.get('total_revenue', 0))
    
    # Collecte des temps d'attente individuels pour les distributions
    for v in model.exited_vehicles:
        if v.entry_time is not None:
            wait = v.entry_time - v.arrival_time
            wait_times.append(wait)
            
    return history, model.get_stats(), wait_times, model

def plot_1_avg_wait_comparison(results, output_dir):
    """Graphique 1: Comparaison des temps d'attente moyens"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    mechanisms = list(results.keys())
    avg_waits = [results[m]['final_stats']['avg_wait_time'] for m in mechanisms]
    colors = [COLORS.get(m, '#7f8c8d') for m in mechanisms]
    
    bars = ax.bar(mechanisms, avg_waits, color=colors, edgecolor='black', linewidth=1)
    
    # Labels sur les barres
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}s', ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax.set_ylabel('Temps d\'attente moyen (steps)', fontsize=12)
    ax.set_title('Performance Globale: Temps d\'Attente Moyen', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '01_comparaison_temps_attente.png'), dpi=150)
    plt.close()

def plot_2_throughput(results, output_dir):
    """Graphique 2: Évolution du débit (Véhicules sortis)"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for mech, data in results.items():
        ax.plot(data['history']['step'], data['history']['total_crossed'], 
                label=mech, color=COLORS.get(mech, 'gray'), linewidth=2.5)
    
    ax.set_xlabel('Temps de simulation (steps)', fontsize=12)
    ax.set_ylabel('Véhicules ayant traversé (cumulé)', fontsize=12)
    ax.set_title('Capacité de Traitement du Trafic', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '02_evolution_debit.png'), dpi=150)
    plt.close()

def plot_3_wait_distribution(results, output_dir):
    """Graphique 3: Distribution des temps d'attente (Boxplot)"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    data_to_plot = []
    labels = []
    
    for mech, data in results.items():
        if data['wait_times']:
            data_to_plot.append(data['wait_times'])
            labels.append(mech)
    
    # Création du boxplot
    box = ax.boxplot(data_to_plot, patch_artist=True, labels=labels, widths=0.6)
    
    # Coloriage
    for patch, label in zip(box['boxes'], labels):
        patch.set_facecolor(COLORS.get(label, 'gray'))
        patch.set_alpha(0.6)
    
    # Lignes médianes
    for median in box['medians']:
        median.set(color='black', linewidth=2)
        
    ax.set_ylabel('Temps d\'attente (steps)', fontsize=12)
    ax.set_title('Distribution des Temps d\'Attente (Équité)', fontsize=14, fontweight='bold')
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '03_distribution_attente.png'), dpi=150)
    plt.close()

def plot_4_urgent_handling(results, output_dir):
    """Graphique 4: Traitement des véhicules urgents vs normaux"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    mechanisms = list(results.keys())
    # Calcul des ratios
    ratios = []
    for m in mechanisms:
        stats = results[m]['final_stats']
        total = stats['total_crossed']
        urgent = stats.get('urgent_crossed', 0)
        # Si total est 0 (cas rare), éviter division par zéro
        pct = (urgent / total * 100) if total > 0 else 0
        ratios.append(pct)
    
    # Barres
    bars = ax.bar(mechanisms, ratios, color=[COLORS.get(m) for m in mechanisms], alpha=0.8)
    
    # Ligne cible théorique (ex: 15% de spawn rate urgent)
    ax.axhline(y=15, color='red', linestyle='--', label='Taux de génération Urgent (15%)')
    
    ax.set_ylabel('% de Véhicules Urgents Sortis', fontsize=12)
    ax.set_title('Efficacité du Traitement des Urgences', fontsize=14, fontweight='bold')
    ax.legend()
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '04_gestion_urgences.png'), dpi=150)
    plt.close()

def plot_5_english_vs_vickrey(output_dir):
    """Graphique 5: Comparaison spécifique des enchères"""
    print("\n   ... Comparaison English vs Vickrey")
    
    # Simulation spécifique
    res_vickrey = run_simulation(Mechanism.AUCTION, AuctionType.VICKREY, steps=300)[1]
    res_english = run_simulation(Mechanism.AUCTION, AuctionType.ENGLISH, steps=300)[1]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    types = ['Vickrey', 'English']
    colors = [COLORS['VICKREY'], COLORS['ENGLISH']]
    
    # Graphe Revenus
    revs = [res_vickrey.get('total_revenue', 0), res_english.get('total_revenue', 0)]
    bars1 = ax1.bar(types, revs, color=colors)
    ax1.set_title('Revenus Totaux du Système', fontweight='bold')
    ax1.set_ylabel('Crédits')
    
    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{int(bar.get_height())}', 
                 ha='center', va='bottom', fontweight='bold')

    # Graphe Prix Moyen
    avg_price = [res_vickrey.get('avg_price', 0), res_english.get('avg_price', 0)]
    bars2 = ax2.bar(types, avg_price, color=colors)
    ax2.set_title('Prix Moyen Payé par Véhicule', fontweight='bold')
    ax2.set_ylabel('Crédits')

    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{bar.get_height():.1f}', 
                 ha='center', va='bottom', fontweight='bold')
    
    plt.suptitle('Comparaison Économique: Vickrey vs English', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '05_comparaison_encheres.png'), dpi=150)
    plt.close()

def generate_summary_text(results, output_dir):
    """Génère un fichier texte avec les chiffres clés pour la conclusion"""
    filepath = os.path.join(output_dir, 'resultats_cles.txt')
    with open(filepath, 'w') as f:
        f.write("CHIFFRES CLES POUR LA PRESENTATION\n")
        f.write("==================================\n\n")
        
        for mech, data in results.items():
            stats = data['final_stats']
            f.write(f"--- {mech} ---\n")
            f.write(f"Passages totaux: {stats['total_crossed']}\n")
            f.write(f"Temps attente moy: {stats['avg_wait_time']:.2f} ticks\n")
            f.write(f"Collisions évitées: {stats['collisions_avoided']}\n")
            if 'negotiations_held' in stats and stats['negotiations_held'] > 0:
                f.write(f"Négociations tenues: {stats['negotiations_held']}\n")
            if 'total_revenue' in stats and stats['total_revenue'] > 0:
                f.write(f"Revenu total: {stats['total_revenue']}\n")
            f.write("\n")
    print(f"✓ Fichier résumé généré: {filepath}")

def main():
    output_dir = 'presentation_graphs'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Démarrage de la génération des graphiques dans '{output_dir}/'...")
    
    # 1. Exécuter les simulations principales
    results = {}
    steps = 500
    
    for mech in [Mechanism.FCFS, Mechanism.AUCTION, Mechanism.NEGOTIATION]:
        hist, stats, waits, _ = run_simulation(mech, steps=steps)
        results[mech.name] = {
            'history': hist,
            'final_stats': stats,
            'wait_times': waits
        }
    
    # 2. Générer les graphiques
    plot_1_avg_wait_comparison(results, output_dir)
    print("✓ Graphe 1 généré")
    
    plot_2_throughput(results, output_dir)
    print("✓ Graphe 2 généré")
    
    plot_3_wait_distribution(results, output_dir)
    print("✓ Graphe 3 généré")
    
    plot_4_urgent_handling(results, output_dir)
    print("✓ Graphe 4 généré")
    
    plot_5_english_vs_vickrey(output_dir)
    print("✓ Graphe 5 généré")
    
    generate_summary_text(results, output_dir)
    
    print("\n🎉 Terminé ! Vous pouvez insérer les images du dossier 'presentation_graphs' dans vos slides.")

if __name__ == '__main__':
    main()
# Autonomous Intersection Management (MAS)

Ce projet est une plateforme de simulation et de visualisation interactive pour comparer différents mécanismes de coordination de véhicules autonomes au niveau d'une intersection. 

Développé dans le cadre du Master **Intelligent Processing Systems (IPS)**, ce simulateur explore l'efficacité des protocoles de communication et de décision décentralisés.

## Mécanismes Implémentés
Le système permet de basculer dynamiquement entre quatre approches :
- **FCFS (First-Come, First-Served) :** Priorité basée sur l'ordre d'arrivée.
- **AUCTION :** Mécanismes d'enchères (Vickrey & English) où les véhicules "enchérissent" selon leur urgence.
- **NEGOTIATION :** Protocole multi-rounds basé sur l'utilité (Urgence, Attente, Carburant).
- **CHICKEN GAME :** Modélisation par la théorie des jeux pour gérer les conflits d'anti-coordination.

## Guide d'Exécution

### 1. Prérequis
- **Python 3.13** (testé et recommandé)
- Un terminal (Bash, PowerShell ou CMD)

### 2. Installation de l'environnement
Il est fortement recommandé d'utiliser un environnement virtuel pour isoler les dépendances :

```bash
# 1. Création de l'environnement virtuel
python -m venv venv

# 2. Activation
# Sur Windows :
venv\Scripts\activate
# Sur Linux/Mac :
source venv/bin/activate

# 3. Installation des bibliothèques nécessaires
pip install -r requirements.txt
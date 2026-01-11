"""
Solara Visualization - FCFS vs AUCTION vs NEGOTIATION
=====================================================

Visual interface for the intersection simulation.
"""
import solara
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
import matplotlib.patches as mpatches
import threading
import time

from intersection import SimpleIntersection
from constants import (
    GRID_SIZE, Mechanism, PARKING_ZONES, BARRIER_POSITIONS, 
    INTERSECTION_POS, WAITING_POSITIONS
)
from mechanisms import NegotiationType
from debug import logger

# =============================================================================
# GLOBAL STATE
# =============================================================================
current_mechanism = Mechanism.FCFS
current_negotiation_type = NegotiationType.STOCHASTIC
model = SimpleIntersection(
    mechanism=current_mechanism,
    negotiation_type=current_negotiation_type,
    spawn_rate=0.15,
    urgent_probability=0.1,
    seed=42
)
is_running = False
timer_thread = None

# Reactive state
tick = solara.reactive(0)
speed = solara.reactive(5)
spawn_rate_value = solara.reactive(0.15)
mechanism_choice = solara.reactive("FCFS")
negotiation_choice = solara.reactive("STOCHASTIC")

# Colors
COLORS = {
    'N': '#2980b9', 'S': '#c0392b', 'E': '#27ae60', 'W': '#8e44ad',
    'intersection': '#f1c40f', 'background': '#ecf0f1',
    'reserved': '#e74c3c', 'free': '#2ecc71', 'conflict': '#e74c3c',
    'parking_N': '#d5e8f7', 'parking_S': '#f7d5d5',
    'parking_E': '#d5f7e0', 'parking_W': '#e8d5f7',
    'barrier': '#f39c12', 'urgent': '#ff0000',
    'negotiating': '#9b59b6',
    'waiting': '#e67e22',
}


# =============================================================================
# TIMER CONTROL
# =============================================================================
def timer_loop():
    global is_running
    while is_running:
        model.step()
        tick.set(tick.value + 1)
        time.sleep(1.0 / speed.value)


def start_timer():
    global is_running, timer_thread
    if not is_running:
        is_running = True
        timer_thread = threading.Thread(target=timer_loop, daemon=True)
        timer_thread.start()


def stop_timer():
    global is_running
    is_running = False


def do_step():
    model.step()
    tick.set(tick.value + 1)


def toggle_running():
    global is_running
    if is_running:
        stop_timer()
    else:
        start_timer()
    tick.set(tick.value + 1)


def reset_simulation():
    global is_running, model, current_mechanism, current_negotiation_type
    stop_timer()
    
    mech_map = {
        "FCFS": Mechanism.FCFS, 
        "AUCTION": Mechanism.AUCTION, 
        "NEGOTIATION": Mechanism.NEGOTIATION
    }
    neg_map = {
        "STOCHASTIC": NegotiationType.STOCHASTIC, 
        "MARGINAL_UTILITY": NegotiationType.MARGINAL_UTILITY,
        "TOKEN_BASED": NegotiationType.TOKEN_BASED
    }
    
    current_mechanism = mech_map.get(mechanism_choice.value, Mechanism.FCFS)
    current_negotiation_type = neg_map.get(negotiation_choice.value, NegotiationType.STOCHASTIC)
    
    model = SimpleIntersection(
        mechanism=current_mechanism,
        negotiation_type=current_negotiation_type,
        spawn_rate=spawn_rate_value.value,
        urgent_probability=0.1,
        seed=42
    )
    tick.set(0)


# =============================================================================
# VISUALIZATION COMPONENTS
# =============================================================================
@solara.component
def IntersectionView():
    _ = tick.value
    
    fig = Figure(figsize=(14, 14), facecolor=COLORS['background'])
    ax = fig.add_subplot(111)
    ax.set_facecolor(COLORS['background'])
    
    stats = model.get_stats()
    is_negotiation = model.mechanism_type == Mechanism.NEGOTIATION
    is_auction = model.mechanism_type == Mechanism.AUCTION
    
    # 1. PARKING ZONES
    for direction, zone in PARKING_ZONES.items():
        x1, y1 = zone['start']
        x2, y2 = zone['end']
        width = x2 - x1 + 1
        height = y2 - y1 + 1
        
        rect = FancyBboxPatch(
            (x1 - 0.5, y1 - 0.5), width, height,
            boxstyle="round,pad=0.1,rounding_size=0.5",
            facecolor=COLORS[f'parking_{direction}'], 
            edgecolor=COLORS[direction],
            linewidth=2, alpha=0.6
        )
        ax.add_patch(rect)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, f"P-{direction}",
               ha='center', va='center', fontsize=8, fontweight='bold', 
               color=COLORS[direction], alpha=0.5)
    
    # 2. CORRIDORS
    ns_color = COLORS['reserved'] if stats['ns_corridor'] == 'RESERVED' else COLORS['free']
    ax.add_patch(Rectangle((6.5, 3.5), 1, 8, facecolor=ns_color, 
                           edgecolor='#7f8c8d', linewidth=2, alpha=0.4))
    
    ew_color = COLORS['reserved'] if stats['ew_corridor'] == 'RESERVED' else COLORS['free']
    ax.add_patch(Rectangle((3.5, 6.5), 8, 1, facecolor=ew_color, 
                           edgecolor='#7f8c8d', linewidth=2, alpha=0.4))
    
    # 3. BARRIERS
    for direction, pos in BARRIER_POSITIONS.items():
        rect = FancyBboxPatch(
            (pos[0] - 0.35, pos[1] - 0.35), 0.7, 0.7,
            boxstyle="round,pad=0.02",
            facecolor=COLORS['barrier'], edgecolor='#d35400', linewidth=2
        )
        ax.add_patch(rect)
        ax.plot([pos[0] - 0.2, pos[0] + 0.2], [pos[1], pos[1]], 
               color='black', linewidth=2)
    
    # 4. WAITING POSITIONS
    for direction, pos in WAITING_POSITIONS.items():
        ax.add_patch(Circle(pos, 0.15, facecolor='none', 
                           edgecolor=COLORS['waiting'], linewidth=1, 
                           linestyle='--', alpha=0.5))
    
    # 5. INTERSECTION
    conflict_occupied = stats['conflict_zone'] == 'OCCUPIED'
    intersection_color = COLORS['conflict'] if conflict_occupied else COLORS['intersection']
    ax.add_patch(Rectangle((6.5, 6.5), 1, 1, facecolor=intersection_color,
                           edgecolor='#d35400', linewidth=3, alpha=0.7))
    
    # 6. DIRECTION LABELS
    ax.text(7, -0.8, "NORTH", ha='center', fontsize=11, fontweight='bold', color=COLORS['N'])
    ax.text(7, 15.3, "SOUTH", ha='center', fontsize=11, fontweight='bold', color=COLORS['S'])
    ax.text(15.8, 7, "EAST", ha='center', fontsize=11, fontweight='bold', color=COLORS['E'])
    ax.text(-1.5, 7, "WEST", ha='center', fontsize=11, fontweight='bold', color=COLORS['W'])
    
    # 7. VEHICLES
    for v in model.get_all_vehicles_positions():
        if v['pos'] is None:
            continue
            
        x, y = v['pos']
        direction = v['direction']
        color = COLORS[direction]
        is_urgent = v.get('is_urgent', False)
        state = v.get('state', '')
        bid = v.get('bid')
        fuel = v.get('fuel', 100)
        is_neg = v.get('is_negotiating', False)
        is_waiting = v.get('waiting_at_intersection', False)
        
        radius = 0.28
        
        # Edge color based on state
        if is_neg:
            edge_color = COLORS['negotiating']
            edge_width = 3
        elif state == 'waiting' or is_waiting:
            edge_color = COLORS['waiting']
            edge_width = 2.5
        elif is_urgent and (is_auction or is_negotiation):
            edge_color = COLORS['urgent']
            edge_width = 2.5
        elif state == 'conflict':
            edge_color = '#d35400'
            edge_width = 2
        else:
            edge_color = '#2c3e50'
            edge_width = 1
        
        ax.add_patch(Circle((x, y), radius, facecolor=color,
                           edgecolor=edge_color, linewidth=edge_width))
        
        ax.text(x, y, f"{v['id']}", ha='center', va='center', 
               fontsize=6, fontweight='bold', color='white')
        
        # Status indicator
        if is_neg:
            ax.text(x, y + radius + 0.15, "NEG", ha='center', va='bottom',
                   fontsize=5, fontweight='bold', color=COLORS['negotiating'],
                   bbox=dict(boxstyle='round,pad=0.05', facecolor='white', 
                            edgecolor=COLORS['negotiating'], alpha=0.9))
        elif state == 'waiting' or is_waiting:
            ax.text(x, y + radius + 0.15, "WAIT", ha='center', va='bottom',
                   fontsize=5, fontweight='bold', color=COLORS['waiting'],
                   bbox=dict(boxstyle='round,pad=0.05', facecolor='white', 
                            edgecolor=COLORS['waiting'], alpha=0.9))
        
        # Label based on mode
        if is_negotiation:
            label_text = f"b:{bid}\nf:{fuel}"
            box_color = '#e8daef' if not is_urgent else '#ffcccc'
            text_color = '#2c3e50'
        elif is_auction:
            if is_urgent:
                label_text = f"URG\nb:{bid}"
                box_color = '#ffcccc'
                text_color = COLORS['urgent']
            else:
                label_text = f"b:{bid}"
                box_color = 'white'
                text_color = '#2c3e50'
        else:
            label_text = f"#{v['id']}"
            box_color = 'white'
            text_color = '#2c3e50'
        
        ax.text(x, y - radius - 0.25, label_text, 
               ha='center', va='top', fontsize=5, fontweight='bold', 
               color=text_color,
               bbox=dict(boxstyle='round,pad=0.1', facecolor=box_color, 
                        edgecolor=edge_color, alpha=0.9, linewidth=0.5))
    
    # 8. GRID
    for i in range(GRID_SIZE + 1):
        ax.axhline(y=i - 0.5, color='#bdc3c7', linewidth=0.2, alpha=0.3)
        ax.axvline(x=i - 0.5, color='#bdc3c7', linewidth=0.2, alpha=0.3)
    
    ax.set_xlim(-2.5, GRID_SIZE + 1.5)
    ax.set_ylim(-2, GRID_SIZE + 1)
    ax.set_aspect('equal')
    ax.axis('off')
    
    mode_label = stats['mechanism'].split()[0][:4].upper()
    title = f"[{mode_label}] Step: {stats['step']}"
    if stats.get('waiting_at_intersection', 0) > 0:
        title += f" | Waiting: {stats['waiting_at_intersection']}"
    ax.set_title(title, fontsize=14, fontweight='bold', color='#2c3e50')
    
    # 9. LEGEND
    legend_handles = [
        mpatches.Patch(facecolor=COLORS['parking_N'], edgecolor='gray', label='Parking'),
        mpatches.Patch(facecolor=COLORS['barrier'], label='Barrier'),
        mpatches.Patch(facecolor=COLORS['free'], alpha=0.5, label='FREE'),
        mpatches.Patch(facecolor=COLORS['reserved'], alpha=0.5, label='RESERVED'),
    ]
    if is_auction or is_negotiation:
        legend_handles.append(
            mpatches.Patch(facecolor='white', edgecolor=COLORS['urgent'], 
                          linewidth=2, label='URGENT')
        )
        legend_handles.append(
            mpatches.Patch(facecolor='white', edgecolor=COLORS['waiting'], 
                          linewidth=2, label='WAITING')
        )
    if is_negotiation:
        legend_handles.append(
            mpatches.Patch(facecolor='white', edgecolor=COLORS['negotiating'], 
                          linewidth=2, label='NEGOTIATING')
        )
    ax.legend(handles=legend_handles, loc='upper right', fontsize=7, framealpha=0.9)
    
    solara.FigureMatplotlib(fig)


@solara.component
def StatsPanel():
    _ = tick.value
    stats = model.get_stats()
    
    with solara.Card("Statistics", margin=2):
        solara.Markdown(f"""
| Metric | Value |
|--------|-------|
| Crossed | **{stats['total_crossed']}** |
| Avg Wait | {stats['avg_wait_time']:.1f} |
| Parking | {stats['parking_count']} |
| Barrier | {stats['barrier_count']} |
| Waiting | {stats.get('waiting_at_intersection', 0)} |
        """)


@solara.component
def StatusPanel():
    _ = tick.value
    stats = model.get_stats()
    
    with solara.Card("Status", margin=2):
        ns = "🔴" if stats['ns_corridor'] == 'RESERVED' else "🟢"
        ew = "🔴" if stats['ew_corridor'] == 'RESERVED' else "🟢"
        cz = "🔴" if stats['conflict_zone'] == 'OCCUPIED' else "🟢"
        
        solara.Markdown(f"**N-S:** {ns} | **E-W:** {ew} | **Center:** {cz}")


@solara.component
def NegotiationPanel():
    _ = tick.value
    
    if model.mechanism_type != Mechanism.NEGOTIATION:
        return
    
    stats = model.get_stats()
    last = model.get_last_negotiation()
    
    with solara.Card("🤝 Negotiation", margin=2):
        solara.Markdown(f"""
**Method:** {stats.get('negotiation_method', 'N/A')}
**Total:** {stats.get('negotiations_held', 0)}
        """)
        
        if last:
            solara.Markdown(f"""
---
**Last Result:**
- Winner: **V{last['winner_id']}**
- Loser: V{last['loser_id']}
- Via: {last['method']}
- Rounds: {last['rounds']}
            """)


@solara.component
def AuctionPanel():
    _ = tick.value
    
    if model.mechanism_type != Mechanism.AUCTION:
        return
    
    stats = model.get_stats()
    last = model.get_last_auction()
    
    with solara.Card("🔨 Auction", margin=2):
        solara.Markdown(f"""
- Auctions: **{stats.get('auctions_held', 0)}**
- Revenue: **{stats.get('total_revenue', 0)}**
- Avg Price: {stats.get('avg_price', 0):.1f}
        """)
        
        if last:
            urg = " 🚨" if last.get('is_urgent') else ""
            solara.Markdown(f"""
---
**Last Winner:** V{last['winner_id']}{urg}
Bid: {last['winning_bid']} | Paid: {last['price_paid']}
            """)


@solara.component
def ControlPanel():
    _ = tick.value
    
    with solara.Card("⚙️ Controls", margin=2):
        with solara.Row():
            solara.Button(
                "⏸️ Pause" if is_running else "▶️ Start", 
                on_click=toggle_running, 
                color="warning" if is_running else "primary"
            )
            solara.Button("⏭️ Step", on_click=do_step, disabled=is_running)
            solara.Button("🔄 Reset", on_click=reset_simulation, color="error")
        
        solara.Select(
            label="Mechanism",
            value=mechanism_choice,
            values=["FCFS", "AUCTION", "NEGOTIATION"],
            on_value=lambda v: mechanism_choice.set(v)
        )
        
        if mechanism_choice.value == "NEGOTIATION":
            solara.Select(
                label="Negotiation Type",
                value=negotiation_choice,
                values=["STOCHASTIC", "MARGINAL_UTILITY", "TOKEN_BASED"],
                on_value=lambda v: negotiation_choice.set(v)
            )
        
        solara.Markdown("*Click Reset to apply changes*")
        
        solara.SliderInt("Speed", value=speed, min=1, max=20)
        solara.SliderFloat("Spawn Rate", value=spawn_rate_value, min=0.05, max=0.5, step=0.05)


@solara.component
def InfoPanel():
    _ = tick.value
    
    with solara.Card("ℹ️ Info", margin=2):
        if model.mechanism_type == Mechanism.NEGOTIATION:
            solara.Markdown(f"""
**NEGOTIATION Mode**

When 2+ vehicles meet:
1. They WAIT before intersection
2. NEGOTIATE to decide priority
3. Winner passes, loser waits

**Type:** {negotiation_choice.value}
            """)
        elif model.mechanism_type == Mechanism.AUCTION:
            solara.Markdown("""
**AUCTION Mode** (Vickrey)

Priority = Highest Bid
- Normal: urgency × 10
- URGENT: 1000+

Winner pays 2nd highest bid.
            """)
        else:
            solara.Markdown("""
**FCFS Mode**

Priority = First Arrived

No bidding, no urgency.
Pure fairness.
            """)


# =============================================================================
# MAIN PAGE
# =============================================================================
@solara.component
def Page():
    mech = model.mechanism_type.value.split()[0].upper()
    
    solara.Title(f"🚗 Intersection: {mech}")
    
    with solara.Columns([3, 1]):
        with solara.Column():
            IntersectionView()
        
        with solara.Column():
            ControlPanel()
            StatusPanel()
            StatsPanel()
            if model.mechanism_type == Mechanism.AUCTION:
                AuctionPanel()
            if model.mechanism_type == Mechanism.NEGOTIATION:
                NegotiationPanel()
            InfoPanel()


# Entry point
app = Page
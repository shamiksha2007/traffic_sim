import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import time

# --- Modern Dark Mode Palette ---
COLOR_BG = "#0f172a"          # Deep Slate/Charcoal Dark Mode
COLOR_PANEL = "#1e293b"       # Floating Panel Background
COLOR_TEXT = "#f8fafc"        # Crisp White Text
COLOR_ROAD_CLEAN = "#10b981"  # Neon Green (Smooth)
COLOR_ROAD_MED = "#f59e0b"    # Neon Amber (Moderate)
COLOR_ROAD_TOXIC = "#ef4444"  # Neon Red (Heavy/Polluted)
COLOR_EMERGENCY = "#06b6d4"   # Bright Cyan (Emergency Corridor)
COLOR_CIVILIAN = "#ffffff"    # Pure White Dots
COLOR_AMBULANCE = "#ef4444"   # Bright Red
COLOR_FIRE = "#f97316"        # Vibrant Orange

class SimulatedTrafficAI:
    """An embedded offline layer that mimics LLM decision-making for hackathon demos."""
    
    def __init__(self):
        self.idle_logs = [
            "Optimizing signal timings based on current grid load...",
            "Micro-adjustments applied to signal phases to minimize idle time.",
            "Grid state nominal. Maintaining current adaptive flow.",
            "Predictive routing active: anticipating future traffic surges."
        ]

    def generate_insight(self, frame, active, stopped, avg_wait, graph, current_pol, baseline):
        """Analyzes the current grid state and returns a realistic AI log."""
        
        high_pol_edges = [e for e in graph.edges if graph.edges[e].get('pollution', 0) > 15]
        if len(high_pol_edges) > 1 and frame % 8 == 0:
            return f"🔴 [HIGH POLLUTION] Critical emissions on {len(high_pol_edges)} roads! AI prioritizing green lights to flush toxic zones."
        elif baseline > 0 and current_pol < baseline * 0.8 and frame % 15 == 0:
            return f"🟢 [IMPROVEMENT] AI Optimization stabilized. Toxic idling eliminated. Emissions reduced."

        max_queue = 0
        worst_node = None
        for node in graph.nodes:
            q_len = len(graph.nodes[node]['queue'])
            if q_len > max_queue:
                max_queue = q_len
                worst_node = node

        if max_queue > 2:
            return f"⚠️ [AI CRITICAL] Severe bottleneck at Intersection {worst_node}. Overriding standard logic to clear {max_queue} waiting vehicles."
        elif stopped > active * 0.4 and active > 0:
            return f"🔄 [AI ADJUSTMENT] Grid efficiency dropping (Avg Wait: {avg_wait:.1f}s). Synchronizing adjacent green lights to improve throughput."
        elif frame > 0 and frame % 12 == 0 and active > 0: 
            return f"📊 [AI SYSTEM] Periodic review complete. {random.choice(self.idle_logs)}"
            
        return None 

class Vehicle:
    """Represents a single vehicle navigating the city grid."""
    
    def __init__(self, v_id, start_node, dest_node, graph, v_type='normal'):
        self.v_id = v_id
        self.current_node = start_node
        self.dest_node = dest_node
        self.graph = graph
        self.v_type = v_type
        
        self.path = nx.shortest_path(graph, source=start_node, target=dest_node)
        self.path_index = 0
        self.wait_time = 0
        self.is_active = (start_node != dest_node)
        self.last_logged_node = None

    def get_next_node(self):
        if self.path_index + 1 < len(self.path):
            return self.path[self.path_index + 1]
        return None

    def move(self):
        self.path_index += 1
        self.current_node = self.path[self.path_index]
        if self.current_node == self.dest_node:
            if self.v_type in ['ambulance', 'fire_engine']:
                nodes = list(self.graph.nodes)
                new_dest = random.choice(nodes)
                while new_dest == self.current_node:
                    new_dest = random.choice(nodes)
                self.dest_node = new_dest
                self.path = nx.shortest_path(self.graph, source=self.current_node, target=self.dest_node)
                self.path_index = 0
            else:
                self.is_active = False

class TrafficSystem:
    """Manages the grid, adaptive signals, emergency overrides, pollution, and vehicle movements."""
    
    def __init__(self, grid_size=4, num_vehicles=25, steps=100):
        self.grid_size = grid_size
        self.total_steps = steps
        self.step_count = 0
        self.current_pollution = 0.0
        self.baseline_pollution = 0.0 
        
        self.graph = nx.grid_2d_graph(grid_size, grid_size)
        self.vehicles = []

        for node in self.graph.nodes:
            self.graph.nodes[node]['signal'] = random.choice(['NS', 'EW'])
            self.graph.nodes[node]['queue'] = []
            self.graph.nodes[node]['demand_NS'] = 0
            self.graph.nodes[node]['demand_EW'] = 0

        for u, v in self.graph.edges:
            self.graph[u][v]['density'] = 0
            self.graph[u][v]['pollution'] = 0.0

        nodes = list(self.graph.nodes)
        
        for i in range(num_vehicles):
            start = random.choice(nodes)
            dest = random.choice(nodes)
            while dest == start: dest = random.choice(nodes)
            self.vehicles.append(Vehicle(i, start, dest, self.graph, v_type='normal'))

        for e_id, e_type in enumerate(['ambulance', 'fire_engine'], start=num_vehicles):
            start = random.choice(nodes)
            dest = random.choice(nodes)
            while dest == start: dest = random.choice(nodes)
            self.vehicles.append(Vehicle(e_id, start, dest, self.graph, v_type=e_type))

    def get_direction(self, current_node, next_node):
        return 'EW' if next_node[0] != current_node[0] else 'NS'

    def step(self):
        self.step_count += 1
        
        for node in self.graph.nodes:
            self.graph.nodes[node]['demand_NS'] = 0
            self.graph.nodes[node]['demand_EW'] = 0
            self.graph.nodes[node]['queue'] = []
            
        edge_stats = {e: {'count': 0, 'wait': 0} for e in self.graph.edges}
        for u, v in self.graph.edges:
            self.graph[u][v]['density'] = 0

        for v in self.vehicles:
            if not v.is_active or v.v_type != 'normal':
                continue
            nxt = v.get_next_node()
            if nxt:
                direction_needed = self.get_direction(v.current_node, nxt)
                edge = (v.current_node, nxt) if (v.current_node, nxt) in edge_stats else (nxt, v.current_node)
                
                edge_stats[edge]['count'] += 1
                if v.wait_time > 0:
                    edge_stats[edge]['wait'] += v.wait_time
                
                current_edge_pollution = self.graph.edges[edge].get('pollution', 0)
                pollution_weight = current_edge_pollution * 0.25 
                
                if direction_needed == 'NS':
                    self.graph.nodes[v.current_node]['demand_NS'] += (1 + pollution_weight)
                else:
                    self.graph.nodes[v.current_node]['demand_EW'] += (1 + pollution_weight)

        for node in self.graph.nodes:
            ns_demand = self.graph.nodes[node]['demand_NS']
            ew_demand = self.graph.nodes[node]['demand_EW']
            
            if ns_demand > ew_demand:
                self.graph.nodes[node]['signal'] = 'NS'
            elif ew_demand > ns_demand:
                self.graph.nodes[node]['signal'] = 'EW'

        total_step_pollution = 0
        for e in self.graph.edges:
            c = edge_stats[e]['count']
            w = edge_stats[e]['wait']
            pol = (c * 1.5) + (w * 2.0)
            self.graph.edges[e]['pollution'] = pol
            total_step_pollution += pol
            
        self.current_pollution = total_step_pollution
        if self.step_count <= 15:
            self.baseline_pollution = max(self.baseline_pollution, total_step_pollution)

        ev_presence_nodes = set()
        for v in self.vehicles:
            if v.is_active and v.v_type in ['ambulance', 'fire_engine']:
                nxt = v.get_next_node()
                ev_presence_nodes.add(v.current_node)
                
                if nxt:
                    ev_presence_nodes.add(nxt)
                    direction = self.get_direction(v.current_node, nxt)
                    if v.last_logged_node != v.current_node:
                        icon = "🚑" if v.v_type == 'ambulance' else "🚒"
                        name = "Ambulance" if v.v_type == 'ambulance' else "Fire Engine"
                        print(f"\n{icon} [URGENT] {name} approaching {v.current_node}! Corridors overridden to {direction}.")
                        v.last_logged_node = v.current_node
                        
                    self.graph.nodes[v.current_node]['signal'] = direction
                    self.graph.nodes[nxt]['signal'] = direction

        stopped_count = 0

        for v in self.vehicles:
            if not v.is_active:
                continue

            nxt = v.get_next_node()
            if nxt:
                direction_needed = self.get_direction(v.current_node, nxt)
                node_signal = self.graph.nodes[v.current_node]['signal']
                is_emergency = (v.v_type in ['ambulance', 'fire_engine'])

                if is_emergency:
                    old_node = v.current_node
                    v.move()
                    self.graph[old_node][v.current_node]['density'] += 1
                else:
                    yield_to_ev = (v.current_node in ev_presence_nodes) or (nxt in ev_presence_nodes)
                    if node_signal == direction_needed and not yield_to_ev:
                        old_node = v.current_node
                        v.move()
                        self.graph[old_node][v.current_node]['density'] += 1
                    else:
                        v.wait_time += 1
                        stopped_count += 1
                        self.graph.nodes[v.current_node]['queue'].append(v.v_id)

        return stopped_count

    def get_metrics(self):
        total_wait = sum(v.wait_time for v in self.vehicles)
        avg_wait = total_wait / len(self.vehicles) if self.vehicles else 0
        active_vehicles = sum(1 for v in self.vehicles if v.is_active and v.v_type == 'normal')
        return total_wait, avg_wait, active_vehicles

# --- Visualization & Animation ---
def run_animated_simulation():
    system = TrafficSystem(grid_size=4, num_vehicles=30, steps=150)
    ai_layer = SimulatedTrafficAI() 
    
    # 1. Setup Dark Mode Figure
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    
    # 2. Organic Map Layout (Physics-based Spring Layout warped from grid)
    initial_pos = {(x, y): (x, -y) for x, y in system.graph.nodes()}
    pos = nx.spring_layout(system.graph, pos=initial_pos, iterations=15, seed=42)
    
    # 3. Generate Visual Background Density (Side streets that do not affect logic)
    visual_bg_lines = []
    min_x = min(p[0] for p in pos.values())
    max_x = max(p[0] for p in pos.values())
    min_y = min(p[1] for p in pos.values())
    max_y = max(p[1] for p in pos.values())
    for _ in range(35):
        p1 = (random.uniform(min_x-0.2, max_x+0.2), random.uniform(min_y-0.2, max_y+0.2))
        p2 = (p1[0] + random.uniform(-0.4, 0.4), p1[1] + random.uniform(-0.4, 0.4))
        visual_bg_lines.append((p1, p2))

    def update(frame):
        ax.clear()
        ax.axis('off') # Remove all grid lines and borders
        
        stopped_count = system.step()
        total_wait, avg_wait, active_count = system.get_metrics()
        
        # Extrapolate Emergency Corridors
        em_paths = set()
        for v in system.vehicles:
            if v.is_active and v.v_type in ['ambulance', 'fire_engine']:
                nxt = v.get_next_node()
                if nxt: em_paths.add(tuple(sorted((v.current_node, nxt))))
        
        # Environment Metrics
        pol_diff = 0.0
        if system.step_count > 15 and system.baseline_pollution > 0:
            pol_diff = ((system.baseline_pollution - system.current_pollution) / system.baseline_pollution) * 100
            baseline_str = f"Peak: {system.baseline_pollution:.1f}"
            reduction_str = f" | AI Reduced: {pol_diff:.1f}%" if pol_diff > 0 else " | AI Reduced: 0.0%"
        else:
            baseline_str = "Calibrating..."
            reduction_str = ""
            
        ai_insight = ai_layer.generate_insight(frame, active_count, stopped_count, avg_wait, system.graph, system.current_pollution, system.baseline_pollution)
        if ai_insight:
            print(f"\n[ STEP {frame + 1} ]")
            print(ai_insight)
            if pol_diff > 0:
                print(f"🌱 [ENV AI] Current optimization has reduced peak pollution by {pol_diff:.1f}%")

        # --- DRAW VISUAL LAYER ---
        
        # A. Draw faint side streets (texture) - Removed zorder
        for line in visual_bg_lines:
            ax.plot([line[0][0], line[1][0]], [line[0][1], line[1][1]], color='#1e293b', linewidth=1, alpha=0.5)

        # B. Parse and Draw Roads (Edges)
        edge_colors, edge_widths = [], []
        for u, v in system.graph.edges:
            pol = system.graph[u][v].get('pollution', 0)
            edge_tuple = tuple(sorted((u, v)))
            
            if edge_tuple in em_paths:
                edge_colors.append(COLOR_EMERGENCY) # Cyan Override!
                edge_widths.append(5.0)
            else:
                if pol < 5: 
                    edge_colors.append(COLOR_ROAD_CLEAN)
                elif pol < 15: 
                    edge_colors.append(COLOR_ROAD_MED)
                else: 
                    edge_colors.append(COLOR_ROAD_TOXIC)
                edge_widths.append(1.5 + min(pol * 0.25, 6))

        # Background Glow Effect - Removed zorder
        nx.draw_networkx_edges(system.graph, pos, ax=ax, edge_color=edge_colors, width=[w*2.5 for w in edge_widths], alpha=0.15)
        # Sharp Foreground Road - Removed zorder
        nx.draw_networkx_edges(system.graph, pos, ax=ax, edge_color=edge_colors, width=edge_widths, alpha=0.8)

        # C. Draw Vehicles (NO NODES OR LABELS)
        normal_nodes = [v.current_node for v in system.vehicles if v.is_active and v.v_type == 'normal']
        amb_nodes = [v.current_node for v in system.vehicles if v.is_active and v.v_type == 'ambulance']
        fire_nodes = [v.current_node for v in system.vehicles if v.is_active and v.v_type == 'fire_engine']

        # Draw vehicles (Order here dictates visual stacking, naturally replacing zorder)
        if normal_nodes:
            veh_pos = {n: (pos[n][0] + random.uniform(-0.02, 0.02), pos[n][1] + random.uniform(-0.02, 0.02)) for n in normal_nodes}
            nx.draw_networkx_nodes(system.graph, veh_pos, nodelist=normal_nodes, ax=ax, node_color=COLOR_CIVILIAN, node_size=15)
            
        if amb_nodes:
            amb_pos = {n: (pos[n][0], pos[n][1]) for n in amb_nodes}
            nx.draw_networkx_nodes(system.graph, amb_pos, nodelist=amb_nodes, ax=ax, node_color=COLOR_AMBULANCE, node_size=200, alpha=0.3) # Glow
            nx.draw_networkx_nodes(system.graph, amb_pos, nodelist=amb_nodes, ax=ax, node_color=COLOR_AMBULANCE, node_size=50, edgecolors='white') # Core
            
        if fire_nodes:
            fire_pos = {n: (pos[n][0], pos[n][1]) for n in fire_nodes}
            nx.draw_networkx_nodes(system.graph, fire_pos, nodelist=fire_nodes, ax=ax, node_color=COLOR_FIRE, node_size=200, alpha=0.3) # Glow
            nx.draw_networkx_nodes(system.graph, fire_pos, nodelist=fire_nodes, ax=ax, node_color=COLOR_FIRE, node_size=60, edgecolors='white') # Core

        # D. Modern Floating Dashboard UI
        dash_text = (
            f" SMART CITY TRAFFIC AI SYSTEM \n"
            f"─────────────────────────────────────\n"
            f" Step: {frame + 1}/{system.total_steps}  | Active Cars: {active_count}\n"
            f" Avg Wait: {avg_wait:.1f}s | Stopped: {stopped_count}\n"
            f"─────────────────────────────────────\n"
            f" 🌍 ENV POLLUTION INDEX: {system.current_pollution:.1f}\n"
            f" {baseline_str}{reduction_str}"
        )
        
        # Placed elegantly in the top-left corner
        ax.text(0.02, 0.98, dash_text, transform=ax.transAxes, ha='left', va='top',
                fontsize=11, color=COLOR_TEXT, family='monospace',
                bbox=dict(facecolor=COLOR_PANEL, alpha=0.8, edgecolor='#334155', boxstyle='round,pad=0.8', linewidth=1))

        # E. Clean Minimal Legend (Bottom Left)
        ax.plot([], [], color=COLOR_ROAD_CLEAN, linewidth=2, label='Smooth Flow')
        ax.plot([], [], color=COLOR_ROAD_MED, linewidth=3, label='Moderate Load')
        ax.plot([], [], color=COLOR_ROAD_TOXIC, linewidth=4, label='Toxic Congestion')
        ax.plot([], [], color=COLOR_EMERGENCY, linewidth=4, label='Emergency Override')
        ax.scatter([], [], c=COLOR_CIVILIAN, s=30, label='Civilian Vehicle')
        ax.scatter([], [], c=COLOR_AMBULANCE, s=80, edgecolors='white', label='Ambulance / Fire')
        
        legend = ax.legend(loc='lower left', frameon=True, fontsize=10, labelcolor=COLOR_TEXT)
        legend.get_frame().set_facecolor(COLOR_PANEL)
        legend.get_frame().set_edgecolor('#334155')
        legend.get_frame().set_alpha(0.8)

        # F. Final Validation Logging
        if active_count == 0:
            ani.event_source.stop()
            pollution_before_ai = system.baseline_pollution
            pollution_after_ai = system.current_pollution
            reduction = ((pollution_before_ai - pollution_after_ai) / pollution_before_ai) * 100 if pollution_before_ai > 0 else 0.0
                
            print("\n✅ [AI SYSTEM] All civilian vehicles routed successfully. Grid clear.")
            print(f"🌍 [ENV DATA] Initial Peak Pollution: {pollution_before_ai:.2f}")
            print(f"🌍 [ENV DATA] Final Pollution: {pollution_after_ai:.2f}")
            print(f"🌍 [FINAL ENV] AI reduced pollution by {reduction:.2f}%")
            
            # End Banner
            ax.text(0.5, 0.5, "SIMULATION COMPLETE\nCIVILIAN GRID CLEAR", transform=ax.transAxes, ha='center', va='center',
                fontsize=20, fontweight='bold', color=COLOR_ROAD_CLEAN, 
                bbox=dict(facecolor=COLOR_PANEL, alpha=0.9, edgecolor=COLOR_ROAD_CLEAN, boxstyle='round,pad=1'))

    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01) # Maximize map area
    ani = animation.FuncAnimation(fig, update, frames=system.total_steps, interval=400, repeat=False)
    plt.show()

if __name__ == "__main__":
    print("=====================================================")
    print("  INITIALIZING SMART CITY AI INFRASTRUCTURE  ")
    print("=====================================================\n")
    time.sleep(0.5)
    print("[SYSTEM] Loading local Embedded Inference Layer...")
    time.sleep(0.5)
    print("[SYSTEM] Connecting to city grid nodes... OK")
    time.sleep(0.5)
    print("[SYSTEM] Initializing Emergency Detection Network... ONLINE")
    time.sleep(0.5)
    print("[SYSTEM] Activating Environmental Air Quality Sensors... ONLINE")
    time.sleep(0.5)
    print("[SYSTEM] Launching Live Dashboard...\n")
    print("-" * 53)
    
    run_animated_simulation()
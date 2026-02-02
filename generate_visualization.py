"""
Genera visualizzazioni statiche della traiettoria
Output: immagini PNG ad alta risoluzione per portfolio
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from trajectory_simulator import TrajectorySimulator, Point, MovementCommand
from typing import List

class TrajectoryVisualizer:
    def __init__(self, style='dark_background'):
        plt.style.use(style)
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    
    def plot_trajectory_2d(
        self,
        points: List,
        movements: List[MovementCommand],
        title: str = "Robot Trajectory Simulation",
        save_path: str = "trajectory_2d.png"
    ):
        """Vista top-down della traiettoria con zone e velocità"""
        fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
        
        # Estrai coordinate
        x = [p.x for p in points]
        y = [p.y for p in points]
        v = [p.velocity for p in points]
        
        # Colormap basata su velocità
        scatter = ax.scatter(x, y, c=v, cmap='plasma', s=15, alpha=0.8, edgecolors='none')
        cbar = plt.colorbar(scatter, ax=ax, label='Velocity (mm/s)')
        cbar.ax.tick_params(labelsize=10)
        
        # Disegna punti target e zone
        for i, move in enumerate(movements):
            color = self.colors[i % len(self.colors)]
            
            # Punto target
            ax.plot(move.target.x, move.target.y, 'o', color=color, markersize=12, 
                   markeredgecolor='white', markeredgewidth=2, zorder=5)
            ax.annotate(f'P{i+1}\n{move.speed}mm/s\n{move.zone}', 
                       (move.target.x, move.target.y), 
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=9, color='white', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
            
            # Cerchio zona (se applicabile)
            from trajectory_simulator import ZONE_SIZES
            zone_size = ZONE_SIZES[move.zone]
            if zone_size > 0:
                circle = plt.Circle((move.target.x, move.target.y), zone_size, 
                                  fill=False, color=color, linestyle='--', alpha=0.5, linewidth=1.5)
                ax.add_patch(circle)
        
        # Punto di partenza
        ax.plot(x[0], y[0], 's', color='#00FF00', markersize=15, 
               markeredgecolor='white', markeredgewidth=2, label='Start', zorder=6)
        
        # Direzione con frecce
        for i in range(0, len(x)-20, len(x)//8):
            dx = x[i+10] - x[i]
            dy = y[i+10] - y[i]
            ax.annotate('', xy=(x[i+10], y[i+10]), xytext=(x[i], y[i]),
                       arrowprops=dict(arrowstyle='->', color='white', alpha=0.4, lw=1.5))
        
        ax.set_xlabel('X (mm)', fontsize=12, color='white')
        ax.set_ylabel('Y (mm)', fontsize=12, color='white')
        ax.set_title(title, fontsize=16, fontweight='bold', color='white', pad=20)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.2, color='gray')
        ax.tick_params(colors='white')
        
        # Sfondo scuro per contrasto
        ax.set_facecolor('#1a1a1a')
        fig.patch.set_facecolor('#1a1a1a')
        
        plt.tight_layout()
        plt.savefig(save_path, facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight')
        plt.close()
        print(f"Salvato: {save_path}")
    
    def plot_velocity_profile(
        self,
        points: List,
        save_path: str = "velocity_profile.png"
    ):
        """Grafico velocità e accelerazione vs tempo"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=150, sharex=True)
        
        t = [p.timestamp for p in points]
        v = [p.velocity for p in points]
        a = [p.acceleration for p in points]
        
        # Velocità
        ax1.fill_between(t, v, alpha=0.3, color='#4ECDC4')
        ax1.plot(t, v, color='#4ECDC4', linewidth=2, label='Velocity')
        ax1.set_ylabel('Velocity (mm/s)', fontsize=11, color='white')
        ax1.set_title('Motion Profiles', fontsize=14, fontweight='bold', color='white')
        ax1.grid(True, alpha=0.2, color='gray')
        ax1.legend(loc='upper right')
        ax1.tick_params(colors='white')
        
        # Accelerazione
        colors = ['#FF6B6B' if acc >= 0 else '#FFA07A' for acc in a]
        ax2.fill_between(t, a, alpha=0.3, color=colors[0])
        ax2.plot(t, a, color='#FF6B6B', linewidth=2, label='Acceleration')
        ax2.axhline(y=0, color='white', linestyle='-', alpha=0.3)
        ax2.set_xlabel('Time (s)', fontsize=11, color='white')
        ax2.set_ylabel('Acceleration (mm/s²)', fontsize=11, color='white')
        ax2.grid(True, alpha=0.2, color='gray')
        ax2.legend(loc='upper right')
        ax2.tick_params(colors='white')
        
        for ax in [ax1, ax2]:
            ax.set_facecolor('#1a1a1a')
        
        fig.patch.set_facecolor('#1a1a1a')
        plt.tight_layout()
        plt.savefig(save_path, facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight')
        plt.close()
        print(f"Salvato: {save_path}")
    
    def create_composite_preview(
        self,
        points: List,
        movements: List[MovementCommand],
        stats: dict,
        rapid_code: str,
        save_path: str = "project_preview.png"
    ):
        """Immagine composita per anteprima GitHub/sito web"""
        fig = plt.figure(figsize=(16, 10), dpi=150)
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Traiettoria 2D (grande, a sinistra)
        ax_traj = fig.add_subplot(gs[:, :2])
        x = [p.x for p in points]
        y = [p.y for p in points]
        v = [p.velocity for p in points]
        
        scatter = ax_traj.scatter(x, y, c=v, cmap='plasma', s=20, alpha=0.8)
        plt.colorbar(scatter, ax=ax_traj, label='Vel (mm/s)', fraction=0.046)
        
        for i, move in enumerate(movements):
            ax_traj.plot(move.target.x, move.target.y, 'o', color='white', markersize=10)
            ax_traj.annotate(f'P{i+1}', (move.target.x, move.target.y), 
                           color='white', fontsize=9, xytext=(5, 5), textcoords='offset points')
        
        ax_traj.plot(x[0], y[0], 's', color='#00FF00', markersize=12, label='Start')
        ax_traj.set_title('ABB Robot Trajectory Simulation', fontsize=14, fontweight='bold', color='white')
        ax_traj.set_xlabel('X (mm)', color='white')
        ax_traj.set_ylabel('Y (mm)', color='white')
        ax_traj.set_facecolor('#2a2a2a')
        ax_traj.tick_params(colors='white')
        
        # 2. Stats box (alto destra)
        ax_stats = fig.add_subplot(gs[0, 2])
        ax_stats.axis('off')
        stats_text = f"""
        CYCLE STATISTICS
        
        Total Time: {stats['total_time']:.2f} s
        Distance: {stats['total_distance']:.1f} mm
        Max Velocity: {stats['max_velocity']:.1f} mm/s
        Max Accel: {stats['max_acceleration']:.1f} mm/s²
        Segments: {stats['segments']}
        Points: {stats['points_generated']}
        """
        ax_stats.text(0.1, 0.5, stats_text, transform=ax_stats.transAxes, 
                     fontsize=11, verticalalignment='center', color='white',
                     fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='#3a3a3a', alpha=0.8))
        ax_stats.set_facecolor('#1a1a1a')
        
        # 3. Velocity profile preview (mezzo destro)
        ax_vel = fig.add_subplot(gs[1, 2])
        t = [p.timestamp for p in points]
        v = [p.velocity for p in points]
        ax_vel.plot(t, v, color='#4ECDC4', linewidth=2)
        ax_vel.fill_between(t, v, alpha=0.3, color='#4ECDC4')
        ax_vel.set_title('Velocity Profile', fontsize=11, color='white')
        ax_vel.set_xlabel('Time (s)', color='white')
        ax_vel.set_ylabel('mm/s', color='white')
        ax_vel.set_facecolor('#2a2a2a')
        ax_vel.tick_params(colors='white')
        ax_vel.grid(True, alpha=0.2)
        
        # 4. RAPID code preview (basso destra)
        ax_code = fig.add_subplot(gs[2, 2])
        ax_code.axis('off')
        code_preview = "\n".join(rapid_code.split("\n")[:15]) + "\n    ..."
        ax_code.text(0.05, 0.95, code_preview, transform=ax_code.transAxes,
                    fontsize=8, verticalalignment='top', color='#98D8C8',
                    fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='#0a0a0a', alpha=0.9))
        ax_code.set_title('RAPID Code Export', fontsize=11, color='white')
        ax_code.set_facecolor('#1a1a1a')
        
        fig.patch.set_facecolor('#1a1a1a')
        plt.savefig(save_path, facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight', dpi=150)
        plt.close()
        print(f"Salvato: {save_path}")

if __name__ == "__main__":
    # Esempio: Percorso quadrato industriale
    sim = TrajectorySimulator()
    viz = TrajectoryVisualizer()
    
    start = Point(0, 0)
    movements = [
        MovementCommand(Point(400, 0), 150, "z5"),
        MovementCommand(Point(400, 300), 100, "z10"),
        MovementCommand(Point(0, 300), 150, "z5"),
        MovementCommand(Point(0, 0), 80, "fine")
    ]
    
    points, stats = sim.simulate(start, movements)
    rapid = sim.generate_rapid(start, movements)
    
    # Genera tutte le visualizzazioni
    viz.plot_trajectory_2d(points, movements, "Industrial Welding Path", "outputs/trajectory_2d.png")
    viz.plot_velocity_profile(points, "outputs/velocity_profile.png")
    viz.create_composite_preview(points, movements, stats, rapid, "outputs/project_preview.png")
    
    # Salva anche il codice RAPID
    with open("outputs/rapid_code.txt", "w") as f:
        f.write(rapid)
    
    print(f"\nSimulazione completata!")
    print(f"Tempo ciclo: {stats['total_time']}s")
    print(f"File generati in /outputs")

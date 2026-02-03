"""
Robot Trajectory Simulator - Versione Standalone
Unico file: genera traiettoria, visualizzazioni e codice RAPID
"""

import math
from dataclasses import dataclass
from typing import List, Literal, Tuple
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import os

# ============ CONFIGURAZIONE ============
ZoneType = Literal["z0", "z1", "z5", "z10", "z20", "z50", "fine"]

ZONE_SIZES = {
    "z0": 0.3, "z1": 1.0, "z5": 5.0, "z10": 10.0,
    "z20": 20.0, "z50": 50.0, "fine": 0.0
}

# ============ CLASSI CORE ============

@dataclass
class Point:
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class MovementCommand:
    target: Point
    speed: float  # mm/s
    zone: ZoneType

@dataclass
class TrajectoryPoint:
    timestamp: float
    x: float
    y: float
    velocity: float
    acceleration: float
    segment_index: int

class TrajectorySimulator:
    def __init__(self, accel_time: float = 0.2, dt: float = 0.02):
        self.accel_time = accel_time
        self.dt = dt
    
    def interpolate_segment(
        self,
        start: Point,
        end: Point,
        speed: float,
        zone_size: float,
        segment_idx: int
    ) -> List[TrajectoryPoint]:
        """Genera profilo trapezoidale per un segmento"""
        distance = start.distance_to(end)
        angle = math.atan2(end.y - start.y, end.x - start.x)
        effective_distance = max(0.1, distance - zone_size)
        
        # Calcolo fasi moto
        accel_dist = 0.5 * speed * self.accel_time
        
        if effective_distance < 2 * accel_dist:
            # Profilo triangolare (non raggiunge v max)
            max_v = math.sqrt(effective_distance * speed / self.accel_time)
            t_acc = max_v / (speed / self.accel_time)
            t_cruise = 0
        else:
            # Profilo trapezoidale
            max_v = speed
            t_acc = self.accel_time
            t_cruise = (effective_distance - 2 * accel_dist) / max_v
        
        t_total = 2 * t_acc + t_cruise
        points = []
        t = 0
        
        while t <= t_total:
            # Calcola velocità e spazio percorso
            if t < t_acc:
                v = (max_v / t_acc) * t
                s = 0.5 * (max_v / t_acc) * t**2
                a = max_v / t_acc
            elif t < t_acc + t_cruise:
                v = max_v
                s = accel_dist + max_v * (t - t_acc)
                a = 0
            else:
                t_dec = t - (t_acc + t_cruise)
                v = max_v - (max_v / t_acc) * t_dec
                s = (effective_distance - accel_dist) + max_v * t_dec - 0.5 * (max_v / t_acc) * t_dec**2
                a = -max_v / t_acc
            
            # Posizione cartesiana
            if s < distance:
                px = start.x + math.cos(angle) * s
                py = start.y + math.sin(angle) * s
            else:
                px, py = end.x, end.y
            
            points.append(TrajectoryPoint(
                timestamp=round(t, 3),
                x=round(px, 2),
                y=round(py, 2),
                velocity=round(v, 2),
                acceleration=round(a, 2),
                segment_index=segment_idx
            ))
            t += self.dt
        
        return points
    
    def simulate(
        self,
        start: Point,
        movements: List[MovementCommand]
    ) -> Tuple[List[TrajectoryPoint], dict]:
        """Simula traiettoria completa"""
        all_points = []
        current_pos = start
        t_offset = 0
        stats = {"segments": len(movements), "total_distance": 0}
        
        for idx, move in enumerate(movements):
            zone = ZONE_SIZES[move.zone]
            segment = self.interpolate_segment(current_pos, move.target, move.speed, zone, idx)
            
            # Aggiorna timestamp
            for p in segment:
                p.timestamp = round(p.timestamp + t_offset, 3)
                all_points.append(p)
            
            if segment:
                t_offset = segment[-1].timestamp
            
            # Calcola nuova posizione effettiva (considerando zona)
            if zone > 0:
                dist = current_pos.distance_to(move.target)
                if dist > 0:
                    ratio = max(0, (dist - zone) / dist)
                    current_pos = Point(
                        x=current_pos.x + (move.target.x - current_pos.x) * ratio,
                        y=current_pos.y + (move.target.y - current_pos.y) * ratio
                    )
            else:
                current_pos = move.target
            
            stats["total_distance"] += start.distance_to(move.target) if idx == 0 else \
                movements[idx-1].target.distance_to(move.target)
        
        # Statistiche finali
        stats.update({
            "total_time": round(all_points[-1].timestamp, 2) if all_points else 0,
            "max_velocity": round(max(p.velocity for p in all_points), 2) if all_points else 0,
            "max_acceleration": round(max(abs(p.acceleration) for p in all_points), 2) if all_points else 0,
            "points_generated": len(all_points)
        })
        
        return all_points, stats
    
    def generate_rapid(
        self,
        start: Point,
        movements: List[MovementCommand],
        tool_name: str = "tool0"
    ) -> str:
        """Genera codice RAPID ABB"""
        lines = [
            "MODULE TrajectorySim",
            "    ! ==========================================",
            "    ! Generated by Python Trajectory Simulator",
            "    ! https://github.com/tuousername/robot-trajectory-sim",
            "    ! ==========================================",
            f"    CONST robtarget pStart := [[{start.x:.1f}, {start.y:.1f}, 0.0], [1, 0, 0, 0], [0, 0, 0, 0], [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]];",
            ""
        ]
        
        # Definisci target intermedi
        for i, move in enumerate(movements):
            lines.append(f"    CONST robtarget p{i+1} := [[{move.target.x:.1f}, {move.target.y:.1f}, 0.0], [1, 0, 0, 0], [0, 0, 0, 0], [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]];")
        
        lines.extend(["", "    PROC main()", "        ! Move to start position", f"        MoveL pStart, v100, fine, {tool_name};", ""])
        
        for i, move in enumerate(movements):
            lines.append(f"        ! Segment {i+1}: speed={move.speed}mm/s, zone={move.zone}")
            lines.append(f"        MoveL p{i+1}, v{int(move.speed)}, {move.zone}, {tool_name};")
            lines.append("")
        
        lines.extend(["    ENDPROC", "ENDMODULE"])
        return "\n".join(lines)
    
    def export_json(self, points: List[TrajectoryPoint], filename: str):
        """Esporta punti in JSON per analisi"""
        data = [{
            "t": p.timestamp,
            "x": p.x,
            "y": p.y,
            "v": p.velocity,
            "a": p.acceleration,
            "seg": p.segment_index
        } for p in points]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

# ============ VISUALIZZAZIONE ============

class TrajectoryVisualizer:
    def __init__(self, style='dark_background'):
        plt.style.use(style)
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    
    def plot_trajectory_2d(
        self,
        points: List[TrajectoryPoint],
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
        print(f"✓ Salvato: {save_path}")
    
    def plot_velocity_profile(
        self,
        points: List[TrajectoryPoint],
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
        ax2.fill_between(t, a, alpha=0.3, color='#FF6B6B')
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
        print(f"✓ Salvato: {save_path}")
    
    def create_composite_preview(
        self,
        points: List[TrajectoryPoint],
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
        print(f"✓ Salvato: {save_path}")

# ============ ESEMPIO D'USO ============

def main():
    """Esempio: Percorso quadrato industriale"""
    
    # Crea cartella outputs se non esiste
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
        print("📁 Creata cartella 'outputs/'")
    
    # Configurazione
    sim = TrajectorySimulator(accel_time=0.25, dt=0.01)
    viz = TrajectoryVisualizer()
    
    # Definisci percorso tipico saldatura telaio
    start_pos = Point(0, 0)
    path = [
        MovementCommand(Point(400, 0),   150, "z5"),   # Avvicinamento veloce
        MovementCommand(Point(400, 300), 80,  "z1"),   # Saldatura lenta, precisione
        MovementCommand(Point(200, 300), 100, "z5"),   # Trasferimento
        MovementCommand(Point(200, 150), 60,  "z0"),   # Saldatura dettaglio
        MovementCommand(Point(0, 150),   100, "z5"),   # Trasferimento
        MovementCommand(Point(0, 0),     120, "fine")  # Ritorno preciso
    ]
    
    print("🤖 Robot Trajectory Simulator")
    print("=" * 50)
    print("Simulazione traiettoria ABB in corso...\n")
    
    # Esegui simulazione
    points, stats = sim.simulate(start_pos, path)
    rapid_code = sim.generate_rapid(start_pos, path, tool_name="weldGun1")
    
    # Stampa statistiche
    print(f"📊 RISULTATI:")
    print(f"   ⏱️  Tempo totale: {stats['total_time']:.2f} secondi")
    print(f"   📏 Distanza: {stats['total_distance']:.1f} mm")
    print(f"   🚀 Velocità max: {stats['max_velocity']:.1f} mm/s")
    print(f"   ⚡ Accelerazione max: {stats['max_acceleration']:.1f} mm/s²")
    print(f"   📍 Punti calcolati: {stats['points_generated']}")
    
    # Genera visualizzazioni
    print(f"\n🎨 Generazione immagini...")
    viz.plot_trajectory_2d(points, path, "Welding Cell Trajectory - Frame Type A", 
                          "outputs/trajectory_2d.png")
    viz.plot_velocity_profile(points, "outputs/velocity_profile.png")
    viz.create_composite_preview(points, path, stats, rapid_code, 
                                "outputs/project_preview.png")
    
    # Salva RAPID e JSON
    with open("outputs/program.mod", "w") as f:
        f.write(rapid_code)
    sim.export_json(points, "outputs/trajectory_data.json")
    
    print(f"\n✅ COMPLETATO!")
    print(f"   📁 outputs/trajectory_2d.png - Vista 2D traiettoria")
    print(f"   📁 outputs/velocity_profile.png - Profili velocità/accelerazione")
    print(f"   📁 outputs/project_preview.png - Anteprima composita (per portfolio)")
    print(f"   📁 outputs/program.mod - Codice RAPID esportato")
    print(f"   📁 outputs/trajectory_data.json - Dati grezzi")

if __name__ == "__main__":
    main()

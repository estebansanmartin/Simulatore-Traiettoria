"""
Simulatore Traiettoria Robotica ABB
Genera profili di moto realistici con esportazione RAPID
"""

import math
from dataclasses import dataclass
from typing import List, Literal, Tuple
import json

ZoneType = Literal["z0", "z1", "z5", "z10", "z20", "z50", "fine"]

ZONE_SIZES = {
    "z0": 0.3, "z1": 1.0, "z5": 5.0, "z10": 10.0,
    "z20": 20.0, "z50": 50.0, "fine": 0.0
}

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
            # Calcola velocità e spazio percors
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

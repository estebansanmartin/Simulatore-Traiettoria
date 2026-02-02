"""
Esempio: Percorso quadrato con parametri industriali
"""

import sys
sys.path.append('..')

from trajectory_simulator import TrajectorySimulator, Point, MovementCommand
from generate_visualization import TrajectoryVisualizer

def main():
    # Configurazione simulazione
    sim = TrajectorySimulator(accel_time=0.25, dt=0.01)
    viz = TrajectoryVisualizer()
    
    # Definisci percorso: quadrato 400x300mm (tipico telaio)
    start_pos = Point(0, 0)
    path = [
        MovementCommand(Point(400, 0),   150, "z5"),   # Base veloce
        MovementCommand(Point(400, 300), 80,  "z1"),   # Saldatura lenta, precisione
        MovementCommand(Point(200, 300), 100, "z5"),   # Trasferimento
        MovementCommand(Point(200, 150), 60,  "z0"),   # Saldatura dettaglio
        MovementCommand(Point(0, 150),   100, "z5"),   # Trasferimento
        MovementCommand(Point(0, 0),     120, "fine")  # Ritorno preciso
    ]
    
    print("🤖 Simulazione traiettoria robot ABB")
    print("=" * 50)
    
    # Esegui simulazione
    points, stats = sim.simulate(start_pos, path)
    rapid_code = sim.generate_rapid(start_pos, path, tool_name="weldGun1")
    
    # Stampa statistiche
    print(f"\n📊 Risultati:")
    print(f"   Tempo totale: {stats['total_time']:.2f} secondi")
    print(f"   Distanza: {stats['total_distance']:.1f} mm")
    print(f"   Velocità max: {stats['max_velocity']:.1f} mm/s")
    print(f"   Accelerazione max: {stats['max_acceleration']:.1f} mm/s²")
    print(f"   Punti calcolati: {stats['points_generated']}")
    
    # Genera output
    print(f"\n🎨 Generazione visualizzazioni...")
    viz.plot_trajectory_2d(points, path, "Welding Cell Trajectory - Frame Type A", 
                          "outputs/welding_frame_a.png")
    viz.plot_velocity_profile(points, "outputs/welding_velocity.png")
    viz.create_composite_preview(points, path, stats, rapid_code, 
                                "outputs/welding_preview.png")
    
    # Salva RAPID
    with open("outputs/frame_a_program.mod", "w") as f:
        f.write(rapid_code)
    
    print(f"\n✅ Output salvato in /outputs")
    print(f"   - Immagini PNG pronte per portfolio")
    print(f"   - Codice RAPID esportato")
    print(f"   - Dati JSON disponibili per analisi")

if __name__ == "__main__":
    main()

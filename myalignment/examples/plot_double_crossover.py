"""Plot complete idealized DOUBLE crossover centrelines (requires matplotlib).

Run from project root: python examples/plot_double_crossover.py
"""
import math
import matplotlib.pyplot as plt
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.type import TurnoutType, TurnoutSide


def build_main(name, y):
    return (AlignmentBuilder(name)
            .with_pi_coords([(0, y), (1000, y)])
            .with_radii([None, None])
            .as_rail_alignment(gauge=1.435)
            .build())


def main():
    a, b = build_main('본선1', 0), build_main('본선2', 4.3)
    tt = TurnoutType('1/12', 12, 17, 373, 150, 45)
    delta = 2*tt.run + (4.3-2*tt.rise)/math.tan(tt.frog_angle)
    crossover = (CrossoverBuilder('C1')
                 .with_alignments('본선1', '본선2')
                 .with_turnout_type(tt)
                 .at_stations(100, 100+delta)
                 .with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT)
                 .as_double().build())
    geometry = crossover.compute_geometry(a, b)
    if not geometry.is_valid:
        raise ValueError(geometry.error_message)

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot([70, 100+delta+30], [0, 0], color='black', label='Main 1')
    ax.plot([70, 100+delta+30], [4.3, 4.3], color='gray', label='Main 2')
    for path, samples in zip(geometry.paths, geometry.sample_connections(step=0.2)):
        ax.plot([p.x for p in samples], [p.y for p in samples],
                linewidth=2, label=path.name)
        ax.scatter([samples[0].x, samples[-1].x],
                   [samples[0].y, samples[-1].y], s=24)
    ax.set_aspect('equal', adjustable='datalim')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('DOUBLE Crossover — complete idealized centreline')
    ax.grid(True)
    ax.legend()
    plt.show()


if __name__ == '__main__':
    main()

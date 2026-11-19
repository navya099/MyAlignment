"""Integration smoke test against the project's real AlignmentBuilder.
Run after installing project dependencies (notably cadgeom).
"""
import unittest

try:
    from myalignment.alignment.alignment_builder import AlignmentBuilder
    IMPORT_ERROR = None
except ImportError as exc:
    AlignmentBuilder = None
    IMPORT_ERROR = str(exc)

from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.type import TurnoutType, TurnoutSide


@unittest.skipIf(AlignmentBuilder is None, f'AlignmentBuilder dependency unavailable: {IMPORT_ERROR}')
class RealAlignmentIntegration(unittest.TestCase):
    def test_parallel_rail_alignment(self):
        def build(name, y):
            return (AlignmentBuilder(name)
                    .with_pi_coords([(0, y), (1000, y)])
                    .with_radii([None, None])
                    .as_rail_alignment(gauge=1.435)
                    .build())
        a, b = build('본선1', 0), build('본선2', 4.3)
        tt = TurnoutType('1/12', 12, 17, 373, 150, 45)
        delta = 2 * tt.run + (4.3 - 2 * tt.rise) / __import__('math').tan(tt.frog_angle)
        c = (CrossoverBuilder('C1').with_alignments('본선1', '본선2')
             .with_turnout_type(tt).at_stations(100, 100 + delta)
             .with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT).as_double().build())
        g = c.compute_geometry(a, b)
        self.assertTrue(g.is_valid, g.error_message)
        self.assertEqual(len(g.connections), 2)


if __name__ == '__main__':
    unittest.main()

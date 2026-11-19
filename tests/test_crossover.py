import math
import unittest
from dataclasses import dataclass
from myalignment.turnout.type import TurnoutType, TurnoutSide
from myalignment.turnout.crossover_builder import CrossoverBuilder

@dataclass
class Point:
    x: float
    y: float

class Straight:
    def __init__(self, y): self.y = y
    def point_at(self, station):
        if not 0 <= station <= 1000: raise ValueError('station out of range')
        return Point(station, self.y)
    def tangent_at(self, station):
        self.point_at(station)
        return 0.0

class Tests(unittest.TestCase):
    def setUp(self):
        self.tt = TurnoutType('1/12', 12, 17, 373, 150, 45)
        self.a, self.b = Straight(0), Straight(4.3)
        theta = self.tt.frog_angle
        self.delta = 2*self.tt.run + (4.3-2*self.tt.rise)/math.tan(theta)

    def build(self, sta2, kind='single', sides=(TurnoutSide.LEFT, TurnoutSide.RIGHT)):
        b = (CrossoverBuilder('C1').with_alignments('본선1', '본선2')
             .with_turnout_type(self.tt).at_stations(100, sta2)
             .with_sides(*sides))
        if kind == 'double': b.as_double()
        return b.build()

    def test_single_valid(self):
        c = self.build(100+self.delta)
        g = c.compute_geometry(self.a, self.b)
        self.assertTrue(g.is_valid, g.error_message)
        self.assertEqual(len(g.connections), 1)
        self.assertAlmostEqual(g.connecting_length, (4.3-2*self.tt.rise)/math.sin(self.tt.frog_angle), places=4)
        self.assertTrue(c.with_geometry(g).is_valid)

    def test_original_stations_invalid(self):
        g = self.build(120).compute_geometry(self.a, self.b)
        self.assertFalse(g.is_valid)
        self.assertIn('배치 불일치', g.error_message)

    def test_original_sides_invalid(self):
        g = self.build(100+self.delta, sides=(TurnoutSide.RIGHT, TurnoutSide.LEFT)).compute_geometry(self.a, self.b)
        self.assertFalse(g.is_valid)
        self.assertIn('방향', g.error_message)

    def test_double(self):
        c = self.build(100+self.delta, kind='double')
        g = c.compute_geometry(self.a, self.b)
        self.assertTrue(g.is_valid, g.error_message)
        self.assertEqual(len(c.turnouts), 4)
        self.assertEqual(len(g.connections), 2)
        self.assertAlmostEqual(g.connections[0].length, g.connections[1].length)

    def test_scissors_rejected(self):
        b = CrossoverBuilder('C').with_alignments('a','b').with_turnout_type(self.tt).as_scissors()
        with self.assertRaises(NotImplementedError): b.build()

if __name__ == '__main__': unittest.main()

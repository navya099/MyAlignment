from myalignment.turnout.crossover import Crossover
from myalignment.turnout.crossover_type import CrossoverType
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide

class CrossoverBuilder:
    def __init__(self, name='Crossover1'):
        self.name = name
        self.kind = CrossoverType.SINGLE
        self.a1 = self.a2 = ''
        self.tt = None
        self.s1 = self.s2 = 0.0
        self.side1 = self.side2 = None

    def with_alignments(self, align1, align2):
        self.a1, self.a2 = align1, align2
        return self

    def with_turnout_type(self, tt):
        self.tt = tt
        return self

    def at_stations(self, sta1, sta2):
        self.s1, self.s2 = float(sta1), float(sta2)
        return self

    def with_sides(self, left, right):
        # Legacy argument names: left means first turnout, right second turnout.
        self.side1, self.side2 = left, right
        return self

    def as_double(self):
        self.kind = CrossoverType.DOUBLE
        return self

    def as_scissors(self):
        self.kind = CrossoverType.SCISSORS
        return self

    def build(self):
        if self.tt is None or not self.a1 or not self.a2 or self.a1 == self.a2:
            raise ValueError('two different alignments and turnout_type are required')
        if self.kind is CrossoverType.SCISSORS:
            raise NotImplementedError('SCISSORS crossing and slip geometry not implemented')
        side1 = self.side1 or TurnoutSide.LEFT
        side2 = self.side2 or TurnoutSide.RIGHT
        def make(n, source, sta, side, conn):
            return Turnout(f'{self.name}_T{n}', self.tt, source, conn, sta, side)
        t1 = make(1, self.a1, self.s1, side1, f'{self.name}_Conn1')
        t2 = make(2, self.a2, self.s2, side2, f'{self.name}_Conn1')
        extra = ()
        if self.kind is CrossoverType.DOUBLE:
            # Reverse diagonal: upper left to lower right.
            extra = (make(3, self.a2, self.s1, side2, f'{self.name}_Conn2'),
                     make(4, self.a1, self.s2, side1, f'{self.name}_Conn2'))
        return Crossover(name=self.name, crossover_type=self.kind, turnout1=t1, turnout2=t2,
                         additional_turnouts=extra, source_alignment1_name=self.a1,
                         source_alignment2_name=self.a2, connecting_alignment_name=f'{self.name}_Conn1')

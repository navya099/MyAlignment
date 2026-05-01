from myalignment.alignment import Alignment
from autocad.point2d import Point2d
al = Alignment(name='test')
coords = [
        Point2d(0, 0),
        Point2d(100, 0),
        Point2d(150, 50),
        Point2d(546, 1535),
    ]
radii = [50, 30, 40]
al.create(coords, radii)
print(al.summary())
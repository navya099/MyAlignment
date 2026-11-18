from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.boundary import Boundary


surface = (
    TinSurfaceBuilder("계획부지")
    .add_grid(0, 100, 0, 100, nx=51, ny=51,
              elevation_func=lambda x, y: 100 + 0.1 * x)
    .add_outer_boundary(Boundary.rectangle(0, 0, 100, 100, name="부지경계"))
    .add_hide_boundary(Boundary.circle(30, 30, 10, n_segments=32, name="연못"))
    .add_hide_boundary(Boundary.rectangle(60, 60, 80, 80, name="건물"))
    .build()
)

print(f"유효 면적: {surface.area_2d:,.2f} m²")
print(f"경계 내부 (50, 50): {surface.is_inside_boundary(50, 50)}")
print(f"연못 내부 (30, 30): {surface.is_inside_boundary(30, 30)}")
print(f"건물 내부 (70, 70): {surface.is_inside_boundary(70, 70)}")

design = (
    TinSurfaceBuilder("계획고")
    .add_grid(0, 100, 0, 100, nx=51, ny=51, elevation_func=lambda x, y: 98)
    .add_outer_boundary(Boundary.rectangle(0, 0, 100, 100))
    .add_hide_boundary(Boundary.circle(30, 30, 10, n_segments=32))
    .add_hide_boundary(Boundary.rectangle(60, 60, 80, 80))
    .build()
)

cut, fill = surface.volume_between(design)
print(f"\n토공량:")
print(f"  Cut:  {cut:,.1f} m³")
print(f"  Fill: {fill:,.1f} m³")
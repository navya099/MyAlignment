from setuptools import setup, find_packages

setup(
    name="MyAlignment",
    version="0.1",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pyproj",
        "shapely>=2.1,<3",
        "cadgeom @ git+https://github.com/navya099/test.git@67cef7c780e26d9da83277b9731f28b914bef412#subdirectory=AutoCAD",
    ],
)

from setuptools import setup, find_packages

setup(
    name="MyAlignment",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "myautocad>=0.1.0",
        "numpy"
    ],
)

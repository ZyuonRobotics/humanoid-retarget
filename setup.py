from setuptools import find_packages
from distutils.core import setup

setup(
    name='humanoid_retargeting',
    version='1.0.0',
    packages=find_packages(),
    install_requires=['mink', "tqdm", "matplotlib", "pandas", "hurodes"]
)

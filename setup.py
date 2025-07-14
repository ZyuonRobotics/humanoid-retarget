from setuptools import setup, find_packages

setup(
    name="humanoid_retargeting",
    version="1.0.0",
    packages=find_packages(include=["humanoid_retargeting*"]),
    install_requires=[
        "hurodes>=0.0.1",
        "tqdm",
        "matplotlib",
        "pytest-cov",
        "scipy",
        "mink",
    ],
    extras_require={
        'gui': [
            'dearpygui',
        ]
    },
    python_requires=">=3.8",
)
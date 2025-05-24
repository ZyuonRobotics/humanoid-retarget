from setuptools import setup, find_packages

setup(
    name="humanoid_retargeting",
    version="1.0.0",
    packages=find_packages(include=["humanoid_retargeting*"]),
    install_requires=[
        "hurodes>=1.0",
        "tqdm",
        "matplotlib",
        "pytest-cov",
        "scipy",
        "mink",
    ],
    extras_require={
        'all': [
            'dearpygui',
        ]
    },
    python_requires=">=3.8",
)
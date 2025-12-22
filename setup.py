from setuptools import setup, find_packages

setup(
    name="humanoid_retargeting",
    version="1.0.0",
    packages=find_packages(include=["humanoid_retargeting*"]),
    install_requires=[
        "hurodes>=0.0.1",
        "tqdm",
        "matplotlib",
        "scipy",
        "mink",
        "click",
        "pyyaml",
        "pydantic",
    ],
    extras_require={
        'gui': [
            'dearpygui',
        ],
        'dev': [
            "pytest-cov",
        ]
    },
    python_requires=">=3.9",
)
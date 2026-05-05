"""
Setup configuration for Loop Health framework
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="loop-health",
    version="1.0.0",
    author="Nikolaos Angelosoulis",
    author_email="nikolaosang@gmail.com",
    description="Stagnation detection framework for deterministic sequential games",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NikolasAng/loop-health",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Intended Audience :: Science/Engineering",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
        "python-chess>=1.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.10",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
    },
    keywords="games stagnation detection chess artificial-intelligence",
    project_urls={
        "Bug Reports": "https://github.com/NikolasAng/loop-health/issues",
        "Source": "https://github.com/NikolasAng/loop-health",
        "Documentation": "https://github.com/NikolasAng/loop-health/blob/main/README.md",
    },
)

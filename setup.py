from setuptools import setup, find_packages
import jpfm

setup(
    name="jpfm",
    version=jpfm.__version__,
    description="Japanese Dictionary Parser and Flashcard Creator",
    author="cm107",
    packages=find_packages(
            where='.',
            include=['jpfm*']
    ),
    python_requires=">=3.7",  # Modern bindings baseline
    install_requires=[
        "PySide6",            # Primary GUI framework
        "PyYAML",             # For managing config.yaml
        "requests",           # For dictionary web requests
        "beautifulsoup4",     # Recommended for robust HTML parsing
    ],
    extras_require={
        "dev": [
            "pytest>=3.0",     # Baseline testing framework
            "pytest-qt",       # Core GUI testing plugin
            "pytest-xvfb",     # For headless execution on Linux/CI
            "pre-commit",      # For maintaining code style consistency
        ],
    },
    entry_points={
        "console_scripts": [
            "jpfm=main:main",  # Pointing to the main entry point
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

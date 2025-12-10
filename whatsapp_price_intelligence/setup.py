"""
Setup script pour installation du package
"""
from setuptools import setup, find_packages
from pathlib import Path

# Lire le README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="whatsapp-price-intelligence",
    version="0.1.0",
    author="Votre Nom",
    author_email="votre@email.com",
    description="Extraction et analyse de prix du marché porcin depuis WhatsApp",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/votre-username/whatsapp-price-intelligence",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "rich>=13.5.0",
        "python-dateutil>=2.8.2",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
        ],
        "ml": [
            "xgboost>=2.0.0",
            "lightgbm>=4.0.0",
            "statsmodels>=0.14.0",
        ],
        "dashboard": [
            "streamlit>=1.28.0",
            "plotly>=5.17.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "whatsapp-price=main:main",
        ],
    },
)

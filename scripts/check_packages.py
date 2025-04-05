#!/usr/bin/env python
"""
Check for required packages and print missing ones.
"""

import sys

def check_packages():
    """Check for required packages and return a list of missing ones."""
    missing = []
    
    # Check for required packages
    packages = {
        'requests': 'requests',
        'pandas': 'pandas',
        'pybtex': 'pybtex',
        'dotenv': 'python-dotenv',
        'Bio.Entrez': 'biopython'
    }
    
    for module, package in packages.items():
        try:
            __import__(module.split('.')[0])
        except ImportError:
            missing.append(package)
    
    return missing

if __name__ == "__main__":
    missing = check_packages()
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Installing missing packages...")
        sys.exit(1)
    else:
        print("All required packages are installed.")
        sys.exit(0)

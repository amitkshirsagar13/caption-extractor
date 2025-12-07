#!/bin/bash
"""
FastAPI Server Startup Script for Caption Extractor
Usage: python start_api.py [--config config.yml]
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the server
from caption_extractor.api_service import run_server

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run Caption Extractor API Server"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yml",
        help="Path to configuration file (default: config.yml)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Caption Extractor API Server")
    print("=" * 60)
    print(f"Config file: {args.config}")
    print()
    
    run_server(args.config)

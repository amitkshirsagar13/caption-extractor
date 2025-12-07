#!/usr/bin/env python3
"""Run the Caption Extractor API server."""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import caption_extractor
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from caption_extractor.api_service import run_server


def main():
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(
        description="Run Caption Extractor API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.yml",
        help="Path to configuration file (default: config.yml)"
    )
    
    args = parser.parse_args()
    
    # Run the server
    run_server(args.config)


if __name__ == "__main__":
    main()

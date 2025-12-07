#!/usr/bin/env python3
"""
Example script demonstrating how to query performance statistics.

Usage:
    python examples/check_performance.py
"""

import requests
import json
import sys


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))


def main():
    """Query and display performance statistics."""
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("Caption Extractor - Performance Statistics Demo")
    print("=" * 80)
    print()
    
    # 1. Get performance summary
    print("1. Performance Summary")
    print("-" * 80)
    try:
        response = requests.get(f"{base_url}/performance/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"Total Requests: {data.get('total_requests', 0)}")
            print(f"Uptime: {data.get('uptime_seconds', 0):.1f} seconds")
            print(f"Start Time: {data.get('start_time', 'N/A')}")
            print()
            
            for req_type in data.get('request_types', []):
                print(f"  {req_type['request_type'].upper()}: {req_type['total_requests']} requests")
                for model in req_type.get('model_breakdown', []):
                    print(f"    - {model['model']}: {model['count']} requests, "
                          f"avg {model['avg_time']:.2f}s (min: {model['min_time']:.2f}s, "
                          f"max: {model['max_time']:.2f}s)")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server. Is it running?")
        sys.exit(1)
    
    print()
    
    # 2. Get detailed image processing stats
    print("2. Detailed Image Processing Statistics")
    print("-" * 80)
    try:
        response = requests.get(f"{base_url}/performance/image")
        if response.status_code == 200:
            data = response.json()
            print(f"Total Image Requests: {data.get('total_requests', 0)}")
            print()
            
            for model_name, stats in data.get('models', {}).items():
                print(f"  Model: {model_name}")
                print(f"    Requests: {stats['request_count']}")
                print(f"    Total Time: {stats['total_time']:.2f}s")
                print(f"    Average Time: {stats['avg_time']:.2f}s")
                print(f"    Min Time: {stats['min_time']:.2f}s")
                print(f"    Max Time: {stats['max_time']:.2f}s")
                print(f"    Last 5 Requests: {stats['request_times'][-5:]}")
                print()
        else:
            print(f"No image processing data available")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # 3. Get OCR stats
    print("3. OCR Processing Statistics")
    print("-" * 80)
    try:
        response = requests.get(f"{base_url}/performance/ocr")
        if response.status_code == 200:
            data = response.json()
            print(f"Total OCR Requests: {data.get('total_requests', 0)}")
            
            for model_name, stats in data.get('models', {}).items():
                print(f"  Average OCR Time: {stats['avg_time']:.3f}s")
                print(f"  Min Time: {stats['min_time']:.3f}s")
                print(f"  Max Time: {stats['max_time']:.3f}s")
        else:
            print(f"No OCR processing data available")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # 4. Get full statistics (commented out as it can be large)
    # print("4. Full Performance Statistics")
    # print("-" * 80)
    # try:
    #     response = requests.get(f"{base_url}/performance")
    #     if response.status_code == 200:
    #         print_json(response.json())
    # except Exception as e:
    #     print(f"Error: {e}")
    
    print("=" * 80)
    print("For full detailed statistics, visit: http://localhost:8000/performance")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 80)


if __name__ == "__main__":
    main()

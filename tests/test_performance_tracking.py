#!/usr/bin/env python3
"""
Quick test to verify performance tracking is working.
Run this after the API server is started and you've processed some images.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from caption_extractor.performance import PerformanceStatsManager


def test_performance_tracking():
    """Test the performance tracking system."""
    print("=" * 80)
    print("Performance Tracking - Unit Test")
    print("=" * 80)
    print()
    
    # Create a test config
    config = {
        'performance_logging': {
            'enabled': True,
            'log_location': 'logs/performance_test',
            'periodicity_seconds': 60
        }
    }
    
    # Initialize the manager
    print("1. Initializing PerformanceStatsManager...")
    stats_manager = PerformanceStatsManager(config)
    print("   ✓ Initialized successfully")
    print()
    
    # Track some test requests
    print("2. Tracking test requests...")
    
    # Track OCR requests
    stats_manager.track_request('ocr', 'paddleocr', 0.85)
    stats_manager.track_request('ocr', 'paddleocr', 0.92)
    stats_manager.track_request('ocr', 'paddleocr', 0.78)
    print("   ✓ Tracked 3 OCR requests")
    
    # Track image processing requests
    stats_manager.track_request('image', 'qwen3-vl:4b', 15.2)
    stats_manager.track_request('image', 'qwen3-vl:4b', 14.8)
    stats_manager.track_request('image', 'llava:latest', 12.5)
    print("   ✓ Tracked 3 image processing requests (2 models)")
    
    # Track text processing requests
    stats_manager.track_request('text', 'mistral:latest', 2.3)
    stats_manager.track_request('text', 'mistral:latest', 2.5)
    print("   ✓ Tracked 2 text processing requests")
    
    # Track translation request
    stats_manager.track_request('translation', 'mistral:latest', 1.8)
    print("   ✓ Tracked 1 translation request")
    print()
    
    # Get statistics
    print("3. Retrieving statistics...")
    all_stats = stats_manager.get_stats()
    
    print(f"   Total Requests: {all_stats['total_requests']}")
    print(f"   Uptime: {all_stats['uptime_seconds']:.2f}s")
    print()
    
    # Verify request types
    print("4. Verifying request types...")
    expected_types = ['ocr', 'image', 'text', 'translation']
    for req_type in expected_types:
        if req_type in all_stats['request_types']:
            req_stats = all_stats['request_types'][req_type]
            print(f"   ✓ {req_type}: {req_stats['total_requests']} requests")
            for model_name, model_stats in req_stats['models'].items():
                print(f"      - {model_name}: {model_stats['request_count']} requests, "
                      f"avg {model_stats['avg_time']:.2f}s")
        else:
            print(f"   ✗ {req_type}: NOT FOUND")
            return False
    print()
    
    # Test specific request type retrieval
    print("5. Testing specific request type retrieval...")
    ocr_stats = stats_manager.get_stats('ocr')
    print(f"   OCR Stats: {ocr_stats['total_requests']} requests")
    print(f"   Average time: {ocr_stats['models']['paddleocr']['avg_time']:.2f}s")
    print("   ✓ Specific request type retrieval works")
    print()
    
    # Test summary
    print("6. Testing summary generation...")
    summary = stats_manager.get_summary()
    print(f"   Summary contains {len(summary['request_types'])} request types")
    print("   ✓ Summary generation works")
    print()
    
    # Test file saving
    print("7. Testing file saving...")
    stats_manager.save_stats_to_file()
    log_file = Path(config['performance_logging']['log_location']) / 'performance_stats.yml'
    if log_file.exists():
        print(f"   ✓ File saved: {log_file}")
        print(f"   File size: {log_file.stat().st_size} bytes")
    else:
        print(f"   ✗ File not found: {log_file}")
        return False
    print()
    
    # Verify accuracy
    print("8. Verifying calculation accuracy...")
    ocr_model = all_stats['request_types']['ocr']['models']['paddleocr']
    expected_avg = (0.85 + 0.92 + 0.78) / 3
    actual_avg = ocr_model['avg_time']
    if abs(expected_avg - actual_avg) < 0.01:
        print(f"   ✓ Average calculation correct: {actual_avg:.3f}s (expected {expected_avg:.3f}s)")
    else:
        print(f"   ✗ Average calculation incorrect: {actual_avg:.3f}s (expected {expected_avg:.3f}s)")
        return False
    print()
    
    print("=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = test_performance_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

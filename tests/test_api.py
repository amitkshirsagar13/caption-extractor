#!/usr/bin/env python3
"""
Test script for Caption Extractor API.

This script demonstrates how to use the API programmatically.
"""

import requests
import json
import sys
from pathlib import Path


def test_health_check(base_url: str = "http://localhost:8000"):
    """Test the health check endpoint."""
    print("=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/health")
        response.raise_for_status()
        
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Version: {data['version']}")
        print(f"Config Loaded: {data['config_loaded']}")
        print("✓ Health check passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Health check failed: {e}\n")
        return False


def test_get_config(base_url: str = "http://localhost:8000"):
    """Test the configuration endpoint."""
    print("=" * 60)
    print("Testing Configuration Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/config")
        response.raise_for_status()
        
        data = response.json()
        print(json.dumps(data, indent=2))
        print("✓ Configuration retrieved\n")
        return True
        
    except Exception as e:
        print(f"✗ Configuration retrieval failed: {e}\n")
        return False


def test_get_models(base_url: str = "http://localhost:8000"):
    """Test the models endpoint."""
    print("=" * 60)
    print("Testing Models Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/models")
        response.raise_for_status()
        
        data = response.json()
        print("Vision Models:")
        for model in data['vision_models']:
            print(f"  - {model}")
        
        print("\nText Models:")
        for model in data['text_models']:
            print(f"  - {model}")
        
        print(f"\nNote: {data['note']}")
        print("✓ Models information retrieved\n")
        return True
        
    except Exception as e:
        print(f"✗ Models retrieval failed: {e}\n")
        return False


def test_process_image(
    image_path: str,
    base_url: str = "http://localhost:8000",
    enable_ocr: bool = False,
    enable_image_agent: bool = True,
    enable_text_agent: bool = True,
    enable_translation: bool = False,
    vision_model: str = None,
    text_model: str = None
):
    """Test the image processing endpoint."""
    print("=" * 60)
    print("Testing Image Processing Endpoint")
    print("=" * 60)
    
    if not Path(image_path).exists():
        print(f"✗ Image file not found: {image_path}\n")
        return False
    
    try:
        # Prepare the request
        files = {"file": open(image_path, "rb")}
        data = {
            "enable_ocr": enable_ocr,
            "enable_image_agent": enable_image_agent,
            "enable_text_agent": enable_text_agent,
            "enable_translation": enable_translation
        }
        
        if vision_model:
            data["vision_model"] = vision_model
        if text_model:
            data["text_model"] = text_model
        
        print(f"Processing image: {Path(image_path).name}")
        print(f"Settings:")
        print(f"  - OCR: {enable_ocr}")
        print(f"  - Image Agent: {enable_image_agent}")
        print(f"  - Text Agent: {enable_text_agent}")
        print(f"  - Translation: {enable_translation}")
        if vision_model:
            print(f"  - Vision Model: {vision_model}")
        if text_model:
            print(f"  - Text Model: {text_model}")
        print("\nSending request...")
        
        response = requests.post(f"{base_url}/process", files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n" + "=" * 60)
        print("Processing Results")
        print("=" * 60)
        
        print(f"\nImage: {result.get('image_file', 'N/A')}")
        print(f"Processing Time: {result.get('processing_time', 0):.2f}s")
        print(f"Processed At: {result.get('processed_at', 'N/A')}")
        
        # OCR Results
        if result.get('ocr'):
            ocr = result['ocr']
            print(f"\nOCR Results:")
            print(f"  Total Elements: {ocr.get('total_elements', 0)}")
            print(f"  Avg Confidence: {ocr.get('avg_confidence', 0):.2f}")
            if ocr.get('full_text'):
                print(f"  Text: {ocr['full_text'][:100]}...")
        
        # Image Analysis
        if result.get('image_analysis'):
            img_analysis = result['image_analysis']
            print(f"\nImage Analysis:")
            if img_analysis.get('description'):
                print(f"  Description: {img_analysis['description'][:100]}...")
            if img_analysis.get('scene'):
                print(f"  Scene: {img_analysis['scene']}")
        
        # Text Processing
        if result.get('text_processing'):
            text_proc = result['text_processing']
            print(f"\nText Processing:")
            if text_proc.get('corrected_text'):
                print(f"  Corrected: {text_proc['corrected_text'][:100]}...")
            if text_proc.get('confidence'):
                print(f"  Confidence: {text_proc['confidence']}")
        
        # Translation
        if result.get('translation') and result['translation'].get('translated_text'):
            trans = result['translation']
            print(f"\nTranslation:")
            print(f"  Text: {trans['translated_text'][:100]}...")
            print(f"  From: {trans.get('source_language', 'N/A')}")
            print(f"  To: {trans.get('target_language', 'N/A')}")
        
        # Summary
        if result.get('summary'):
            summary = result['summary']
            print(f"\nSummary:")
            print(f"  Total Text Length: {summary.get('total_text_length', 0)}")
            print(f"  Has OCR Data: {summary.get('has_ocr_data', False)}")
            print(f"  Has Image Analysis: {summary.get('has_image_analysis', False)}")
            print(f"  Has Text Processing: {summary.get('has_text_processing', False)}")
        
        print("\n✓ Image processing completed successfully\n")
        
        # Save full result to file
        output_file = f"{Path(image_path).stem}_api_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Full results saved to: {output_file}\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Image processing failed: {e}\n")
        return False


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Caption Extractor API"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to image file to process"
    )
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        help="Enable OCR processing"
    )
    parser.add_argument(
        "--enable-translation",
        action="store_true",
        help="Enable translation"
    )
    parser.add_argument(
        "--vision-model",
        type=str,
        help="Vision model to use"
    )
    parser.add_argument(
        "--text-model",
        type=str,
        help="Text model to use"
    )
    parser.add_argument(
        "--skip-basic-tests",
        action="store_true",
        help="Skip health/config/models tests"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Caption Extractor API Test Suite")
    print("=" * 60)
    print(f"API URL: {args.url}\n")
    
    results = []
    
    # Run basic tests
    if not args.skip_basic_tests:
        results.append(("Health Check", test_health_check(args.url)))
        results.append(("Configuration", test_get_config(args.url)))
        results.append(("Models List", test_get_models(args.url)))
    
    # Run image processing test if image provided
    if args.image:
        results.append((
            "Image Processing",
            test_process_image(
                args.image,
                args.url,
                enable_ocr=args.enable_ocr,
                enable_translation=args.enable_translation,
                vision_model=args.vision_model,
                text_model=args.text_model
            )
        ))
    else:
        print("No image provided. Skipping image processing test.")
        print("Use --image /path/to/image.jpg to test image processing.\n")
    
    # Print summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    print("=" * 60 + "\n")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

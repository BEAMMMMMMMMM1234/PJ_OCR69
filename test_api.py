#!/usr/bin/env python3
"""
Test client for OCR Pipeline API
"""
import sys
from pathlib import Path
import requests
import json


def test_ocr_api(image_path: str, api_url: str = "http://localhost:8000"):
    """
    Upload an image to OCR API and print results
    
    Args:
        image_path: Path to image file
        api_url: Base URL of the API server
    """
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"Error: Image file not found: {image_path}")
        return False
    
    try:
        print(f"📤 Uploading {image_file.name}...")
        
        with open(image_file, "rb") as f:
            files = {"file": (image_file.name, f)}
            response = requests.post(f"{api_url}/ocr/process", files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Document type: {result.get('document_type')}")
            print("\n📋 Result:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error: Cannot reach {api_url}")
        print("   Make sure the API server is running: python3 api.py")
        return False
    except Exception as exc:
        print(f"❌ Error: {exc}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_api.py <image_path> [api_url]")
        print("Example: python3 test_api.py evaluation/appointment/images/A01.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    success = test_ocr_api(image_path, api_url)
    sys.exit(0 if success else 1)

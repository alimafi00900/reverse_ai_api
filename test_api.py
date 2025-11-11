#!/usr/bin/env python3
"""
Simple test script for the OpenAI-compatible reverse API
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_list_models():
    """Test models list endpoint"""
    print("Testing /v1/models endpoint...")
    response = requests.get(f"{BASE_URL}/v1/models")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_get_model():
    """Test get model endpoint"""
    print("Testing /v1/models/gpt-3.5-turbo endpoint...")
    response = requests.get(f"{BASE_URL}/v1/models/gpt-3.5-turbo")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_chat_completions():
    """Test chat completions endpoint"""
    print("Testing /v1/chat/completions endpoint...")
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7
    }
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    try:
        test_health()
        test_list_models()
        test_get_model()
        test_chat_completions()
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running on http://localhost:5000")
    except Exception as e:
        print(f"Error: {e}")


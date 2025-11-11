"""
Provider loader module for loading provider configurations dynamically
"""
import os
import json
import re
from typing import Dict, Optional, Tuple

PROVIDERS_DIR = os.path.join(os.path.dirname(__file__), 'porviders')


def parse_headers(header_text: str) -> Dict[str, str]:
    """
    Parse HTTP headers from header.txt file
    Returns a dictionary of header key-value pairs
    Uses all headers exactly as they appear in the file without any filtering
    """
    headers = {}
    lines = header_text.strip().split('\n')
    
    # Skip the first line (HTTP method and path)
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Use all headers exactly as they are in the file
            headers[key] = value
    
    return headers


def get_provider_path(provider_name: str) -> Optional[str]:
    """
    Get the path to a provider directory
    """
    provider_path = os.path.join(PROVIDERS_DIR, provider_name)
    if os.path.isdir(provider_path):
        return provider_path
    return None


def load_provider_config(provider_name: str) -> Optional[Dict]:
    """
    Load provider configuration from files
    Returns dict with: host, headers, payload_template, response
    """
    provider_path = get_provider_path(provider_name)
    if not provider_path:
        return None
    
    config = {}
    
    # Load metadata.json
    metadata_path = os.path.join(provider_path, 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            config['metadata'] = json.load(f)
    
    # Load header.txt
    header_path = os.path.join(provider_path, 'header.txt')
    if os.path.exists(header_path):
        with open(header_path, 'r', encoding='utf-8') as f:
            header_text = f.read()
            config['headers'] = parse_headers(header_text)
            # Extract path and method from first line
            first_line = header_text.split('\n')[0]
            # Match: METHOD /path?query HTTP/1.1
            match = re.match(r'(\w+)\s+([^\s]+)\s+HTTP', first_line)
            if match:
                config['method'] = match.group(1)
                full_path = match.group(2)
                # Split path and query params
                if '?' in full_path:
                    config['path'] = full_path.split('?')[0]
                    config['query_params'] = full_path.split('?', 1)[1]
                else:
                    config['path'] = full_path
    
    # Load payload.json
    payload_path = os.path.join(provider_path, 'payload.json')
    if os.path.exists(payload_path):
        with open(payload_path, 'r', encoding='utf-8') as f:
            config['payload_template'] = json.load(f)
    
    # Load response.md (for reference, though we'll parse actual responses)
    response_path = os.path.join(provider_path, 'reasponse_example.md')
    if os.path.exists(response_path):
        with open(response_path, 'r', encoding='utf-8') as f:
            config['response'] = f.read()
    
    return config


def determine_provider(model: str, provider: Optional[str] = None) -> Optional[str]:
    """
    Determine provider name from model or explicit provider field
    """
    if provider:
        return provider
    
    # Infer from model name
    model_lower = model.lower()
    if 'qwen' in model_lower:
        return 'qwen'
    
    # Add more inference rules as needed
    # if 'claude' in model_lower:
    #     return 'claude'
    
    return None


def get_available_providers() -> list:
    """
    Get list of available providers
    """
    if not os.path.exists(PROVIDERS_DIR):
        return []
    
    providers = []
    for item in os.listdir(PROVIDERS_DIR):
        provider_path = os.path.join(PROVIDERS_DIR, item)
        if os.path.isdir(provider_path):
            # Check if it has required files
            if os.path.exists(os.path.join(provider_path, 'metadata.json')):
                providers.append(item)
    
    return providers


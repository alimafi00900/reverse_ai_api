from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import os
import requests

app = Flask(__name__)

# Configuration
FORWARD_URL = os.environ.get('FORWARD_URL', None)  # Set to forward requests to another API
FORWARD_API_KEY = os.environ.get('FORWARD_API_KEY', None)  # API key for forwarded requests

# OpenAI-compatible API endpoints

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint
    """
    try:
        data = request.get_json()
        
        # Extract request parameters
        messages = data.get('messages', [])
        model = data.get('model', 'gpt-3.5-turbo')
        temperature = data.get('temperature', 1.0)
        max_tokens = data.get('max_tokens', None)
        stream = data.get('stream', False)
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            return jsonify({
                'error': {
                    'message': 'messages is required and must be a list',
                    'type': 'invalid_request_error',
                    'code': 'missing_messages'
                }
            }), 400
        
        # Forward to another API if configured, otherwise use mock response
        if FORWARD_URL:
            return forward_request(data)
        
        # Generate a mock response
        response_content = generate_mock_response(messages)
        
        # Create OpenAI-compatible response
        response = {
            'id': f'chatcmpl-{uuid.uuid4().hex[:29]}',
            'object': 'chat.completion',
            'created': int(datetime.now().timestamp()),
            'model': model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': response_content
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': count_tokens(str(messages)),
                'completion_tokens': count_tokens(response_content),
                'total_tokens': count_tokens(str(messages)) + count_tokens(response_content)
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': {
                'message': str(e),
                'type': 'server_error',
                'code': 'internal_error'
            }
        }), 500


@app.route('/v1/models', methods=['GET'])
def list_models():
    """
    OpenAI-compatible models list endpoint
    """
    models = [
        {
            'id': 'gpt-4',
            'object': 'model',
            'created': 1677610602,
            'owned_by': 'openai',
            'permission': [],
            'root': 'gpt-4',
            'parent': None
        },
        {
            'id': 'gpt-4-turbo',
            'object': 'model',
            'created': 1692904200,
            'owned_by': 'openai',
            'permission': [],
            'root': 'gpt-4-turbo',
            'parent': None
        },
        {
            'id': 'gpt-3.5-turbo',
            'object': 'model',
            'created': 1677610602,
            'owned_by': 'openai',
            'permission': [],
            'root': 'gpt-3.5-turbo',
            'parent': None
        },
        {
            'id': 'gpt-3.5-turbo-16k',
            'object': 'model',
            'created': 1685474247,
            'owned_by': 'openai',
            'permission': [],
            'root': 'gpt-3.5-turbo-16k',
            'parent': None
        }
    ]
    
    return jsonify({
        'object': 'list',
        'data': models
    })


@app.route('/v1/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """
    OpenAI-compatible model retrieval endpoint
    """
    model = {
        'id': model_id,
        'object': 'model',
        'created': 1677610602,
        'owned_by': 'openai',
        'permission': [],
        'root': model_id,
        'parent': None
    }
    
    return jsonify(model)


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({'status': 'healthy', 'service': 'openai-reverse-api'})


def forward_request(data):
    """
    Forward request to another API endpoint
    """
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key if provided
        if FORWARD_API_KEY:
            headers['Authorization'] = f'Bearer {FORWARD_API_KEY}'
        
        # Forward the request
        response = requests.post(
            FORWARD_URL,
            json=data,
            headers=headers,
            timeout=60
        )
        
        # Return the response from the forwarded API
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': {
                'message': f'Failed to forward request: {str(e)}',
                'type': 'server_error',
                'code': 'forward_error'
            }
        }), 500


def generate_mock_response(messages):
    """
    Generate a mock response based on messages
    In a real implementation, this would forward to another API
    """
    # Simple echo response - you can replace this with actual API forwarding
    last_message = messages[-1] if messages else {}
    user_content = last_message.get('content', '')
    
    # Mock response
    if user_content:
        return f"This is a mock response to: {user_content}"
    return "This is a mock response from the reverse OpenAI API."


def count_tokens(text):
    """
    Simple token counting (approximation)
    In production, use tiktoken or similar library
    """
    # Rough approximation: 1 token ≈ 4 characters
    return len(text) // 4


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


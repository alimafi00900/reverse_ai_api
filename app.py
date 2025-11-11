from flask import Flask, request, jsonify
import os
from provider_loader import determine_provider, get_available_providers
from provider_handler import handle_provider_request

app = Flask(__name__)

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
        provider = data.get('provider', None)  # Explicit provider field
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            return jsonify({
                'error': {
                    'message': 'messages is required and must be a list',
                    'type': 'invalid_request_error',
                    'code': 'missing_messages'
                }
            }), 400
        
        # Determine provider from model or explicit field
        provider_name = determine_provider(model, provider)
        
        # If provider found, use provider system
        if provider_name:
            return handle_provider_request(data, provider_name)
        
        # No provider found - return error
        return jsonify({
            'error': {
                'message': f'No provider found for model "{model}". Please specify a provider or use a supported model.',
                'type': 'invalid_request_error',
                'code': 'provider_not_found'
            }
        }), 400
    
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


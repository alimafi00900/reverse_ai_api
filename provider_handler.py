"""
Provider handler module for making requests to providers and parsing responses
"""
import json
import time
import uuid
import copy
import requests
from typing import Dict, List, Generator, Optional
from flask import Response, stream_with_context
from provider_loader import load_provider_config


def build_provider_messages(openai_messages: List[Dict], payload_template: Dict) -> List[Dict]:
    """
    Convert OpenAI format messages to provider format messages
    Adds timestamps with gaps between messages
    """
    provider_messages = []
    base_timestamp = int(time.time())
    timestamp_gap = 10  # 10 seconds gap between messages
    
    # Get the first message template from payload
    message_template = payload_template.get('messages', [{}])[0] if payload_template.get('messages') else {}
    
    for idx, msg in enumerate(openai_messages):
        # Create a new message based on template (deep copy for nested structures)
        provider_msg = copy.deepcopy(message_template)
        
        # Update role and content
        provider_msg['role'] = msg.get('role', 'user')
        provider_msg['content'] = msg.get('content', '')
        
        # Update timestamp with gap
        if 'timestamp' in provider_msg:
            provider_msg['timestamp'] = base_timestamp + (idx * timestamp_gap)
        
        # Update model if present in template
        if 'models' in provider_msg and payload_template.get('model'):
            provider_msg['models'] = [payload_template['model']]
        
        provider_messages.append(provider_msg)
    
    return provider_messages


def build_provider_payload(openai_data: Dict, provider_config: Dict) -> Dict:
    """
    Build provider payload from OpenAI request data
    """
    payload_template = provider_config['payload_template'].copy()
    
    # Extract OpenAI messages
    openai_messages = openai_data.get('messages', [])
    
    # Convert to provider format
    provider_messages = build_provider_messages(openai_messages, payload_template)
    
    # Update payload
    payload = payload_template.copy()
    payload['messages'] = provider_messages
    
    # Update timestamp
    if 'timestamp' in payload:
        payload['timestamp'] = int(time.time())
    
    # # Update model if specified in OpenAI request
    # if 'model' in openai_data:
    #     payload['model'] = openai_data['model']
    
    # Update stream setting based on metadata (provider's default behavior)
    metadata = provider_config.get('metadata', {})
    provider_streams = metadata.get('stream', True)  # Default to True if not specified
    
    # Use provider's stream setting, but allow override from request if needed
    if 'stream' in payload:
        payload['stream'] = provider_streams
    
    return payload


def parse_sse_line(line: str) -> Optional[Dict]:
    """
    Parse a single SSE (Server-Sent Events) line
    Returns the data as dict if it's a data line, None otherwise
    """
    line = line.strip()
    if line.startswith('data: '):
        data_str = line[6:]  # Remove 'data: ' prefix
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None
    return None


def convert_provider_response_to_openai(provider_data: Dict, model: str, response_id: str) -> Dict:
    """
    Convert provider non-streaming response format to OpenAI format
    """
    # Handle OpenAI-like format
    if 'choices' in provider_data and provider_data['choices']:
        choice = provider_data['choices'][0]
        # Check if it's a message format (non-streaming) or delta format (streaming)
        if 'message' in choice:
            # Already in correct format
            return {
                'id': response_id,
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model,
                'choices': provider_data.get('choices', []),
                'usage': provider_data.get('usage', {})
            }
        elif 'delta' in choice:
            # Streaming format - shouldn't be here, but handle it
            delta = choice['delta']
            return {
                'id': response_id,
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model,
                'choices': [{
                    'index': 0,
                    'message': {
                        'role': delta.get('role', 'assistant'),
                        'content': delta.get('content', '')
                    },
                    'finish_reason': 'stop'
                }],
                'usage': provider_data.get('usage', {})
            }
    
    # Handle provider-specific formats
    # If provider has a 'content' or 'text' field directly
    if 'content' in provider_data:
        return {
            'id': response_id,
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': provider_data['content']
                },
                'finish_reason': 'stop'
            }],
            'usage': provider_data.get('usage', {})
        }
    
    # Default: try to return as-is if it looks like OpenAI format
    if 'object' in provider_data:
        provider_data['id'] = response_id
        return provider_data
    
    return None


def make_provider_request(provider_config: Dict, payload: Dict, stream: bool = True) -> requests.Response:
    """
    Make request to provider API
    """
    metadata = provider_config['metadata']
    headers = provider_config['headers'].copy()
    
    # Build URL
    host = metadata['host']
    path = provider_config.get('path', '/api/v2/chat/completions')
    url = f"https://{host}{path}"
    
    # Add query params if any
    if 'query_params' in provider_config:
        url += f"?{provider_config['query_params']}"
    
    # Make request
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        stream=stream,
        timeout=60
    )
    
    return response


def stream_provider_response(provider_response: requests.Response, model: str, stream_requested: bool) -> Generator:
    """
    Stream provider response and convert to OpenAI format
    Returns generator that yields SSE-formatted strings for streaming, or yields a dict for non-streaming
    """
    response_id = f'chatcmpl-{uuid.uuid4().hex[:29]}'
    accumulated_content = ""
    usage = None
    first_chunk_sent = False
    
    # Parse SSE stream in real-time
    # iter_lines() reads line by line as they arrive from the provider
    for line in provider_response.iter_lines(decode_unicode=True):
        if not line:
            continue
        
        parsed = parse_sse_line(line)
        if not parsed:
            continue
        
        # Skip response.created messages
        if 'response.created' in parsed:
            continue
        
        # Convert to OpenAI format
        if 'choices' in parsed:
            choices = parsed.get('choices', [])
            # Ensure choices array exists and has at least one element
            if choices and len(choices) > 0 and isinstance(choices[0], dict) and 'delta' in choices[0]:
                delta = choices[0]['delta']
                content = delta.get('content', '')
                status = delta.get('status', 'typing')
                
                if content:
                    accumulated_content += content
                
                if stream_requested:
                    # Build delta object - OpenAI format
                    # First chunk should have only 'role', subsequent chunks have 'content'
                    delta_obj = {}
                    
                    # Send role only in the very first chunk
                    if not first_chunk_sent:
                        delta_obj['role'] = 'assistant'
                        # Only include content if not empty
                        if content:
                            delta_obj['content'] = content
                        first_chunk_sent = True
                    else:
                        # Subsequent chunks: only include content
                        delta_obj['content'] = content
                    
                    openai_chunk = {
                        'id': response_id,
                        'object': 'chat.completion.chunk',
                        'created': int(time.time()),
                        'model': model,
                        'choices': [{
                            'index': 0,
                            'delta': delta_obj,
                            'finish_reason': None
                        }]
                    }
                    
                    # Add usage if available
                    if 'usage' in parsed:
                        openai_chunk['usage'] = parsed['usage']
                        usage = parsed['usage']
                    
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                
                # Check if finished
                if status == 'finished':
                    if stream_requested:
                        # Send final chunk
                        final_chunk = {
                            'id': response_id,
                            'object': 'chat.completion.chunk',
                            'created': int(time.time()),
                            'model': model,
                            'choices': [{
                                'index': 0,
                                'delta': {},
                                'finish_reason': 'stop'
                            }]
                        }
                        if usage:
                            final_chunk['usage'] = usage
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                    break
    
    # If not streaming, yield the final result as a dict
    if not stream_requested:
        yield {
            'id': response_id,
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': accumulated_content
                },
                'finish_reason': 'stop'
            }],
            'usage': usage or {}
        }


def handle_provider_request(openai_data: Dict, provider_name: str) -> Response:
    """
    Main handler for provider requests
    """
    # Load provider config
    provider_config = load_provider_config(provider_name)
    if not provider_config:
        from flask import jsonify
        return jsonify({
            'error': {
                'message': f'Provider "{provider_name}" not found',
                'type': 'invalid_request_error',
                'code': 'provider_not_found'
            }
        }), 400
    
    # Build payload
    payload = build_provider_payload(openai_data, provider_config)
    
    # Check metadata to determine if provider uses streaming
    metadata = provider_config.get('metadata', {})
    provider_streams = metadata.get('stream', True)  # Default to True if not specified
    
    model = openai_data.get('model', 'gpt-3.5-turbo')
    
    # Make request with appropriate stream setting based on metadata
    try:
        provider_response = make_provider_request(provider_config, payload, stream=provider_streams)
        provider_response.raise_for_status()
        
        # Determine if response is actually a stream
        # If metadata says stream=false, it's definitely not a stream
        if not provider_streams:
            is_actually_stream = False
        else:
            # Check Content-Type header to verify
            content_type = provider_response.headers.get('Content-Type', '').lower()
            is_actually_stream = 'text/event-stream' in content_type or 'event-stream' in content_type
            
            # If metadata says stream but response isn't actually a stream, check Transfer-Encoding
            if not is_actually_stream:
                transfer_encoding = provider_response.headers.get('Transfer-Encoding', '').lower()
                is_actually_stream = 'chunked' in transfer_encoding
            
            # If still not sure but metadata says stream, trust metadata
            if not is_actually_stream and provider_streams:
                is_actually_stream = True
        
        # If provider returns a stream, always stream it directly to the client
        if is_actually_stream:
            # Return streaming response
            return Response(
                stream_with_context(stream_provider_response(provider_response, model, True)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Provider returned non-streaming response, convert to OpenAI format
            from flask import jsonify
            try:
                response_data = provider_response.json()
                response_id = f'chatcmpl-{uuid.uuid4().hex[:29]}'
                
                # Convert provider response to OpenAI format
                openai_response = convert_provider_response_to_openai(response_data, model, response_id)
                
                if openai_response:
                    return jsonify(openai_response), provider_response.status_code
                else:
                    # If conversion failed, try to return as-is
                    return jsonify(response_data), provider_response.status_code
            except Exception as e:
                return jsonify({
                    'error': {
                        'message': f'Failed to parse provider response: {str(e)}',
                        'type': 'server_error',
                        'code': 'parse_error'
                    }
                }), 500
    
    except requests.exceptions.RequestException as e:
        from flask import jsonify
        return jsonify({
            'error': {
                'message': f'Failed to connect to provider: {str(e)}',
                'type': 'server_error',
                'code': 'provider_error'
            }
        }), 500


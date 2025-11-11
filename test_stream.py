#!/usr/bin/env python3
"""
Test script to verify OpenAI-compatible streaming format
"""
from flask import Flask, Response, stream_with_context
import json
import time

app = Flask(__name__)

@app.route('/test/stream')
def test_stream():
    """
    Test endpoint that returns OpenAI-compatible streaming response
    """
    def generate():
        response_id = "chatcmpl-test123"
        model = "gpt-3.5-turbo"
        created = int(time.time())
        
        # First chunk with role
        chunk1 = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk1)}\n\n"
        
        # Content chunks
        words = ["Hello", " ", "world", "!", " ", "This", " ", "is", " ", "a", " ", "test", "."]
        for word in words:
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": word
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            time.sleep(0.1)  # Simulate streaming delay
        
        # Final chunk
        final_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    print("Test streaming endpoint: http://localhost:5001/test/stream")
    app.run(host='0.0.0.0', port=5001, debug=True)


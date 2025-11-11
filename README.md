# OpenAI-Compatible Reverse API

A Flask-based reverse API that mimics the OpenAI API structure, making it compatible with OpenAI API clients.

## Features

- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ `/v1/models` endpoint for listing available models
- ✅ `/v1/models/<model_id>` endpoint for model details
- ✅ Health check endpoint
- ✅ Proper error handling with OpenAI-style error responses

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start the server:
```bash
python app.py
```

The server will run on `http://localhost:5000` by default.

### Environment Variables

- `PORT`: Port number (default: 5000)
- `FORWARD_URL`: (Optional) URL to forward requests to another API
- `FORWARD_API_KEY`: (Optional) API key for the forwarded API

### Example API Calls

#### Chat Completions
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-xxx" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7
  }'
```

#### List Models
```bash
curl http://localhost:5000/v1/models
```

#### Get Model
```bash
curl http://localhost:5000/v1/models/gpt-3.5-turbo
```

## Forwarding to Another API

To forward requests to another API instead of returning mock responses, set environment variables:

```bash
export FORWARD_URL="https://api.openai.com/v1/chat/completions"
export FORWARD_API_KEY="sk-your-api-key"
python app.py
```

The reverse API will automatically forward all requests to the specified URL and return the response in OpenAI-compatible format.

## License

MIT


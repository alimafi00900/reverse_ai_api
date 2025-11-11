# OpenAI-Compatible Reverse API

A Flask-based reverse API that mimics the OpenAI API structure, making it compatible with OpenAI API clients.

## Features

- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ `/v1/models` endpoint for listing available models
- ✅ `/v1/models/<model_id>` endpoint for model details
- ✅ Health check endpoint
- ✅ Proper error handling with OpenAI-style error responses
- ✅ **Provider system** - Dynamic provider routing based on model/provider
- ✅ **Streaming support** - Full SSE (Server-Sent Events) streaming support
- ✅ **Automatic message conversion** - Converts OpenAI format to provider format

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

## Provider System

The API supports a dynamic provider system that routes requests to different AI providers based on the model or explicit provider field.

### How It Works

1. **Provider Detection**: The API determines the provider from:
   - Explicit `provider` field in the request (e.g., `"provider": "qwen"`)
   - Model name inference (e.g., models containing "qwen" → qwen provider)

2. **Provider Configuration**: Each provider has a folder in `porviders/` containing:
   - `metadata.json` - Provider host/endpoint information
   - `header.txt` - HTTP headers to send with requests
   - `payload.json` - Request payload template
   - `reasponse_example.md` - Example response format (for reference)

3. **Message Conversion**: OpenAI format messages are automatically converted to provider format:
   - Messages are mapped using the template from `payload.json`
   - Timestamps are added with gaps between messages
   - Model information is updated

4. **Streaming**: If the provider returns a stream, it's automatically converted to OpenAI-compatible SSE format

### Using Providers

#### With Explicit Provider Field
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-max-2025-10-30",
    "provider": "qwen",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": true
  }'
```

#### With Model Inference
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-7b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": true
  }'
```

### Adding a New Provider

1. Create a folder in `porviders/` (e.g., `porviders/myprovider/`)
2. Add the required files:
   - `metadata.json`: `{"host": "api.example.com"}`
   - `header.txt`: HTTP headers (first line should be: `METHOD /path HTTP/1.1`)
   - `payload.json`: Request payload template with message structure
   - `reasponse_example.md`: Example response (optional, for reference)
3. Update `provider_loader.py` to recognize your provider in `determine_provider()`

### Error Handling

If no provider is found for a given model, the API will return an error:

```json
{
  "error": {
    "message": "No provider found for model \"model-name\". Please specify a provider or use a supported model.",
    "type": "invalid_request_error",
    "code": "provider_not_found"
  }
}
```

## License

MIT


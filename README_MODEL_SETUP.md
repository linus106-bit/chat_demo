# OpenLab Chat Demo - Model Management Guide

## Overview

The OpenLab Chat Demo now supports easy addition of new models through a configuration-driven architecture. This guide explains how to add new models, customize the interface, and manage model configurations.

## Quick Start: Adding a New Model

### Method 1: Interactive Script (Recommended)

```bash
python3 add_model.py --interactive
```

Follow the prompts to add your model configuration.

### Method 2: Command Line

```bash
python3 add_model.py \
  --key "llama2" \
  --name "Llama-2-7B" \
  --huggingface-id "meta-llama/Llama-2-7b-chat-hf" \
  --avatar "🦙" \
  --generation-type "sequential"
```

### Method 3: Manual Configuration

Edit `config/models.json` directly:

```json
{
  "models": [
    {
      "key": "llama2",
      "name": "Llama-2-7B",
      "display_name": "Llama-2-7B-Chat",
      "huggingface_id": "meta-llama/Llama-2-7b-chat-hf",
      "avatar": "🦙",
      "generation_type": "sequential",
      "enabled": true,
      "demo_folder": "llama2"
    }
  ]
}
```

## Configuration File Structure

### `config/models.json`

This file contains all model and interface configurations:

#### Models Section

```json
{
  "models": [
    {
      "key": "unique_model_key",           // Internal identifier
      "name": "Model Display Name",        // Full model name
      "display_name": "Short Name",       // Name shown in UI
      "huggingface_id": "org/model-name", // HuggingFace model ID
      "avatar": "🤖",                     // Emoji for model avatar
      "generation_type": "sequential",    // "sequential" or "shuffled"
      "enabled": true,                    // Whether to load this model
      "demo_folder": "model_folder"       // Folder name in response/
    }
  ]
}
```

#### Generation Types

- **`sequential`**: Traditional left-to-right token generation
- **`shuffled`**: Diffusion-style generation where tokens appear in random positions

#### Suggestions Section

```json
{
  "suggestions": [
    {
      "key": "suggestion_key",
      "category": "general|correction|extraction",
      "title": "🎯 Button Display Text",
      "prompt": "The actual prompt text sent to models"
    }
  ]
}
```

#### Tabs Section

```json
{
  "tabs": [
    {
      "id": "tab_id",
      "name": "Tab Name",
      "icon": "📝",
      "title": "🎯 Suggestions section title:",
      "active": true
    }
  ]
}
```

## Architecture Overview

### Key Components

1. **`model_manager.py`**: Central model management class
2. **`config/models.json`**: Configuration file
3. **`static/dynamic_script.js`**: Dynamic frontend that loads configuration
4. **`templates/dynamic_index.html`**: Dynamic HTML template
5. **`add_model.py`**: Helper script for adding models

### Model Manager Class

The `ModelManager` class provides:

- Dynamic model loading based on configuration
- Model status tracking
- Configuration management
- Suggestion and tab management

```python
from model_manager import model_manager

# Load all enabled models
model_manager.load_all_models()

# Get model configuration
config = model_manager.get_model_config("model_key")

# Check if model is loaded
is_loaded = model_manager.is_model_loaded("model_key")

# Get prompt from suggestion key
prompt = model_manager.get_prompt_from_suggestion_key("general_suggestion1")
```

## Demo Mode Support

### Adding Demo Responses

1. Create folder: `response/{demo_folder}/`
2. Add JSON files: `{suggestion_key}.json`

Example: `response/llama2/general_suggestion1.json`

```json
{
  "prompt": "Explain quantum computing in simple terms",
  "full_input_ids": [123, 456, 789],
  "full_tokens": ["Quantum", " computing", " is"],
  "total_tokens": 3,
  "steps": [
    {
      "step": 1,
      "prompt": "Explain quantum computing in simple terms",
      "token_index": 1
    }
  ],
  "model_info": {
    "model": "llama2",
    "generation_type": "sequential"
  }
}
```

### Shuffled Generation Format

For diffusion-style models, add `"generation_type": "shuffled"`:

```json
{
  "prompt": "Explain quantum computing",
  "full_input_ids": [123, 456, 789],
  "total_tokens": 3,
  "generation_type": "shuffled",
  "steps": [
    {
      "step": 1,
      "prompt": "Explain quantum computing",
      "filled_positions": [0],
      "total_positions": 3
    }
  ]
}
```

## Frontend Customization

### Dynamic Interface

The frontend automatically:
- Loads model configurations from `/api/config`
- Creates tabs based on configuration
- Builds model panels for each enabled model
- Generates suggestion buttons from configuration

### Adding New Tabs

Add to `config/models.json`:

```json
{
  "tabs": [
    {
      "id": "creative",
      "name": "Creative Writing",
      "icon": "✍️",
      "title": "✍️ Try these creative prompts:",
      "active": false
    }
  ],
  "suggestions": [
    {
      "key": "creative_suggestion1",
      "category": "creative",
      "title": "📝 Write a short story",
      "prompt": "Write a short story about time travel"
    }
  ]
}
```

## API Endpoints

### `/api/config`

Returns complete frontend configuration:

```json
{
  "models": [...],
  "suggestions": [...],
  "tabs": [...]
}
```

### `/chat_stream`

Streaming chat endpoint supporting:
- `message`: Suggestion key or prompt text
- `mode`: Tab category (general, correction, extraction)
- `model`: Model key
- `demo`: Boolean for demo mode

## Testing New Models

1. **Add Model**: Use `add_model.py` or edit config
2. **Restart Server**: `python3 main.py`
3. **Check Health**: `curl http://localhost:8080/health`
4. **Test Interface**: Open web browser to `http://localhost:8080`

## Troubleshooting

### Model Loading Issues

Check server logs for:
- Model download progress
- Memory issues
- Authentication errors (for gated models)

### Configuration Errors

Validate JSON syntax:
```bash
python3 -m json.tool config/models.json
```

### Demo Mode Issues

Ensure:
- Demo folder exists: `response/{demo_folder}/`
- JSON files match suggestion keys
- JSON format is valid

## Best Practices

### Model Selection

- Use appropriate model sizes for your hardware
- Consider generation type based on model capabilities
- Test with demo mode before adding real models

### Configuration Management

- Keep model configurations organized
- Use descriptive keys and names
- Test configuration changes in development

### Performance Optimization

- Enable only needed models
- Use demo mode for testing interface changes
- Monitor memory usage with multiple models

## Examples

### Adding GPT-2

```bash
python3 add_model.py \
  --key "gpt2" \
  --name "GPT-2" \
  --huggingface-id "gpt2" \
  --avatar "🧠" \
  --generation-type "sequential"
```

### Adding FLAN-T5

```bash
python3 add_model.py \
  --key "flan-t5" \
  --name "FLAN-T5-Base" \
  --huggingface-id "google/flan-t5-base" \
  --avatar "🔬" \
  --generation-type "sequential"
```

### Adding Diffusion-Style Model

```bash
python3 add_model.py \
  --key "diffusion-model" \
  --name "Diffusion Text Model" \
  --huggingface-id "some-org/diffusion-text-model" \
  --avatar "🌊" \
  --generation-type "shuffled"
```

This architecture makes it extremely easy to add new models while maintaining a clean, scalable codebase.

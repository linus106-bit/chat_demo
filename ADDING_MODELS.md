# Adding New Models - Quick Guide

## 🚀 Super Simple Model Addition

Adding a new model to OpenLab Chat Demo is now extremely easy! You have 3 simple options:

### Option 1: Interactive Script (Easiest)

```bash
python3 add_model.py --interactive
```

Answer a few questions and you're done! ✨

### Option 2: One Command

```bash
python3 add_model.py \
  --key "gpt2" \
  --name "GPT-2" \
  --huggingface-id "gpt2" \
  --avatar "🧠"
```

### Option 3: Edit Config File

Add to `config/models.json`:

```json
{
  "key": "gpt2",
  "name": "GPT-2", 
  "display_name": "GPT-2",
  "huggingface_id": "gpt2",
  "avatar": "🧠",
  "generation_type": "sequential",
  "enabled": true,
  "demo_folder": "gpt2"
}
```

## What Happens Automatically

When you add a model, the system automatically:

✅ **Updates the configuration**  
✅ **Creates demo folder** (`response/{model_name}/`)  
✅ **Shows in web interface** (no code changes needed!)  
✅ **Loads on server restart**  
✅ **Works with all tabs** (General, Correction, Extraction)  

## Example: Adding GPT-2

```bash
# Step 1: Add the model
python3 add_model.py \
  --key "gpt2" \
  --name "GPT-2" \
  --huggingface-id "gpt2" \
  --avatar "🧠" \
  --generation-type "sequential"

# Step 2: Restart server
python3 main.py

# Step 3: Open browser - GPT-2 appears automatically!
```

## Example: Adding Llama-2

```bash
# Add Llama-2 with llama emoji
python3 add_model.py \
  --key "llama2" \
  --name "Llama-2-7B-Chat" \
  --huggingface-id "meta-llama/Llama-2-7b-chat-hf" \
  --avatar "🦙"
```

## Demo Mode (Optional)

To support demo mode, add JSON files to `response/{model_name}/`:

- `general_suggestion1.json`
- `correction_suggestion1.json`  
- `extraction_suggestion1.json`
- etc.

See existing files in `response/smollm/` for format examples.

## That's It! 🎉

No need to:
- ❌ Edit HTML templates
- ❌ Modify JavaScript code  
- ❌ Update CSS styles
- ❌ Change routing logic
- ❌ Rebuild the interface

The system is **fully dynamic** and handles everything automatically based on your configuration!

## Architecture Benefits

- **🔧 Config-Driven**: Everything controlled by `config/models.json`
- **🎨 Dynamic Frontend**: Interface builds itself from configuration
- **📦 Self-Contained**: Each model is independent  
- **🛡️ Robust**: Fallbacks for missing configurations
- **🚀 Scalable**: Add unlimited models easily

## Full Documentation

See `README_MODEL_SETUP.md` for complete documentation, troubleshooting, and advanced features.

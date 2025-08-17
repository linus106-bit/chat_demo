from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
import torch
import json
import os
import asyncio
import markdown
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

import threading
import queue

# Import model manager
from model_manager import model_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for loading and unloading models"""
    # Startup: Load models
    print("🚀 Starting OpenLab Chat Demo...")
    
    # Load all enabled models using model manager
    load_results = model_manager.load_all_models()
    
    if all(load_results.values()):
        print("🎉 All models loaded successfully!")
    else:
        failed_models = [model for model, success in load_results.items() if not success]
        print(f"⚠️  Some models failed to load: {failed_models}")
    
    print("🎉 OpenLab Chat Demo started successfully!")
    
    yield
    
    # Shutdown: Clean up models
    print("🛑 Shutting down OpenLab Chat Demo...")
    model_manager.unload_all_models()
    print("✅ Models cleaned up successfully")

app = FastAPI(
    title="OpenLab Chat Demo", 
    description="A modern chat demo with dual SmolLM models",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

class CustomTextStreamer(TextStreamer):
    """Custom text streamer that yields tokens as they're generated"""
    def __init__(self, tokenizer, skip_prompt=True):
        super().__init__(tokenizer, skip_prompt=skip_prompt)
        self.token_queue = queue.Queue()
        self.finished = False
        
    def on_finalized_text(self, text: str, stream_end: bool = False):
        """Called when text is finalized (after each token)"""
        if text and not stream_end:
            self.token_queue.put(text)
        if stream_end:
            self.finished = True
            self.token_queue.put(None)  # Sentinel value
    
    def get_tokens(self):
        """Generator that yields tokens as they become available"""
        while True:
            try:
                token = self.token_queue.get(timeout=0.1)
                if token is None:  # End of generation
                    break
                yield token
            except queue.Empty:
                if self.finished:
                    break
                continue

def generate_response(prompt: str, model_key: str, mode: str = "general") -> str:
    """Generate response using the specified model and mode"""
    model_info = model_manager.get_loaded_model(model_key)
    
    if model_info["model"] is None or model_info["tokenizer"] is None:
        # Mock response for demo purposes
        return f"I'm a demo version of {model_info['name']}. In a full implementation, I would process your message: " + prompt[:100] + "..."
    
    try:
        tokenizer = model_info["tokenizer"]
        model = model_info["model"]
        
        # Create system prompt based on mode
        system_prompts = {
            "general": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to any questions or tasks.",
            "correction": "You are a text correction specialist. Your task is to correct grammar, spelling, punctuation, and improve the clarity of the given text. Return only the corrected version without explanations unless specifically asked.",
            "extraction": "You are a key-value extraction specialist. Extract important information from the given text and present it as key-value pairs in a structured format. Focus on names, dates, numbers, addresses, and other significant data points."
        }
        
        system_prompt = system_prompts.get(mode, system_prompts["general"])
        
        # Create chat messages for the template
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize the formatted prompt
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        input_length = inputs.input_ids.shape[1]
        
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                attention_mask=inputs.attention_mask if 'attention_mask' in inputs else None
            )
        
        # Decode only the new tokens (response part)
        response_tokens = outputs[0][input_length:]
        response = tokenizer.decode(response_tokens, skip_special_tokens=True)
        
        return response.strip()
    
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def generate_streaming_response(prompt: str, model_key: str, mode: str = "general"):
    """Generate streaming response using the specified model and mode"""
    model_info = model_manager.get_loaded_model(model_key)
    
    if model_info["model"] is None or model_info["tokenizer"] is None:
        # Mock streaming for demo purposes
        demo_text = f"I'm a demo version of {model_info['name']}. In a full implementation, I would process your message: {prompt[:100]}..."
        for word in demo_text.split():
            yield word + " "
            import time
            time.sleep(0.1)  # Simulate streaming delay
        return
    
    try:
        tokenizer = model_info["tokenizer"]
        model = model_info["model"]
        
        # Create system prompt based on mode
        system_prompts = {
            "general": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to any questions or tasks.",
            "correction": "You are a text correction specialist. Your task is to correct grammar, spelling, punctuation, and improve the clarity of the given text. Return only the corrected version without explanations unless specifically asked.",
            "extraction": "You are a key-value extraction specialist. Extract important information from the given text and present it as key-value pairs in a structured format. Focus on names, dates, numbers, addresses, and other significant data points."
        }
        
        system_prompt = system_prompts.get(mode, system_prompts["general"])
        
        # Create chat messages for the template
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize the formatted prompt
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        
        # Create custom streamer
        streamer = CustomTextStreamer(tokenizer, skip_prompt=True)
        
        # Generate in a separate thread
        def generate():
            with torch.no_grad():
                model.generate(
                    inputs.input_ids,
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    attention_mask=inputs.attention_mask if 'attention_mask' in inputs else None,
                    streamer=streamer
                )
            streamer.on_finalized_text("", stream_end=True)
        
        # Start generation in background thread
        generation_thread = threading.Thread(target=generate)
        generation_thread.start()
        
        # Yield tokens as they become available
        for token in streamer.get_tokens():
            yield token
        
        # Wait for generation to complete
        generation_thread.join()
        
    except Exception as e:
        yield f"Sorry, I encountered an error: {str(e)}"

def get_actual_prompt(key: str) -> str:
    """Get actual prompt text from model manager or fallback"""
    # First try to get prompt from model manager configuration
    prompt = model_manager.get_prompt_from_suggestion_key(key)
    if prompt:
        return prompt
    
    # Fallback: try to get from JSON file
    prompt_from_file = get_prompt_from_json(key)
    if prompt_from_file:
        return prompt_from_file
    
    # Final fallback: return the key itself
    return key

def get_prompt_from_json(key: str) -> str:
    """Try to get prompt text from JSON file"""
    # Map keys to file names
    file_mapping = {
        'general_suggestion1': 'general_suggestion1.json',
        'general_suggestion2': 'general_suggestion2.json',
        'general_suggestion3': 'general_suggestion3.json',
        'general_suggestion4': 'general_suggestion4.json',
        'correction_suggestion1': 'correction_suggestion1.json',
        'correction_suggestion2': 'correction_suggestion2.json',
        'correction_suggestion3': 'correction_suggestion3.json',
        'correction_suggestion4': 'correction_suggestion4.json',
        'extraction_suggestion1': 'extraction_suggestion1.json',
        'extraction_suggestion2': 'extraction_suggestion2.json',
        'extraction_suggestion3': 'extraction_suggestion3.json',
        'extraction_suggestion4': 'extraction_suggestion4.json',
    }
    
    filename = file_mapping.get(key)
    if not filename:
        return None
    
    # Try to read prompt from any model's JSON file (they should be the same)
    for model_key in ['smollm2', 'smollm']:
        try:
            filepath = f"response/{model_key}/{filename}"
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data.get('prompt')
        except:
            continue
    
    return None

def generate_demo_streaming_response(prompt: str, mode: str, model_key: str):
    """Generate demo streaming response from pre-saved JSON files using input_ids"""
    import time
    
    # Get model configuration
    model_config = model_manager.get_model_config(model_key)
    if not model_config:
        # Fallback response if model not found
        fallback_text = f"Demo response for {model_key}: {prompt[:50]}..."
        for word in fallback_text.split():
            yield word + " "
            time.sleep(0.1)
        return
    
    # Get demo folder from model config
    demo_folder = model_config.get("demo_folder", model_key)
    
    # Try to find JSON file for this suggestion
    filename = f"{prompt}.json"
    print(f"DEBUG: Looking for file: {filename}")
    if not filename:
        # Fallback response if prompt doesn't match
        fallback_text = f"Demo response for {model_key}: {prompt[:50]}..."
        for word in fallback_text.split():
            yield word + " "
            time.sleep(0.1)
        return
    
    try:
        # Load the JSON file from model-specific folder
        filepath = f"response/{demo_folder}/{filename}"
        with open(filepath, 'r') as f:
            steps = json.load(f)
        
        # Get the tokenizer for this model
        model_info = model_manager.get_loaded_model(model_key)
        tokenizer = model_info.get("tokenizer")
        print(f"DEBUG: Model info for {model_key}: {model_info}")
        print(f"DEBUG: Tokenizer available: {tokenizer is not None}")
        
        # Check if this is the new JSON format (array of turns)
        if isinstance(steps, list) and len(steps) > 0:
            # New multiturn format - array of conversation turns
            # Use the first turn (index 0) for initial generation
            turn_data = steps[0]  # Use first turn for initial generation
            print(f"DEBUG: Using multiturn format, first turn from {filepath}")
            
            if isinstance(turn_data, dict) and "full_input_ids" in turn_data and "steps" in turn_data:
                full_input_ids = turn_data["full_input_ids"]
                full_tokens = turn_data["full_tokens"]
                step_list = turn_data["steps"]
                generation_type = turn_data.get("generation_type", "sequential")
                print(f"DEBUG: Turn data loaded - {len(full_input_ids)} tokens, {len(step_list)} steps, type: {generation_type}")
                
                # Handle generation for new format
                if not tokenizer:
                    print(f"DEBUG: No tokenizer available, using fallback")
                    fallback_text = f"Demo response for {model_key}: {prompt[:50]}..."
                    for word in fallback_text.split():
                        yield word + " "
                        time.sleep(0.1)
                    return
                
                if generation_type == "shuffled":
                    print(f"DEBUG: Starting shuffled generation with {len(step_list)} steps")
                    # Shuffled generation
                    for step in step_list:
                        filled_positions = step["filled_positions"]
                        total_positions = len(full_input_ids)
                        
                        response_parts = []
                        for pos in range(total_positions):
                            token_text = tokenizer.decode([full_input_ids[pos]], skip_special_tokens=True)
                            
                            if pos in filled_positions:
                                response_parts.append(token_text)
                            else:
                                blank_space = " " * len(token_text)
                                response_parts.append(blank_space)
                        
                        current_response = "".join(response_parts)
                        print(f"DEBUG: Generated shuffled response: '{current_response}'")
                        yield f"__SHUFFLED_UPDATE__{current_response}"
                        time.sleep(0.03)
                else:
                    print(f"DEBUG: Starting sequential generation with {len(step_list)} steps")
                    # Sequential generation
                    last_token_index = 0
                    for step in step_list:
                        current_token_index = step["token_index"]
                        
                        if current_token_index > last_token_index:
                            new_token_ids = full_input_ids[last_token_index:current_token_index]
                            
                            for token_id in new_token_ids:
                                token_text = tokenizer.decode([token_id], skip_special_tokens=True)
                                if token_text:
                                    yield token_text
                                    time.sleep(0.03)
                        
                        last_token_index = current_token_index
                return  # Exit after processing first turn
            else:
                # Fallback to old format
                full_input_ids = steps["full_input_ids"]
                full_tokens = steps["full_tokens"]
                step_list = steps["steps"]
                generation_type = steps.get("generation_type", "sequential")
                print(f"DEBUG: Fallback to old format from {filepath}")
        
        elif isinstance(steps, dict) and "full_input_ids" in steps and "steps" in steps:
            # Old format with single object
            full_input_ids = steps["full_input_ids"]
            full_tokens = steps["full_tokens"]
            step_list = steps["steps"]
            generation_type = steps.get("generation_type", "sequential")
        
        # Handle generation based on type (for both new and old formats)
        if not tokenizer:
                # Fallback to text-based streaming if no tokenizer available
                last_response = ""
                for step in step_list:
                    response = step["response"]
                    if len(response) > len(last_response):
                        new_part = response[len(last_response):]
                        if new_part:
                            yield new_part
                            time.sleep(0.05)
                    last_response = response
                return
            
        if generation_type == "shuffled":
            # Shuffled (diffusion-style) generation - build response from input_ids and positions
            print(f"DEBUG: Starting shuffled generation with {len(step_list)} steps")
            for step in step_list:
                filled_positions = step["filled_positions"]
                total_positions = len(full_input_ids)
                
                # Build response text using only filled positions
                response_parts = []
                for pos in range(total_positions):
                    # Always decode the token to get its exact length
                    token_text = tokenizer.decode([full_input_ids[pos]], skip_special_tokens=True)
                    
                    if pos in filled_positions:
                        # Position is filled - use the actual decoded token
                        response_parts.append(token_text)
                    else:
                        # Position is unfilled - use blank spaces with exact token length
                        blank_space = " " * len(token_text)
                        response_parts.append(blank_space)
                
                # Join all parts to create the complete response
                current_response = "".join(response_parts)
                print(f"DEBUG: Generated shuffled response: '{current_response}'")
                
                # Send the complete response as a single update
                yield f"__SHUFFLED_UPDATE__{current_response}"
                time.sleep(0.03)  # Same speed as sequential generation
        else:
            # Sequential generation - stream using token indices
            last_token_index = 0
            for step in step_list:
                current_token_index = step["token_index"]
                
                # Calculate new tokens to add (from last_token_index to current_token_index)
                if current_token_index > last_token_index:
                    new_token_ids = full_input_ids[last_token_index:current_token_index]
                    
                    # Convert new token IDs to text
                    for token_id in new_token_ids:
                        token_text = tokenizer.decode([token_id], skip_special_tokens=True)
                        if token_text:
                            yield token_text
                            time.sleep(0.03)  # Slightly faster for token-by-token
                
                last_token_index = current_token_index
        
    except Exception as e:
        yield f"Demo error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config")
async def get_config():
    """Get frontend configuration including models, suggestions, and tabs"""
    return {
        "models": model_manager.get_enabled_models(),
        "suggestions": model_manager.config["suggestions"],
        "tabs": model_manager.get_tabs()
    }

@app.get("/chat_stream")
async def chat_stream(message: str, mode: str = "general", model: str = "smollm2", demo: bool = False):
    """Stream chat response for a single model"""
    def stream_generator():
        try:
            if demo:
                # Use demo responses from JSON files
                for token in generate_demo_streaming_response(message, mode, model):
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            else:
                # Map internal key to actual prompt text for real model generation
                prompt_text = get_actual_prompt(message)
                
                # Use real model generation with actual prompt text
                for token in generate_streaming_response(prompt_text, model, mode):
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.get("/remask_stream")
async def remask_stream(suggestion: str, turn: int = 1, mode: str = "correction", model: str = "smollm"):
    """Stream remask response for a specific turn from JSON files"""
    def stream_generator():
        try:
            # Get model configuration
            model_config = model_manager.get_model_config(model)
            if not model_config:
                yield f"data: {json.dumps({'error': 'Model not found', 'done': True})}\n\n"
                return
            
            # Get demo folder from model config
            demo_folder = model_config.get("demo_folder", model)
            
            # Load the JSON file
            filepath = f"response/{demo_folder}/{suggestion}.json"
            print(f"Loading remask file: {filepath}")
            with open(filepath, 'r') as f:
                turns_data = json.load(f)
            print(f"Loaded turns data: {len(turns_data) if isinstance(turns_data, list) else 'not a list'}")
            
            # Check if the requested turn exists
            print(f"Requested turn: {turn}, Available turns: {len(turns_data) if isinstance(turns_data, list) else 'not a list'}")
            if not isinstance(turns_data, list) or turn >= len(turns_data):
                error_msg = f'Turn {turn} not available'
                print(f"Error: {error_msg}")
                yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"
                return
            
            # Get the specific turn data
            turn_data = turns_data[turn]
            
            # Get the tokenizer for this model
            model_info = model_manager.get_loaded_model(model)
            tokenizer = model_info.get("tokenizer")
            
            print(f"Model info: {model_info}")
            print(f"Tokenizer available: {tokenizer is not None}")
            
            if not tokenizer:
                error_msg = 'Tokenizer not available'
                print(f"Error: {error_msg}")
                yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"
                return
            
            # Generate streaming response for this specific turn
            full_input_ids = turn_data["full_input_ids"]
            full_tokens = turn_data["full_tokens"]
            step_list = turn_data["steps"]
            generation_type = turn_data.get("generation_type", "sequential")
            
            import time
            
            if generation_type == "shuffled":
                # Shuffled generation for this turn
                for step in step_list:
                    filled_positions = step["filled_positions"]
                    total_positions = len(full_input_ids)
                    
                    # Build response text using only filled positions
                    response_parts = []
                    for pos in range(total_positions):
                        token_text = tokenizer.decode([full_input_ids[pos]], skip_special_tokens=True)
                        
                        if pos in filled_positions:
                            response_parts.append(token_text)
                        else:
                            blank_space = " " * len(token_text)
                            response_parts.append(blank_space)
                    
                    current_response = "".join(response_parts)
                    yield f"data: {json.dumps({'token': f'__SHUFFLED_UPDATE__{current_response}', 'done': False})}\n\n"
                    time.sleep(0.03)
            else:
                # Sequential generation for this turn
                last_token_index = 0
                for step in step_list:
                    current_token_index = step["token_index"]
                    
                    if current_token_index > last_token_index:
                        new_token_ids = full_input_ids[last_token_index:current_token_index]
                        
                        for token_id in new_token_ids:
                            token_text = tokenizer.decode([token_id], skip_special_tokens=True)
                            if token_text:
                                yield f"data: {json.dumps({'token': token_text, 'done': False})}\n\n"
                                time.sleep(0.03)
                    
                    last_token_index = current_token_index
            
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "models": model_manager.get_model_status()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

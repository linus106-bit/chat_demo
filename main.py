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

# Global variables for models
models = {
    "smollm2": {"model": None, "tokenizer": None, "name": "SmolLM2-135M-Instruct"},
    "smollm": {"model": None, "tokenizer": None, "name": "SmolLM-135M-Instruct"}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for loading and unloading models"""
    # Startup: Load models
    print("Loading SmolLM models...")
    
    # Load SmolLM2-135M-Instruct
    try:
        print("Loading SmolLM2-135M-Instruct...")
        model_name = "HuggingFaceTB/SmolLM2-135M-Instruct"
        models["smollm2"]["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
        models["smollm2"]["model"] = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype='auto',
            trust_remote_code=True
        )
        print("SmolLM2-135M-Instruct loaded successfully!")
    except Exception as e:
        print(f"Error loading SmolLM2-135M-Instruct: {e}")
        models["smollm2"]["model"] = None
        models["smollm2"]["tokenizer"] = None

    # Load SmolLM-135M-Instruct
    try:
        print("Loading SmolLM-135M-Instruct...")
        model_name = "HuggingFaceTB/SmolLM-135M-Instruct"
        models["smollm"]["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
        models["smollm"]["model"] = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype='auto',
            trust_remote_code=True
        )
        print("SmolLM-135M-Instruct loaded successfully!")
    except Exception as e:
        print(f"Error loading SmolLM-135M-Instruct: {e}")
        models["smollm"]["model"] = None
        models["smollm"]["tokenizer"] = None
    
    yield
    
    # Shutdown: Clean up models
    print("Shutting down models...")
    for model_key in models:
        if models[model_key]["model"] is not None:
            del models[model_key]["model"]
            models[model_key]["model"] = None
        if models[model_key]["tokenizer"] is not None:
            del models[model_key]["tokenizer"]
            models[model_key]["tokenizer"] = None
    print("Models cleaned up successfully!")

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
    model_info = models[model_key]
    
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
    model_info = models[model_key]
    
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
    """Get actual prompt text from JSON file or fallback to hardcoded mapping"""
    # First try to get prompt from JSON file
    prompt_from_file = get_prompt_from_json(key)
    if prompt_from_file:
        return prompt_from_file
    
    # Fallback to hardcoded mapping
    prompt_map = {
        # General Chat
        'general_suggestion1': 'Explain quantum computing in simple terms',
        'general_suggestion2': 'Write a Python function to calculate fibonacci numbers',
        'general_suggestion3': 'What are the benefits of renewable energy?',
        'general_suggestion4': 'How do I start learning machine learning?',
        
        # Correction
        'correction_suggestion1': 'I cant beleive its already december and i havent finished my homwork yet.',
        'correction_suggestion2': 'Their going to there house to get they\'re things.',
        'correction_suggestion3': 'The meeting will be held on Monday, Wenesday, and friday at 3pm.',
        'correction_suggestion4': 'Please find attached the documents you requested. I hope this helps with you\'re project.',
        
        # Extraction
        'extraction_suggestion1': 'John Doe, 123 Main Street, New York, NY 10001, Phone: (555) 123-4567, Email: john.doe@email.com, DOB: 01/15/1985',
        'extraction_suggestion2': 'Invoice #INV-2024-001, Date: March 15, 2024, Total: $1,234.56, Customer: ABC Corp, Items: 5x Laptops ($200 each), 3x Monitors ($150 each)',
        'extraction_suggestion3': 'Meeting scheduled for January 20, 2024 at 2:30 PM EST. Attendees: Sarah Johnson (Manager), Mike Chen (Developer), Lisa Park (Designer). Location: Conference Room B, Duration: 90 minutes',
        'extraction_suggestion4': 'Company: TechStart LLC, Founded: 2020, CEO: David Wilson, Revenue: $2.5M, Employees: 45, Address: 456 Tech Plaza, San Francisco, CA 94105'
    }
    
    # Return mapped prompt or the original key if no mapping found
    return prompt_map.get(key, key)

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
    
    # Map simple keys to their corresponding JSON files for each model
    prompt_to_file = {
        "smollm2": {
            # General Chat suggestions
            "general_suggestion1": "general_suggestion1.json",
            "general_suggestion2": "general_suggestion2.json", 
            "general_suggestion3": "general_suggestion3.json",
            "general_suggestion4": "general_suggestion4.json",
            
            # Correction suggestions
            "correction_suggestion1": "correction_suggestion1.json",
            "correction_suggestion2": "correction_suggestion2.json",
            "correction_suggestion3": "correction_suggestion3.json",
            "correction_suggestion4": "correction_suggestion4.json",
            
            # Extraction suggestions
            "extraction_suggestion1": "extraction_suggestion1.json",
            "extraction_suggestion2": "extraction_suggestion2.json",
            "extraction_suggestion3": "extraction_suggestion3.json",
            "extraction_suggestion4": "extraction_suggestion4.json"
        },
        "smollm": {
            # General Chat suggestions
            "general_suggestion1": "general_suggestion1.json",
            "general_suggestion2": "general_suggestion2.json", 
            "general_suggestion3": "general_suggestion3.json",
            "general_suggestion4": "general_suggestion4.json",
            
            # Correction suggestions
            "correction_suggestion1": "correction_suggestion1.json",
            "correction_suggestion2": "correction_suggestion2.json",
            "correction_suggestion3": "correction_suggestion3.json",
            "correction_suggestion4": "correction_suggestion4.json",
            
            # Extraction suggestions
            "extraction_suggestion1": "extraction_suggestion1.json",
            "extraction_suggestion2": "extraction_suggestion2.json",
            "extraction_suggestion3": "extraction_suggestion3.json",
            "extraction_suggestion4": "extraction_suggestion4.json"
        }
    }
    
    # Find the matching file for this prompt and model
    model_prompts = prompt_to_file.get(model_key, {})
    filename = model_prompts.get(prompt)
    if not filename:
        # Fallback response if prompt doesn't match
        fallback_text = f"Demo response for {model_key}: {prompt[:50]}..."
        for word in fallback_text.split():
            yield word + " "
            time.sleep(0.1)
        return
    
    try:
        # Load the JSON file from model-specific folder
        filepath = f"response/{model_key}/{filename}"
        with open(filepath, 'r') as f:
            steps = json.load(f)
        
        # Get the tokenizer for this model
        model_info = models.get(model_key, {})
        tokenizer = model_info.get("tokenizer")
        
        # Check if this is the new JSON format
        if isinstance(steps, dict) and "full_input_ids" in steps and "steps" in steps:
            # New format with full_input_ids and token indices
            full_input_ids = steps["full_input_ids"]
            full_tokens = steps["full_tokens"]
            step_list = steps["steps"]
            generation_type = steps.get("generation_type", "sequential")
            
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
        
        else:
            # Legacy format - fallback for old JSON structure
            if not tokenizer:
                # Fallback to text-based streaming if no tokenizer available
                last_response = ""
                for step in steps:
                    if isinstance(step, dict) and "response" in step:
                        response = step["response"]
                        if len(response) > len(last_response):
                            new_part = response[len(last_response):]
                            if new_part:
                                yield new_part
                                time.sleep(0.05)
                        last_response = response
                return
            
            # Stream using input_ids - each step represents new tokens to add (legacy)
            last_input_ids = []
            for step in steps:
                if isinstance(step, dict) and "tokenization" in step:
                    current_input_ids = step["tokenization"]["input_ids"]
                    
                    # Calculate new tokens to add (difference from previous step)
                    if len(current_input_ids) > len(last_input_ids):
                        new_token_ids = current_input_ids[len(last_input_ids):]
                        
                        # Convert new token IDs to text
                        for token_id in new_token_ids:
                            token_text = tokenizer.decode([token_id], skip_special_tokens=True)
                            if token_text:
                                yield token_text
                                time.sleep(0.03)  # Slightly faster for token-by-token
                    
                    last_input_ids = current_input_ids
            
    except Exception as e:
        yield f"Demo error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "models": {
            "smollm2": {"loaded": models["smollm2"]["model"] is not None, "name": models["smollm2"]["name"]},
            "smollm": {"loaded": models["smollm"]["model"] is not None, "name": models["smollm"]["name"]}
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

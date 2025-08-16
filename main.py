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
from concurrent.futures import ThreadPoolExecutor
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

# Thread pool for concurrent model execution
executor = ThreadPoolExecutor(max_workers=2)

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

def generate_demo_streaming_response(prompt: str, mode: str, model_key: str):
    """Generate demo streaming response from pre-saved JSON files using input_ids"""
    import time
    
    # Map prompts to their corresponding JSON files for each model
    prompt_to_file = {
        "smollm2": {
            # General Chat suggestions
            "Explain quantum computing in simple terms": "general_suggestion1.json",
            "Write a Python function to calculate fibonacci numbers": "general_suggestion2.json", 
            "What are the benefits of renewable energy?": "general_suggestion3.json",
            "How do I start learning machine learning?": "general_suggestion4.json",
            
            # Correction suggestions
            "I cant beleive its already december and i havent finished my homwork yet.": "correction_suggestion1.json",
            "Their going to there house to get they're things.": "correction_suggestion2.json",
            "The meeting will be held on Monday, Wenesday, and friday at 3pm.": "correction_suggestion3.json",
            "Please find attached the documents you requested. I hope this helps with you're project.": "correction_suggestion4.json",
            
            # Extraction suggestions
            "John Doe, 123 Main Street, New York, NY 10001, Phone: (555) 123-4567, Email: john.doe@email.com, DOB: 01/15/1985": "extraction_suggestion1.json",
            "Invoice #INV-2024-001, Date: March 15, 2024, Total: $1,234.56, Customer: ABC Corp, Items: 5x Laptops ($200 each), 3x Monitors ($150 each)": "extraction_suggestion2.json",
            "Meeting scheduled for January 20, 2024 at 2:30 PM EST. Attendees: Sarah Johnson (Manager), Mike Chen (Developer), Lisa Park (Designer). Location: Conference Room B, Duration: 90 minutes": "extraction_suggestion3.json",
            "Company: TechStart LLC, Founded: 2020, CEO: David Wilson, Revenue: $2.5M, Employees: 45, Address: 456 Tech Plaza, San Francisco, CA 94105": "extraction_suggestion4.json"
        },
        "smollm": {
            # General Chat suggestions
            "Explain quantum computing in simple terms": "general_suggestion1.json",
            "Write a Python function to calculate fibonacci numbers": "general_suggestion2.json", 
            "What are the benefits of renewable energy?": "general_suggestion3.json",
            "How do I start learning machine learning?": "general_suggestion4.json",
            
            # Correction suggestions
            "I cant beleive its already december and i havent finished my homwork yet.": "correction_suggestion1.json",
            "Their going to there house to get they're things.": "correction_suggestion2.json",
            "The meeting will be held on Monday, Wenesday, and friday at 3pm.": "correction_suggestion3.json",
            "Please find attached the documents you requested. I hope this helps with you're project.": "correction_suggestion4.json",
            
            # Extraction suggestions
            "John Doe, 123 Main Street, New York, NY 10001, Phone: (555) 123-4567, Email: john.doe@email.com, DOB: 01/15/1985": "extraction_suggestion1.json",
            "Invoice #INV-2024-001, Date: March 15, 2024, Total: $1,234.56, Customer: ABC Corp, Items: 5x Laptops ($200 each), 3x Monitors ($150 each)": "extraction_suggestion2.json",
            "Meeting scheduled for January 20, 2024 at 2:30 PM EST. Attendees: Sarah Johnson (Manager), Mike Chen (Developer), Lisa Park (Designer). Location: Conference Room B, Duration: 90 minutes": "extraction_suggestion3.json",
            "Company: TechStart LLC, Founded: 2020, CEO: David Wilson, Revenue: $2.5M, Employees: 45, Address: 456 Tech Plaza, San Francisco, CA 94105": "extraction_suggestion4.json"
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
                # Shuffled (diffusion-style) generation - send complete response for each step
                for step in step_list:
                    # Get the current response (which shows filled positions)
                    current_response = step["response"]
                    
                    # Send the complete response as a single update
                    # This creates the diffusion effect where text appears/changes in different positions
                    yield f"__SHUFFLED_UPDATE__{current_response}"
                    time.sleep(0.15)  # Slower update for diffusion effect visualization
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

async def generate_response_async(prompt: str, model_key: str, mode: str = "general") -> str:
    """Async wrapper for generate_response to run in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_response, prompt, model_key, mode)

@app.post("/chat")
async def chat(message: str = Form(...), mode: str = Form("general")):
    """Handle chat messages and return responses from both models simultaneously"""
    try:
        # Generate responses from both models concurrently
        smollm2_task = generate_response_async(message, "smollm2", mode)
        smollm_task = generate_response_async(message, "smollm", mode)
        
        # Wait for both responses to complete simultaneously
        smollm2_response, smollm_response = await asyncio.gather(smollm2_task, smollm_task)
        
        # Convert responses to HTML using markdown
        smollm2_html = markdown.markdown(smollm2_response, extensions=['fenced_code', 'tables', 'nl2br'])
        smollm_html = markdown.markdown(smollm_response, extensions=['fenced_code', 'tables', 'nl2br'])
        
        return {
            "responses": {
                "smollm2": {
                    "text": smollm2_response,
                    "html": smollm2_html
                },
                "smollm": {
                    "text": smollm_response,
                    "html": smollm_html
                }
            },
            "mode": mode,
            "status": "success"
        }
    except Exception as e:
        return {"responses": {"smollm2": f"Error: {str(e)}", "smollm": f"Error: {str(e)}"}, "status": "error"}

@app.post("/chat_single")
async def chat_single(message: str = Form(...), mode: str = Form("general"), model: str = Form(...)):
    """Handle chat message for a single model"""
    try:
        # Generate response from specified model
        response = await generate_response_async(message, model, mode)
        
        # Convert response to HTML using markdown
        response_html = markdown.markdown(response, extensions=['fenced_code', 'tables', 'nl2br'])
        
        return {
            "response": {
                "text": response,
                "html": response_html
            },
            "model": model,
            "mode": mode,
            "status": "success"
        }
    except Exception as e:
        return {"response": {"text": f"Error: {str(e)}", "html": f"Error: {str(e)}"}, "status": "error"}

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
                # Use real model generation
                for token in generate_streaming_response(message, model, mode):
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

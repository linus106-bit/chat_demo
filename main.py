from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import json
import os
import asyncio
import markdown
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import threading

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

# Removed AsyncTextStreamer class - using simpler direct streaming approach

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
        input_length = inputs.input_ids.shape[1]
        
        # Simple streaming approach: generate tokens one by one
        with torch.no_grad():
            generated_ids = inputs.input_ids.clone()
            last_text = ""
            
            for _ in range(512):  # max_new_tokens
                # Get next token
                outputs = model(generated_ids)
                next_token_logits = outputs.logits[0, -1, :]
                
                # Sample next token
                next_token_logits = next_token_logits / 0.7  # temperature
                probs = torch.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                # Check if we hit the end token
                if next_token.item() == tokenizer.eos_token_id:
                    break
                
                # Append the new token
                generated_ids = torch.cat([generated_ids, next_token.unsqueeze(0)], dim=-1)
                
                # Decode and yield the new token
                new_text = tokenizer.decode(generated_ids[0][input_length:], skip_special_tokens=True)
                if len(new_text) > len(last_text):
                    new_part = new_text[len(last_text):]
                    last_text = new_text
                    if new_part:
                        yield new_part
        
    except Exception as e:
        yield f"Sorry, I encountered an error: {str(e)}"

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
async def chat_stream(message: str, mode: str = "general", model: str = "smollm2"):
    """Stream chat response for a single model"""
    def stream_generator():
        try:
            for token in generate_streaming_response(message, model, mode):
                # Send token as Server-Sent Event
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
            # Send completion signal
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

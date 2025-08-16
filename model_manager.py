"""
Model Manager - Handles dynamic model loading and configuration
"""

import json
import os
from typing import Dict, List, Optional, Any
from transformers import AutoTokenizer, AutoModelForCausalLM


class ModelManager:
    """Manages model loading, configuration, and metadata"""
    
    def __init__(self, config_path: str = "config/models.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.loaded_models = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Model configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def get_enabled_models(self) -> List[Dict[str, Any]]:
        """Get list of enabled models from configuration"""
        return [model for model in self.config["models"] if model.get("enabled", True)]
    
    def get_model_config(self, model_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model"""
        for model in self.config["models"]:
            if model["key"] == model_key:
                return model
        return None
    
    def get_suggestions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get suggestions for a specific category"""
        return [suggestion for suggestion in self.config["suggestions"] 
                if suggestion["category"] == category]
    
    def get_suggestion(self, suggestion_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific suggestion by key"""
        for suggestion in self.config["suggestions"]:
            if suggestion["key"] == suggestion_key:
                return suggestion
        return None
    
    def get_tabs(self) -> List[Dict[str, Any]]:
        """Get tab configuration"""
        return self.config["tabs"]
    
    def load_model(self, model_key: str) -> bool:
        """Load a specific model"""
        model_config = self.get_model_config(model_key)
        if not model_config:
            print(f"❌ Model configuration not found: {model_key}")
            return False
        
        if model_key in self.loaded_models:
            print(f"⏭️  Model already loaded: {model_key}")
            return True
        
        try:
            print(f"🔄 Loading {model_config['name']}...")
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_config["huggingface_id"])
            model = AutoModelForCausalLM.from_pretrained(model_config["huggingface_id"])
            
            # Add pad token if it doesn't exist
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Store loaded model
            self.loaded_models[model_key] = {
                "tokenizer": tokenizer,
                "model": model,
                "config": model_config,
                "loaded": True,
                "name": model_config["name"]
            }
            
            print(f"✅ Successfully loaded {model_config['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading {model_config['name']}: {str(e)}")
            return False
    
    def load_all_models(self) -> Dict[str, bool]:
        """Load all enabled models"""
        results = {}
        enabled_models = self.get_enabled_models()
        
        for model_config in enabled_models:
            model_key = model_config["key"]
            results[model_key] = self.load_model(model_key)
        
        return results
    
    def unload_model(self, model_key: str) -> bool:
        """Unload a specific model"""
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            print(f"🗑️  Unloaded model: {model_key}")
            return True
        return False
    
    def unload_all_models(self):
        """Unload all models"""
        for model_key in list(self.loaded_models.keys()):
            self.unload_model(model_key)
    
    def is_model_loaded(self, model_key: str) -> bool:
        """Check if a model is loaded"""
        return model_key in self.loaded_models and self.loaded_models[model_key].get("loaded", False)
    
    def get_loaded_model(self, model_key: str) -> Optional[Dict[str, Any]]:
        """Get loaded model data"""
        return self.loaded_models.get(model_key)
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        status = {}
        for model_config in self.config["models"]:
            model_key = model_config["key"]
            status[model_key] = {
                "loaded": self.is_model_loaded(model_key),
                "name": model_config["name"],
                "enabled": model_config.get("enabled", True)
            }
        return status
    
    def get_prompt_from_suggestion_key(self, suggestion_key: str) -> Optional[str]:
        """Get the actual prompt text from a suggestion key"""
        suggestion = self.get_suggestion(suggestion_key)
        return suggestion["prompt"] if suggestion else None
    
    def add_model(self, model_config: Dict[str, Any]) -> bool:
        """Add a new model to the configuration"""
        # Validate required fields
        required_fields = ["key", "name", "huggingface_id", "avatar", "generation_type"]
        for field in required_fields:
            if field not in model_config:
                raise ValueError(f"Missing required field: {field}")
        
        # Add default values
        model_config.setdefault("enabled", True)
        model_config.setdefault("display_name", model_config["name"])
        model_config.setdefault("demo_folder", model_config["key"])
        
        # Add to configuration
        self.config["models"].append(model_config)
        
        # Save configuration
        return self._save_config()
    
    def _save_config(self) -> bool:
        """Save configuration back to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False


# Global model manager instance
model_manager = ModelManager()

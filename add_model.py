#!/usr/bin/env python3
"""
Script to easily add a new model to the OpenLab Chat Demo
"""

import argparse
import json
import os
import sys
from model_manager import ModelManager

def add_new_model():
    """Interactive script to add a new model"""
    print("🤖 OpenLab Chat Demo - Add New Model")
    print("=" * 50)
    
    # Get model information
    key = input("Model key (e.g., 'gpt2'): ").strip()
    if not key:
        print("❌ Model key is required")
        return False
    
    name = input("Model name (e.g., 'GPT-2'): ").strip()
    if not name:
        print("❌ Model name is required")
        return False
    
    huggingface_id = input("HuggingFace model ID (e.g., 'gpt2'): ").strip()
    if not huggingface_id:
        print("❌ HuggingFace model ID is required")
        return False
    
    avatar = input("Avatar emoji (e.g., '🎯'): ").strip()
    if not avatar:
        avatar = "🤖"
    
    print("\nGeneration types:")
    print("1. sequential - Traditional left-to-right generation")
    print("2. shuffled - Diffusion-style random position generation")
    generation_choice = input("Choose generation type (1 or 2): ").strip()
    
    if generation_choice == "1":
        generation_type = "sequential"
    elif generation_choice == "2":
        generation_type = "shuffled"
    else:
        print("❌ Invalid choice. Using 'sequential' as default.")
        generation_type = "sequential"
    
    enabled = input("Enable model by default? (y/n) [y]: ").strip().lower()
    enabled = enabled != 'n'
    
    demo_folder = input(f"Demo folder name [{key}]: ").strip()
    if not demo_folder:
        demo_folder = key
    
    # Create model configuration
    model_config = {
        "key": key,
        "name": name,
        "display_name": name,
        "huggingface_id": huggingface_id,
        "avatar": avatar,
        "generation_type": generation_type,
        "enabled": enabled,
        "demo_folder": demo_folder
    }
    
    # Show summary
    print("\n📋 Model Configuration Summary:")
    print(f"Key: {key}")
    print(f"Name: {name}")
    print(f"HuggingFace ID: {huggingface_id}")
    print(f"Avatar: {avatar}")
    print(f"Generation Type: {generation_type}")
    print(f"Enabled: {enabled}")
    print(f"Demo Folder: {demo_folder}")
    
    confirm = input("\nAdd this model? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Model addition cancelled")
        return False
    
    try:
        # Add model using model manager
        model_manager = ModelManager()
        model_manager.add_model(model_config)
        
        print(f"✅ Model '{name}' added successfully!")
        
        # Create demo folder if it doesn't exist
        demo_path = f"response/{demo_folder}"
        if not os.path.exists(demo_path):
            os.makedirs(demo_path)
            print(f"📁 Created demo folder: {demo_path}")
            print(f"💡 Add demo JSON files to {demo_path}/ for demo mode support")
        
        print("\n🎉 Model added successfully!")
        print("\n📝 Next steps:")
        print(f"1. Add demo response files to 'response/{demo_folder}/' (optional)")
        print("2. Restart the application to load the new model")
        print("3. The model will appear automatically in the web interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding model: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Add a new model to OpenLab Chat Demo')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='Run in interactive mode')
    parser.add_argument('--key', help='Model key')
    parser.add_argument('--name', help='Model name')
    parser.add_argument('--huggingface-id', help='HuggingFace model ID')
    parser.add_argument('--avatar', help='Avatar emoji', default='🤖')
    parser.add_argument('--generation-type', choices=['sequential', 'shuffled'], 
                       default='sequential', help='Generation type')
    parser.add_argument('--enabled', action='store_true', default=True, 
                       help='Enable model by default')
    parser.add_argument('--demo-folder', help='Demo folder name')
    
    args = parser.parse_args()
    
    if args.interactive or len(sys.argv) == 1:
        # Interactive mode
        success = add_new_model()
        sys.exit(0 if success else 1)
    else:
        # Command line mode
        if not all([args.key, args.name, args.huggingface_id]):
            print("❌ Error: --key, --name, and --huggingface-id are required")
            sys.exit(1)
        
        model_config = {
            "key": args.key,
            "name": args.name,
            "display_name": args.name,
            "huggingface_id": args.huggingface_id,
            "avatar": args.avatar,
            "generation_type": args.generation_type,
            "enabled": args.enabled,
            "demo_folder": args.demo_folder or args.key
        }
        
        try:
            model_manager = ModelManager()
            model_manager.add_model(model_config)
            print(f"✅ Model '{args.name}' added successfully!")
            
            # Create demo folder
            demo_path = f"response/{model_config['demo_folder']}"
            if not os.path.exists(demo_path):
                os.makedirs(demo_path)
                print(f"📁 Created demo folder: {demo_path}")
            
        except Exception as e:
            print(f"❌ Error adding model: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()

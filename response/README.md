# Demo Response Files Structure

This directory contains the demo response files organized by model for the offline demo mode.

## Folder Structure

```
response/
├── smollm2/          # SmolLM2-135M-Instruct demo responses
│   ├── general_suggestion1.json
│   ├── general_suggestion2.json
│   ├── general_suggestion3.json
│   ├── general_suggestion4.json
│   ├── correction_suggestion1.json
│   ├── correction_suggestion2.json
│   ├── correction_suggestion3.json
│   ├── correction_suggestion4.json
│   ├── extraction_suggestion1.json
│   ├── extraction_suggestion2.json
│   ├── extraction_suggestion3.json
│   └── extraction_suggestion4.json
├── smollm/           # SmolLM-135M-Instruct demo responses
│   ├── general_suggestion1.json
│   ├── general_suggestion2.json
│   ├── general_suggestion3.json
│   ├── general_suggestion4.json
│   ├── correction_suggestion1.json
│   ├── correction_suggestion2.json
│   ├── correction_suggestion3.json
│   ├── correction_suggestion4.json
│   ├── extraction_suggestion1.json
│   ├── extraction_suggestion2.json
│   ├── extraction_suggestion3.json
│   └── extraction_suggestion4.json
└── shared/           # Shared/common demo files (if any)
```

## File Format

Each JSON file contains the complete token sequence and streaming steps with token indices:

### Sequential Generation Format (SmolLM2):
```json
{
    "full_input_ids": [48021, 7867, 314, 253, 11951, 1835],
    "full_tokens": ["Quantum", "Ġcomputing", "Ġis", "Ġa", "Ġrevolutionary", "Ġtechnology"],
    "total_tokens": 6,
    "steps": [
        {
            "step": 1,
            "prompt": "The original prompt",
            "response": "Quantum",
            "token_index": 1
        },
        {
            "step": 2,
            "prompt": "The original prompt", 
            "response": "Quantum computing",
            "token_index": 2
        }
        // ... more steps
    ],
    "model_info": { /* model metadata */ }
}
```

### Shuffled Generation Format (SmolLM):
```json
{
    "full_input_ids": [48021, 7867, 314, 253, 11951, 1835],
    "full_tokens": ["Quantum", "Ġcomputing", "Ġis", "Ġa", "Ġrevolutionary", "Ġtechnology"],
    "total_tokens": 6,
    "generation_type": "shuffled",
    "steps": [
        {
            "step": 1,
            "prompt": "The original prompt",
            "filled_positions": [0],
            "total_positions": 6
        },
        {
            "step": 2,
            "prompt": "The original prompt",
            "filled_positions": [0, 3],
            "total_positions": 6
        }
        // ... more steps with random token positions
    ],
    "model_info": { /* model metadata */ }
}
```

**Note**: Shuffled responses are generated dynamically from `full_input_ids` and `filled_positions` - no pre-computed response text is stored.

**Technical Implementation**:
```python
for pos in range(total_positions):
    token_text = tokenizer.decode([full_input_ids[pos]], skip_special_tokens=True)
    if pos in filled_positions:
        response_parts.append(token_text)  # Actual token
    else:
        response_parts.append(" " * len(token_text))  # Exact-length blank space
```

## Usage

- **Demo Mode**: When demo mode is enabled, the system loads responses from these files
- **Model-Specific**: Each model uses its own folder for different response styles
- **Token-Based Streaming**: Responses are streamed using actual input_ids for realistic token-by-token generation
- **Generation Types**: 
  - **Sequential** (SmolLM2): Traditional left-to-right token generation (0.03s per step)
  - **Shuffled** (SmolLM): Diffusion-style generation where tokens appear in random positions (0.03s per step)
    - Uses blank spaces (`" " * len(decoded_token)`) for unfilled token positions
    - Responses generated dynamically from `input_ids` and `filled_positions`
    - Maintains exact token-length spacing throughout generation
    - Special purple styling in UI to distinguish from sequential generation
    - Same speed as sequential generation for consistent user experience
- **Offline**: Works without requiring actual model loading
- **Fallback**: If tokenizer is unavailable, falls back to text-based streaming

## Adding New Demos

1. Create new JSON files in the appropriate model folder
2. Follow the step-by-step format
3. Update the `prompt_to_file` mapping in `main.py` to match the exact prompts from the HTML template
4. Test with the demo mode toggle

## Current Prompt Mappings

### General Chat
- "Explain quantum computing in simple terms" → `general_suggestion1.json`
- "Write a Python function to calculate fibonacci numbers" → `general_suggestion2.json`
- "What are the benefits of renewable energy?" → `general_suggestion3.json`
- "How do I start learning machine learning?" → `general_suggestion4.json`

### Correction
- "I cant beleive its already december and i havent finished my homwork yet." → `correction_suggestion1.json`
- "Their going to there house to get they're things." → `correction_suggestion2.json`
- "The meeting will be held on Monday, Wenesday, and friday at 3pm." → `correction_suggestion3.json`
- "Please find attached the documents you requested. I hope this helps with you're project." → `correction_suggestion4.json`

### Extraction
- "John Doe, 123 Main Street, New York, NY 10001, Phone: (555) 123-4567, Email: john.doe@email.com, DOB: 01/15/1985" → `extraction_suggestion1.json`
- "Invoice #INV-2024-001, Date: March 15, 2024, Total: $1,234.56, Customer: ABC Corp, Items: 5x Laptops ($200 each), 3x Monitors ($150 each)" → `extraction_suggestion2.json`
- "Meeting scheduled for January 20, 2024 at 2:30 PM EST. Attendees: Sarah Johnson (Manager), Mike Chen (Developer), Lisa Park (Designer). Location: Conference Room B, Duration: 90 minutes" → `extraction_suggestion3.json`
- "Company: TechStart LLC, Founded: 2020, CEO: David Wilson, Revenue: $2.5M, Employees: 45, Address: 456 Tech Plaza, San Francisco, CA 94105" → `extraction_suggestion4.json`

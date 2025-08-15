# OpenLab Chat Demo - Dual SmolLM Models

A modern chat demo website built with FastAPI featuring **two SmolLM models side by side** for easy comparison. The design is inspired by [Llama.com](https://www.llama.com/) with a clean, modern interface.

## Features

- 🤖 **Dual SmolLM Models**: Compare responses from both SmolLM2-135M-Instruct and SmolLM-135M-Instruct
- 🎨 **Modern UI**: Llama.com-inspired design with gradient backgrounds and glass effects
- 📱 **Responsive Design**: Works perfectly on desktop and mobile devices
- ⚡ **FastAPI Backend**: High-performance Python backend with async support
- 🔄 **Real-time Chat**: Smooth chat experience with loading states
- 🎯 **Side-by-side Comparison**: Easily compare responses from both models
- 📊 **Model Status Indicators**: Real-time status for each model

## Screenshots

The application features:
- Beautiful gradient background
- Glass-morphism design elements
- **Dual chat panels** for side-by-side model comparison
- Clean chat interface with user/assistant avatars
- Real-time model status indicators for both models
- Responsive layout that stacks on mobile devices

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Sufficient RAM (recommended 8GB+) for running two models

### Setup

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Open your browser** and navigate to:
   ```
   http://localhost:8080
   ```

## Usage

1. **Start a conversation**: Type your message in the input field
2. **Send messages**: Press Enter or click the send button
3. **Compare responses**: Both models will respond to the same question side by side
4. **Multi-line messages**: Use Shift+Enter for new lines
5. **Monitor model status**: Check the status indicators in each panel header

## API Endpoints

- `GET /`: Main chat interface with dual panels
- `POST /chat`: Send a message and get responses from both models
- `GET /health`: Check application and model status for both models

## Model Information

This demo uses **two SmolLM models** from HuggingFace:

### SmolLM2-135M-Instruct
- **Model**: `HuggingFaceTB/SmolLM2-135M-Instruct`
- **Size**: 135M parameters
- **Type**: Instruction-tuned language model
- **Capabilities**: Text generation, conversation, coding assistance

### SmolLM-135M-Instruct
- **Model**: `HuggingFaceTB/SmolLM-135M-Instruct`
- **Size**: 135M parameters
- **Type**: Instruction-tuned language model
- **Capabilities**: Text generation, conversation, coding assistance

## Development

### Project Structure

```
openlab_demo/
├── main.py              # FastAPI application with dual model support
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html      # Main HTML template with dual chat panels
├── static/
│   ├── styles.css      # CSS styles for dual panel layout
│   └── script.js       # JavaScript functionality for dual models
└── README.md           # This file
```

### Customization

- **Styling**: Modify `static/styles.css` to change the appearance
- **Functionality**: Edit `static/script.js` for frontend behavior
- **Backend**: Update `main.py` for server-side changes
- **Models**: Add or change models in the `load_models()` function

## Troubleshooting

### Model Loading Issues

If the models fail to load:
1. Check your internet connection
2. Ensure you have sufficient disk space (~1GB for both models)
3. Verify Python and PyTorch versions are compatible
4. The app will show demo mode if models can't be loaded

### Performance

- Both models load on startup and may take 1-2 minutes
- First responses may be slower due to model initialization
- Consider using GPU acceleration for better performance
- Monitor memory usage when running two models simultaneously

### Memory Requirements

- **Minimum**: 4GB RAM
- **Recommended**: 8GB+ RAM
- **GPU**: Optional but recommended for faster inference

## License

This project is for demonstration purposes. The SmolLM models are subject to their own license terms.

## Contributing

Feel free to submit issues and enhancement requests!

---

Built with ❤️ using FastAPI and dual SmolLM models

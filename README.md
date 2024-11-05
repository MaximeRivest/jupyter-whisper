# JupyterWhisper - AI-Powered Chat Interface for Jupyter Notebooks

JupyterWhisper transforms your Jupyter notebook environment by seamlessly integrating Claude AI capabilities. This extension enables natural chat interactions, intelligent code execution, and voice command features to enhance your notebook workflow.

## ✨ Key Features

- 🤖 Native integration with Claude 3.5 Sonnet
- 🎯 Intelligent code execution and cell management 
- 🔍 Advanced search capabilities powered by Perplexity AI
- 🎙️ Voice command support using OpenAI Whisper
- 📝 Context-aware text processing and formatting
- 💬 Comprehensive chat history management
- ⚡ Real-time streaming responses

## 🚀 Installation

```bash
pip install jupyter_whisper
```
## 📋 Requirements

- Python 3.7+
- JupyterLab 4.0+ (important: this extension is designed for JupyterLab, not classic Notebook)
- Jupyter Notebook 7.0+ (if using Notebook instead of Lab)
- Required API keys:
  - Anthropic API key (for Claude integration)
  - OpenAI API key (optional, for voice features) 
  - Perplexity API key (for advanced search capabilities)

### Installation Steps

1. Install JupyterLab if you haven't already:
```bash
pip install jupyterlab>=4.0.0
```

2. Install Jupyter Whisper:
```bash
pip install jupyter_whisper
```

3. Start JupyterLab:
```bash
jupyter lab
```

### Important Note About Server Management

Jupyter Whisper runs a local FastAPI server (on port 5000) to handle features like audio transcription and text processing. The server is shared between notebooks for efficiency.

**Important Notes:**
- The server persists between notebook sessions
- Configuration changes (like API keys) only take effect when the server restarts
- You'll be notified if you're using an older server version

To manually refresh the server and apply new configurations:

```python
from jupyter_whisper import refresh_jupyter_whisper
refresh_jupyter_whisper()  # Warning: affects all active notebooks
```

**When to refresh:**
- After updating API keys
- After upgrading the package
- If you encounter configuration issues

Note: Refreshing the server will impact all notebooks currently using it. You may need to restart kernels in affected notebooks.

### JupyterLab Compatibility

JupyterWhisper is specifically designed and tested for JupyterLab 4.0+. While it may work in classic Jupyter Notebook (7.0+), we recommend using JupyterLab for the best experience and full feature support.

Key compatibility notes:
- Voice features require a modern browser
- WebSocket support is required for real-time streaming
- Some features may require JupyterLab extensions to be enabled
- Port 5000 must be available for the local server

## 🔧 Configuration

### Interactive Setup

The easiest way to configure Jupyter Whisper is through the interactive setup interface:

```python
import jupyter_whisper
```

This will open an interactive UI with tabs for:
- API Keys configuration
- Model selection
- System prompt customization

### Manual Configuration

You can also configure settings programmatically:

```python
from jupyter_whisper.config import get_config_manager
config = get_config_manager()

# Set API keys
config.set_api_key('ANTHROPIC_API_KEY', 'your-key-here')
config.set_api_key('OPENAI_API_KEY', 'your-key-here')      # Optional for voice
config.set_api_key('PERPLEXITY_API_KEY', 'your-key-here')  # For search

# Change the model
config.set_model('claude-3-5-sonnet-20241022')

# Update system prompt
config.set_system_prompt("Your custom system prompt here")

# Set other preferences
config.set_config_value('SKIP_SETUP_POPUP', True)
```

Available models:
- claude-3-5-sonnet-20241022
- claude-3-5-haiku-20241022
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

## 💡 Usage

### Basic Chat

Interact with the AI using the `%%user` magic command:

```python
%%user
How do I read a CSV file using pandas?
```

### Online Search

Access web information directly within your notebook:

```python
from jupyter_whisper import search_online
style = "Be precise and concise"
question = "What's new in Python 3.12?"
search_online(style, question)
```

### Voice Commands

Leverage voice input capabilities:
- Control recording with keyboard shortcuts
- Automatic speech-to-text conversion
- Seamless chat interface integration

## 🛠️ Advanced Features

### Magic Commands

- `%%user [index]` - Initiate a user message
- `%%user [index]:set` - Replace user message at given index
- `%%assistant [index]` - Include assistant response
- `%%assistant [index]:set` - Replace assistant message at given index
- `%%assistant [index]:add` - Concatenate content to existing assistant message

Example usage:
```python
%%user 3:set
How do I read a CSV file?

%%assistant 3:set
Here's how to read a CSV file using pandas:
import pandas as pd
df = pd.read_csv('file.csv')

%%assistant 3:add
You can also specify additional parameters:
df = pd.read_csv('file.csv', encoding='utf-8')
```

## 🔧 Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/jupyter_whisper.git
cd jupyter_whisper
pip install -e ".[dev]"
```

## 🤝 Contributing

We welcome contributions! Please submit your Pull Requests.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Credits

Powered by:
- [Claude](https://anthropic.com/claude) by Anthropic
- [OpenAI Whisper](https://openai.com/research/whisper)
- [Perplexity AI](https://perplexity.ai)

---

Made with ❤️ by Maxime

*Note: This project is independent and not affiliated with Anthropic, OpenAI, or Perplexity AI.*
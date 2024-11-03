# JupyterChat - AI-Powered Chat Interface for Jupyter Notebooks

JupyterChat transforms your Jupyter notebook environment by seamlessly integrating Claude AI capabilities. This extension enables natural chat interactions, intelligent code execution, and voice command features to enhance your notebook workflow.

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
pip install jupyterchat
```

## 📋 Requirements

- Python 3.7+
- Jupyter Notebook
- Anthropic API key (for Claude integration)
- OpenAI API key (optional, for voice features)

## 🏁 Quick Start

1. Configure your API keys:

```bash
export ANTHROPIC_API_KEY='your-key-here'
export OPENAI_API_KEY='your-key-here'  # Optional for voice features
```

2. Import the package:

```python
import jupyterchat as jc
```

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
style = "Be precise and concise"
question = "What's new in Python 3.12?"
search_online(style, question)
```

### Voice Commands

Leverage voice input capabilities:
- Control recording with keyboard shortcuts
- Automatic speech-to-text conversion
- Seamless chat interface integration

### History Management

Access your conversation history:

```python
hist()  # Display formatted chat history
```

## 🛠️ Advanced Features

### Magic Commands

- `%%user [index]` - Initiate a user message
- `%%assistant [index]` - Include assistant response
- Multi-language support (Python, R, SQL, etc.)

### Smart Processing

- Automatic code detection and execution
- Dynamic cell type conversion
- Live markdown rendering
- Syntax highlighting support

## 🔧 Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/jupyterchat.git
cd jupyterchat
pip install -e ".[dev]"
```

### Running Tests

```bash
python -m pytest tests/
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
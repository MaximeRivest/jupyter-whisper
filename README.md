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
- Jupyter Notebook
- Anthropic API key (for Claude integration)
- OpenAI API key (optional, for voice features) 
- Perplexity API key (required for advanced search capabilities)

## 🏁 Quick Start

<details>
<summary>Linux/MacOS Configuration</summary>

```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="your-key-here"' >> ~/.bashrc  # Optional for voice features
echo 'export PERPLEXITY_API_KEY="your-key-here"' >> ~/.bashrc  # For search features
source ~/.bashrc
```
</details>

<details>
<summary>Windows Configuration</summary>

```powershell
# Run in PowerShell as administrator
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key-here", "User")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key-here", "User")
[Environment]::SetEnvironmentVariable("PERPLEXITY_API_KEY", "your-key-here", "User")
```
</details>

<details>
<summary>Python Configuration</summary>

```python
import os

# Set environment variables programmatically
os.environ["ANTHROPIC_API_KEY"] = "your-key-here"
os.environ["OPENAI_API_KEY"] = "your-key-here"      # Optional for voice
os.environ["PERPLEXITY_API_KEY"] = "your-key-here"  # For search
```
</details>

2. Import and start using JupyterWhisper:

```python
import jupyter_whisper as jw
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
git clone https://github.com/yourusername/jupyter_whisper.git
cd jupyter_whisper
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
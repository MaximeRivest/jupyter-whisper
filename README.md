# JChat - Interactive AI Assistant for Jupyter Notebooks

JChat is a powerful Jupyter notebook extension that integrates Claude AI capabilities with voice recognition, text processing, and interactive chat features. It provides a seamless way to interact with AI assistants directly within your notebook environment.

## Features

- 🤖 Direct integration with Claude AI
- 🎙️ Voice-to-text transcription
- ⌨️ Convenient keyboard shortcuts
- 📝 Smart text processing and code execution
- 🔄 Real-time markdown rendering
- 🎯 Code block parsing and syntax highlighting

## Installation

bash
pip install jchat-notebook


## Requirements

- Python 3.7+
- Jupyter Notebook
- Anthropic API key
- OpenAI API key (for voice transcription)

## Quick Start

1. Set up your API keys:

bash
export ANTHROPIC_API_KEY='your-key-here'
export OPENAI_API_KEY='your-key-here'


2. Import JChat in your notebook:

python
from jchat import *


## Usage

### Chat Interface

Use the `%%user` magic command to interact with the AI:

python
%%user
How do I read a CSV file using pandas?


The assistant's response will automatically appear in a new cell with executable code blocks when appropriate.

### Voice Commands

- Press `Ctrl+Shift+Z` to start/stop voice recording
- Your speech will be transcribed and processed automatically

### Text Processing

- Select text and press `Ctrl+Shift+A` to process with Claude
- Supports code formatting and correction
- Handles multiple programming languages

### History Management

View your chat history:

python
hist()


## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+Z | Toggle voice recording |
| Ctrl+Shift+A | Process selected text |

## API Reference

### Python Interface

python
# Initialize chat
c = Chat(model="claude-3-5-sonnet-20241022")

# Access history
c.h  # Chat history

# Create new cells
create_assistant_cell()


### JavaScript API

javascript
// Start voice recording
VoiceRecorderModule.startRecording()

// Stop recording
VoiceRecorderModule.stopRecording()


## Configuration

Debug mode can be enabled:

python
DEBUG = True


## Examples

### Code Assistance

python
%%user
Fix this code:
def fibonacci(n)
    if n <= 1: return n
    return fibonacci(n-1) + fibonacci(n-2)


### Voice Transcription

1. Press `Ctrl+Shift+Z` to start recording
2. Speak your query
3. Press `Ctrl+Shift+Z` again to stop and process

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

### Development Setup

bash
git clone https://github.com/yourusername/jchat.git
cd jchat
pip install -e ".[dev]"


## License

MIT License - see [LICENSE](LICENSE) for details

## Credits

- Built with [Claude](https://anthropic.com/claude) by Anthropic
- Voice transcription powered by [OpenAI Whisper](https://openai.com/research/whisper)
- FastAPI for backend services

## Support

- 📚 [Documentation](docs/README.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/jchat/issues)
- 💬 [Discussions](https://github.com/yourusername/jchat/discussions)

## Roadmap

- [ ] Support for additional AI models
- [ ] Enhanced code completion
- [ ] Custom voice commands
- [ ] Collaborative features
- [ ] Plugin system

---

Made with ❤️ by [Your Name]

*Note: This project is not officially affiliated with Anthropic or OpenAI.*

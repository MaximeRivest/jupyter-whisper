User Guide
=========

Installation
-----------

.. code-block:: bash

   pip install jupyter_whisper

Quick Start
----------

.. code-block:: python

   from jupyter_whisper import *

   # Start a chat session
   %%user 0
   How can I help you today?

Configuration
------------

1. Set up your Claude API key:
   
   .. code-block:: python

      import os
      os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

Basic Usage
----------

- Use ``%%user`` magic command to start a chat
- Use ``%%assistant`` to see AI responses
- Use voice commands with the microphone button
- Access online search with the search button

Features
--------

- AI-powered chat interface
- Voice command support
- Online search integration
- Cell output management
- Real-time execution monitoring

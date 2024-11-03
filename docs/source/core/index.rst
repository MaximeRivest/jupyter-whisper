Core Functionality
================

Chat Interface
------------
The core of JupyterWhisper is its chat interface, implemented through cell magic commands:

.. code-block:: python

   %%user 0
   How can I help you today?

   %%assistant 1
   I'm here to help! Let me know what you need.

Cell Management
-------------
JupyterWhisper provides sophisticated cell output capture and management:

- Captures stdout, stderr, and cell outputs
- Tracks execution timestamps
- Maintains cell type information
- Supports multiple programming languages

Server Features
-------------
Built-in FastAPI server providing:

- Audio transcription
- External API communication
- CORS support
- Proxy functionality

Search Integration
---------------
Online search capabilities with style-based formatting:

.. code-block:: python

   search_online("concise", "What is Python?")

Installation
-----------
Install via pip:

.. code-block:: bash

   pip install jupyter_whisper


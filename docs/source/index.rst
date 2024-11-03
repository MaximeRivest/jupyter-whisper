JupyterChat Documentation
========================

JupyterChat is a Jupyter notebook extension that enhances notebooks with chat-like capabilities, AI assistance, and advanced cell management features.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user_guide/index
   api_reference/index
   examples/index
   development/index

Features
--------

* Chat-like interface in Jupyter notebooks
* AI-powered assistance using Claude model
* Advanced cell output capture and management
* Online search integration
* Audio transcription support
* Real-time cell execution monitoring

Quick Start
----------

.. code-block:: python

   from jupyterchat import *

   # Start a chat session
   %%user 0
   How can I help you today?

Installation
------------

.. code-block:: bash

   pip install jupyterchat


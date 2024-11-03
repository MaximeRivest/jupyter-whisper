Basic Examples
============

Chat Interaction
--------------

.. code-block:: python

   from jupyterchat import *

   %%user 0
   How do I use Python's list comprehension?

   %%assistant 1
   Here's an example of list comprehension:
   
   numbers = [1, 2, 3, 4, 5]
   squares = [x**2 for x in numbers]

Search Usage
----------

.. code-block:: python

   search_online(
       style="concise",
       question="What is machine learning?"
   )

Audio Transcription
----------------

.. code-block:: python

   # Record audio and transcribe
   # The UI will show a record button
   # Transcription happens automatically

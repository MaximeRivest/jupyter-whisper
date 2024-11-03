API Reference
===========

Core Functions
------------

.. py:function:: search_online(style: str, question: str)
   
   Search online with formatted results

.. py:function:: hist()
   
   Display chat history

Magic Commands
------------

.. py:function:: %%user [index]

   Create a user message cell

.. py:function:: %%assistant [index]

   Create an assistant response cell

Server API
---------

.. py:class:: FastAPI

   /proxy - Proxy requests to Claude API
   /audio - Handle audio transcription
   /status - Server health check

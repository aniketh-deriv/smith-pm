# Agentic Office PM - Smith

An intelligent Slack bot powered by LangChain that serves as a Project Manager AI, capable of tracking project statuses and team activities based on Slack channel data.

## Overview

This project implements a Slack bot named Smith that uses Large Language Models (LLMs) to understand and respond to user requests about project statuses and team activities. It features a sophisticated system for analyzing Slack conversations, tracking project progress, and providing concise status reports.

## Features

- 🤖 AI-powered Slack bot using LangChain
- 🧵 Thread-based conversation management
- 📊 Project status tracking and reporting
- 👥 Team activity monitoring
- 🔍 Smart channel discovery and analysis
- 📝 Comprehensive logging
- 🧠 LangGraph Supervisor architecture with specialized agents
- 💾 LangMem persistent memory system for context retention

## Prerequisites

- Python 3.x
- Slack App with Socket Mode enabled
- OpenAI API key (or other supported LLM provider)

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Slack App:
   - Create a new Slack App in your workspace
   - Enable Socket Mode in your Slack App settings
   - Generate an App-Level Token with `connections:write` scope
   - Add bot token scopes: `channels:history`, `channels:join`, `channels:read`, `chat:write`, `groups:history`, `groups:read`, `im:history`, `im:read`
   - Install the app to your workspace

4. Create a `.env` file with the following variables:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL_NAME=gpt-4o  # or your preferred model
   API_BASE_URL=your-api-base-url  # if using a custom API endpoint
   ```

## Running the Bot

### Slack Interface

1. Start the Slack bot:
   ```bash
   python slack.py
   ```

2. The bot will connect to Slack using Socket Mode, which:
   - Provides a secure connection without exposing public endpoints
   - Eliminates the need for setting up SSL/TLS certificates
   - Works behind firewalls and in local development
   - Enables real-time message handling

3. Once connected, you can interact with the bot by:
   - Mentioning it in a channel: `@Smith what's the status of Project Alpha?`
   - The bot will respond in a thread
   - All subsequent messages in the thread will be processed by the bot

## Project Structure

- `slack.py` - Main Slack bot implementation with message handling
- `manager.py` - Conversation management and LLM integration
- `tools.py` - Tool definitions and implementations
- `agents.py` - Agent definitions for different specialized roles
- `system.md` - System prompt for the AI agent
- `docs/` - Documentation files

## Architecture

Smith uses a LangGraph Supervisor architecture to coordinate between specialized agents:

- **Supervisor Agent**: Orchestrates the workflow and delegates to specialized agents
- **Main Agent**: Handles general queries and provides overall assistance
- **Channel Explorer Agent**: Specializes in channel information and exploration
- **User Activity Agent**: Focuses on analyzing user activities and patterns
- **Message Search Agent**: Specializes in finding and analyzing message content

This multi-agent approach allows Smith to handle a wide range of project management tasks with specialized expertise for each domain.

### Memory System

Smith uses LangMem for persistent memory capabilities:

- **Thread-Specific Memory**: Maintains context within conversation threads
- **User-Global Memory**: Remembers user preferences across different conversations
- **Namespaced Storage**: Organizes memory by user and context type
- **Memory Tools**: Provides tools for storing and retrieving information

This memory architecture enables Smith to maintain context over time, remember user preferences, and provide personalized responses based on past interactions.

## Core Tools

The bot uses a flexible tool system that allows it to perform specific actions based on user requests:

### 1. Channel Management

- `get_accessible_channels` - Lists all accessible Slack channels
- `get_channel_info` - Retrieves detailed information about a specific channel
- `list_channel_members` - Lists all members in a specific channel

### 2. Message Analysis

- `get_recent_channel_messages` - Retrieves recent messages from specified channels
- `get_user_active_channels` - Finds channels where a user is actively posting

### 3. Memory Management

- `manage_memory` - Stores information in the bot's memory using LangMem
- `search_memory` - Searches for information in the bot's memory
- `store_procedure` - Stores a procedure for later execution
- `recall_procedure` - Recalls a stored procedure
- `execute_procedure` - Executes a stored procedure

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- `index.md` - Overview and getting started
- `system.md` - System prompt and AI behavior
- `tools.md` - Available tools and their usage
- `slack.md` - Slack integration details
- `manager.md` - Conversation manager implementation

You can view the documentation using MkDocs:

```bash
pip install -r requirements.txt
mkdocs serve
```

Then visit `http://localhost:8000` in your browser.

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
# smith-pm
# smith-pm

# Slack Integration

The Slack integration component of the Agentic Office PM system handles all interactions with Slack, including message processing, event handling, and interactive components.

## Setup

### Environment Variables

Required environment variables:
```bash
SLACK_BOT_TOKEN=xoxb-...  # Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...  # App-Level Token
OPENAI_API_KEY=sk-...     # OpenAI API Key
OPENAI_MODEL_NAME=gpt-4o  # OpenAI Model Name
API_BASE_URL=...          # Optional custom API endpoint
```

### Installation

1. Create a Slack App in your workspace
2. Enable Socket Mode
3. Add required bot scopes:
   - channels:history
   - channels:join
   - channels:read
   - chat:write
   - groups:history
   - groups:read
   - im:history
   - im:read

## Core Components

### 1. Slack App Initialization

```python
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
handler = SocketModeHandler(
    app=app,
    app_token=os.environ.get("SLACK_APP_TOKEN")
)
```

### 2. Event Handlers

#### App Mention Handler

Processes mentions of the bot in channels:

```python
@app.event("app_mention")
def handle_app_mention_events(body):
    """
    Handles mentions of the bot in channels.
    """
```

Features:
- Extracts message text
- Identifies the channel and thread
- Creates or retrieves conversation manager
- Processes the message and generates a response

#### Message Handler

Processes messages in threads where the bot is active:

```python
@app.event("message")
def handle_message_events(body):
    """
    Handles messages in threads where the bot is active.
    """
```

Features:
- Thread awareness
- Ignores messages not in relevant threads
- Maintains conversation context
- Processes messages and generates responses

## Message Processing

### LangGraphManager

The `LangGraphManager` class handles the core AI functionality:

```python
class LangGraphManager:
    def __init__(self, slack_client=None, checkpointer=None):
        """
        Initialize the manager with optional Slack client and checkpointer.
        """
```

Key methods:
- `process_message` - Processes user messages and generates responses
- `_create_agent` - Creates the AI agent with appropriate tools
- `tool_approval_node` - Handles tool approval workflow

### Conversation Management

The system maintains conversation state using thread IDs:

```python
def get_or_create_manager(conversation_id, slack_client=None):
    """
    Get an existing manager or create a new one for the conversation.
    """
```

Features:
- Thread-based conversation tracking
- Persistent conversation state
- Slack client integration
- Error handling and recovery

## Best Practices

### 1. Thread Management

- Keep conversations in threads for context
- Use thread_ts for conversation identification
- Handle thread-specific state

### 2. Message Formatting

- Use Slack's text formatting for readability
- Format channel references as `<#CHANNEL_ID|channel-name>`
- Format user references as `<@USER_ID>`

### 3. Error Handling

- Log all errors with appropriate context
- Provide user-friendly error messages
- Maintain conversation state during errors
- Gracefully recover from API failures

### 4. Performance

- Cache channel and user information
- Batch API calls when possible
- Handle rate limits appropriately
- Optimize message processing

## Example Interactions

### 1. Project Status Query

User:
```
@Smith what's the status of Project Alpha?
```

Processing:
1. Bot identifies the request as a project status query
2. Finds channels related to "Project Alpha"
3. Retrieves recent messages from those channels
4. Analyzes messages for status information
5. Formats a concise response with status indicators

### 2. Team Activity Query

User:
```
@Smith what has @username been working on?
```

Processing:
1. Bot identifies the request as a user activity query
2. Finds channels where the user is active
3. Retrieves recent messages from those channels
4. Analyzes messages for the user's contributions
5. Formats a concise summary of the user's activities

### 3. Multi-Channel Report

User:
```
@Smith give me updates on all backend projects
```

Processing:
1. Bot identifies the request as a multi-channel report
2. Finds channels related to "backend" and "projects"
3. Batches channels (up to 5 at a time) for message retrieval
4. Analyzes messages for status information
5. Formats a structured report with status indicators for each project

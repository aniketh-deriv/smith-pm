# Available Tools

This document outlines the tools available in the Agentic Office PM system. These tools provide specific functionalities that enable the AI to interact with Slack and manage project information effectively.

## Tool System Overview

The tool system is built using decorators to manage tool registration:

```python
@enabled_tool     # Registers the tool as available
@tool             # Langchain tool decorator
def tool_name():
    # Tool implementation
```

## Core Tools

### 1. Channel Management

#### get_accessible_channels

Retrieves a list of accessible Slack channels.

```python
@enabled_tool
@tool
def get_accessible_channels(opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Get a list of public channels that are not archived.
    """
```

**Features:**
- Excludes archived channels
- Filters for public channels only
- Caches results for performance
- Handles pagination automatically

**Output Format:**
```
=== Available Slack Channels ===
channel-name: CHANNEL_ID
another-channel: CHANNEL_ID
```

#### get_channel_info

Retrieves detailed information about a specific channel.

```python
@tool
def get_channel_info(channel_id_or_name: str) -> str:
    """
    Get detailed information about a specific channel.
    """
```

**Features:**
- Accepts either channel ID or name
- Provides comprehensive channel details
- Includes member count and topic
- Shows creation date and purpose

#### list_channel_members

Lists all members in a specific channel.

```python
@tool
def list_channel_members(channel_id_or_name: str) -> str:
    """
    List all members in a specific channel.
    """
```

**Features:**
- Accepts either channel ID or name
- Lists all members with their IDs
- Handles large member lists
- Provides formatted output

### 2. Message Analysis

#### get_recent_channel_messages

Fetches and formats recent messages from specified channels.

```python
@enabled_tool
@tool
def get_recent_channel_messages(channel_ids: List[str], days: int, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Get recent messages from specified channels over the past X days.
    """
```

**Features:**
- Retrieves messages from multiple channels
- Includes threaded replies
- Filters by time period (days)
- Formats messages for readability
- Handles message pagination

**Output Format:**
```
=== Messages from #channel-name (last X days) ===
[YYYY-MM-DD HH:MM] @username: Message text
  └─ [YYYY-MM-DD HH:MM] @reply_user: Reply text
```

#### get_user_active_channels

Analyzes Slack data to find channels where a user is actively posting.

```python
@enabled_tool
@tool
def get_user_active_channels(user_identifier: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Find channels where a user is actively posting.
    """
```

**Features:**
- Accepts user ID or username
- Analyzes posting frequency
- Ranks channels by activity level
- Provides post count per channel

**Output Format:**
```
=== Active Channels for @username ===
<#CHANNEL_ID|channel-name>: 42 posts
<#CHANNEL_ID|another-channel>: 15 posts
```

### 3. Memory Management

The memory management tools leverage LangMem to provide sophisticated memory capabilities with namespaced organization.

#### manage_memory

Stores information in the bot's memory for later retrieval.

```python
@enabled_tool
@tool
def manage_memory(content: str, key: str = None, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Store information in memory for later retrieval.
    """
```

**Features:**
- Stores arbitrary content
- Optional key for organization
- Namespace support for multi-user environments
- Automatic timestamping
- Agent-specific or shared memory spaces

**Usage:**

#### search_memory

Searches for information in the bot's memory.

```python
@enabled_tool
@tool
def search_memory(query: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Search for information in memory.
    """
```

**Features:**
- Keyword-based search
- Namespace-aware searching
- Relevance ranking
- Formatted results

### 4. Procedure Management

#### store_procedure

Stores a procedure (sequence of steps) for later execution.

```python
@enabled_tool
@tool
def store_procedure(name: str, steps: List[str], opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Store a procedure (sequence of steps) for later execution.
    """
```

**Features:**
- Named procedures
- Multi-step sequences
- Persistent storage
- User-specific procedures

#### recall_procedure

Recalls a stored procedure.

```python
@enabled_tool
@tool
def recall_procedure(name: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Recall a stored procedure.
    """
```

**Features:**
- Retrieves procedure by name
- Shows all steps
- Handles missing procedures
- User-specific recall

#### execute_procedure

Executes a stored procedure.

```python
@enabled_tool
@tool
def execute_procedure(name: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Execute a stored procedure.
    """
```

**Features:**
- Runs all steps in sequence
- Reports execution status
- Handles errors gracefully
- Provides execution summary

### 5. Agent Transfer

#### transfer_to_channel_explorer

Transfers control to the Channel Explorer agent.

```python
@enabled_tool
@tool
def transfer_to_channel_explorer(tool_input: str = "") -> str:
    """
    Transfer control to the Channel Explorer agent.
    """
```

#### transfer_back_to_supervisor

Transfers control back to the main supervisor agent.

```python
@enabled_tool
@tool
def transfer_back_to_supervisor(tool_input: str = "") -> str:
    """
    Transfer control back to the main supervisor agent.
    """
```

### 6. Self-Improvement

#### reflect_and_improve

Analyzes past interactions and updates agent instructions to improve performance.

```python
@enabled_tool
@tool
def reflect_and_improve(feedback: str = "", opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Reflect on recent interactions and update agent instructions to improve performance.
    """
```

**Features:**
- Analyzes recent conversations
- Incorporates explicit user feedback
- Updates agent instructions
- Preserves core agent functionality
- Provides improvement summary

**Process:**
1. Retrieves current agent instructions
2. Analyzes recent conversations
3. Identifies improvement opportunities
4. Generates updated instructions
5. Stores the improved instructions
6. Returns a summary of improvements

This tool enables continuous improvement of agent performance based on actual usage patterns and explicit user feedback.

## Best Practices for Tool Usage

1. **Channel Selection**
   - Use `get_accessible_channels` to discover available channels
   - Filter channels based on naming patterns (e.g., "project-", "team-")
   - Prioritize active channels for information gathering

2. **Message Analysis**
   - Use appropriate time windows (7 days for general updates, shorter for specific queries)
   - Batch channel requests (up to 5 at a time)
   - Look for patterns in message content (status updates, blockers, deadlines)

3. **User Activity**
   - Use `get_user_active_channels` to find where team members are most active
   - Set appropriate post thresholds (10 posts is a good default)
   - Correlate activity with project channels for team contribution analysis

4. **Memory Usage**
   - Store important information for later reference
   - Use consistent key naming for easier retrieval
   - Regularly search memory for relevant context

5. **Procedure Management**
   - Create procedures for common multi-step tasks
   - Use clear, descriptive procedure names
   - Include error handling in procedure steps

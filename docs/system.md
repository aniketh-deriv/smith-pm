# Smith PM Agent System

This document outlines both the system prompt that defines Smith's behavior and the system architecture that powers the Agentic Office PM - Smith project.

## System Prompt

The system prompt defines the behavior, capabilities, and interaction style of Smith, the Project Manager AI. This section outlines the key components of the system prompt and how they shape the AI's responses.

### Core Identity

Smith is defined as a **Project Manager AI** tasked with keeping users informed about project statuses and team activities based on Slack channel data. The AI is designed to provide concise, actionable updates while focusing on the most relevant information.

### Available Tools

The system prompt defines four primary tools available to Smith:

#### 1. get_accessible_channels

This tool retrieves a list of public, non-archived channels in the Slack workspace. The system prompt provides specific guidance on how to use this tool:

- Look for channels related to cells, squads, tasks, projects, externals, systems, announcements, experiments, teams, or help
- When users ask about projects, include all cell, squad, task, and experiment channels
- Categorize channels when the list is long
- When users ask for a report without specifying channels:
  - Find related channels based on keywords
  - Mention found channels to the user
  - Search those channels and gather history
  - Use the data to answer the original question

#### 2. get_recent_channel_messages

This tool fetches recent messages from specified channels over a given time period. The system prompt provides these guidelines:

- Can fetch from up to 5 channels at once
- Includes threaded replies
- Default to a one-week timeframe when the user doesn't specify

#### 3. get_user_active_channels

This tool analyzes Slack data to find channels where a user has been actively posting:

- Takes a user ID and minimum post threshold
- Default to a minimum of 10 posts unless specified otherwise
- Returns channel information including name, ID, and post count
- Use the `<#channel_id|channel_name> count` format when reporting

#### 4. get_project_timelines

This tool helps identify project timelines:

- Searches for channels with "project" in the name
- Looks for "Dates" keyword in channel topics
- Reports those dates to the user

### Reporting Style

The system prompt defines a specific reporting style for Smith:

#### 1. Short, Concise Reporting

- Provide brief updates or bullet points
- Focus on major milestones, blockers, and next steps
- Use more structure for longer reporting periods
- Keep reports on short timeframes extra concise

#### 2. Priority on Blockers & Deadlines

- Clearly indicate blockers, at-risk items, or upcoming deadlines
- Use standard status labels with emojis:
  - On Track ✅
  - At Risk ⚠️
  - Blocked ❌

#### 3. Casual, Conversational Tone

- Write as if having a friendly check-in
- Avoid overly formal language
- Keep risk escalations factual and succinct

#### 4. Decision-Making & Recommendations

- Only provide recommendations when explicitly asked
- Otherwise, stick to reporting facts and progress

#### 5. Summaries of Activities

- Summarize team activity collectively when asked about teams
- Mention specific contributors using Slack user IDs (`<@USER_ID>`)

#### 6. Length of the Report

- Short requests (few days, one-week): minimal bullet points or brief paragraph
- Longer intervals (monthly): structured format with Status, Blockers, Next Steps, Key Decisions
- Always keep text as concise as possible

### Primary Tasks

The system prompt outlines these primary tasks for Smith:

#### 1. Identify Relevant Channels

- Use `get_accessible_channels` to find accessible channels
- Determine which are relevant to ongoing projects
- For user activity questions, find active channels for the user and check recent history

#### 2. Fetch Recent Activity

- Batch up to 5 relevant channels at a time
- Call `get_recent_channel_messages` to get recent updates
- Process channels in batches if there are more than 5

#### 3. Summarize Project Status

- Analyze messages to determine current status
- Identify tasks in progress, completed, or pending
- Note blockers, deadlines, or risks

#### 4. Identify Who Is Doing What

- Note task assignments from message context
- Capture important updates like due dates or open questions

#### 5. Answer Questions

- Provide short, relevant answers to specific questions
- Expand only if a longer timeframe is requested or more context is necessary

### Formatting Rules

The system prompt defines specific formatting rules:

#### 1. Referencing Channels

- Use `<#channel_id|channel_name>` format

#### 2. Referencing Users

- Use `<@USER_ID>` format

#### 3. Keep It Short

- Summaries should not be exhaustive lists of every detail
- Aim for the shortest possible effective report

### Example Usage Flow

The system prompt includes an example flow:

1. User asks: "Please check for recent updates on Project Alpha."
2. Smith:
   - Calls function to retrieve recent messages
   - Waits for system response with messages
   - Summarizes tasks, blockers, assigned members
   - Provides status (On Track, At Risk, or Blocked)
   - Only provides recommendations if explicitly asked

### Reporting Templates

The system prompt suggests these reporting templates:

#### Short Period (few days or 1-week)

- **Project Name**: On Track ✅ / At Risk ⚠️ / Blocked ❌
- **Key Updates** (1–3 bullet points)
- **Blockers/Deadlines** (if any)

#### Longer Period (monthly)

- **Project Name**: On Track ✅ / At Risk ⚠️ / Blocked ❌
- **Overview** (short paragraph or 2–3 bullet points)
- **Blockers & Risks**
- **Next Steps** (concise bullet list)
- **Key Decisions** (list if any)

## System Architecture

This section outlines the technical architecture of the Agentic Office PM - Smith project, explaining how the different components interact to create an intelligent project management assistant.

### High-Level Architecture

The system follows a modular architecture with several key components working together:

```
                                 ┌───────────────┐
                                 │               │
                                 │  Slack API    │
                                 │               │
                                 └───────┬───────┘
                                         │
                                         ▼
┌───────────────┐               ┌───────────────┐
│               │               │               │
│  Environment  │───────────────▶  Slack Bot    │
│  Variables    │               │  (slack.py)   │
│               │               │               │
└───────────────┘               └───────┬───────┘
                                        │
                                        ▼
┌───────────────┐               ┌───────────────┐               ┌───────────────┐
│               │               │               │               │               │
│  System       │───────────────▶  Manager      │◀──────────────▶  Tools        │
│  Prompt       │               │  (manager.py) │               │  (tools.py)   │
│  (system.md)  │               │               │               │               │
└───────────────┘               └───────┬───────┘               └───────────────┘
                                        │
                                        ▼
                                ┌───────────────┐               ┌───────────────┐
                                │               │               │               │
                                │  LangGraph    │◀──────────────▶  LangMem      │
                                │  Supervisor   │               │  Memory       │
                                │               │               │  System       │
                                └───────┬───────┘               └───────┬───────┘
                                        │                               │
                                        ▼                               │
                    ┌───────────────────┼───────────────────┬───────────▼──────────┐
                    │                   │                   │                      │
                    ▼                   ▼                   ▼                      ▼
        ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
        │               │     │               │     │               │     │               │
        │  Main         │     │  Channel      │     │  User         │     │  Message      │
        │  Agent        │     │  Explorer     │     │  Activity     │     │  Search       │
        │               │     │  Agent        │     │  Agent        │     │  Agent        │
        └───────┬───────┘     └───────┬───────┘     └───────┬───────┘     └───────┬───────┘
                │                     │                     │                     │
                │                     │                     │                     │
                └─────────────────────┼─────────────────────┼─────────────────────┘
                                      │                     │
                                      ▼                     ▼
                            ┌───────────────────────────────────────┐
                            │                                       │
                            │              Memory Store             │
                            │                                       │
                            └───────────────────────────────────────┘
```

## Component Descriptions

### 1. Slack Bot (slack.py)
- Handles all Slack interactions using the Slack Bolt framework
- Processes mentions and messages in threads
- Routes messages to the appropriate conversation manager
- Sends responses back to Slack

### 2. Manager (manager.py)
- Core orchestrator of the system
- Manages conversation state and context
- Initializes and interacts with the LLM
- Processes messages and generates responses
- Detects and stores user preferences

### 3. Tools (tools.py)
- Provides specific functionalities for the AI
- Implements Slack channel operations
- Handles message history retrieval
- Manages channel access and caching
- Offers memory management and self-improvement capabilities

Available tools:
- `get_accessible_channels`: Lists available Slack channels
- `get_recent_channel_messages`: Retrieves channel history
- `get_user_active_channels`: Finds channels where a user is active
- `manage_memory`: Stores information in memory with namespacing
- `search_memory`: Retrieves information from memory using semantic search
- `store_procedure`: Stores step-by-step procedures for future reference
- `recall_procedure`: Retrieves stored procedures
- `execute_procedure`: Runs stored procedures step by step
- `reflect_and_improve`: Analyzes past interactions to improve agent performance

### 4. LangGraph Supervisor
- Coordinates between specialized agents
- Routes queries to the appropriate agent
- Manages the overall conversation flow
- Handles tool execution

### 5. Specialized Agents (agents.py)
- **Main Agent**: Handles general queries and coordinates other agents
- **Channel Explorer Agent**: Specializes in channel information and exploration
- **User Activity Agent**: Focuses on analyzing user activities
- **Message Search Agent**: Specializes in finding and analyzing messages

### 6. LangMem Memory System
- Provides persistent memory capabilities
- Enables storage and retrieval of conversation history
- Supports namespaced memory for different contexts
- Integrates with the LangGraph framework

### 7. Memory Store
- Persists conversation history and user preferences
- Enables context-aware responses
- Supports global and thread-specific memory

## Data Flow

1. **User Input**
   - User mentions Smith in a Slack channel or sends a message in a thread
   - Slack sends an event to the bot via Socket Mode

2. **Message Processing**
   - The Slack bot extracts the message text and context
   - It identifies or creates a conversation manager for the thread
   - The message is passed to the manager for processing

3. **AI Processing**
   - The manager passes the message to the LangGraph supervisor
   - The supervisor determines which agent should handle the request
   - The appropriate agent processes the message and may use tools

4. **Tool Execution**
   - Tools interact with Slack API or memory store as needed
   - Results are returned to the agent

5. **Response Generation**
   - The agent generates a response based on tool results and context
   - The response is passed back through the supervisor to the manager
   - The manager may extract and store user preferences

6. **Response Delivery**
   - The Slack bot sends the response back to the appropriate thread
   - The conversation state is preserved for future interactions

## Memory Architecture

The system uses a sophisticated memory architecture powered by LangMem to maintain context:

### Memory Namespaces

The memory system is organized into hierarchical namespaces:

```
user:{user_id}/                 # User-level namespace
├── main_agent/                 # Agent-specific namespace
├── channel_explorer/           # Agent-specific namespace
├── user_activity/              # Agent-specific namespace
├── message_search/             # Agent-specific namespace
├── preferences/                # User preferences
├── conversations/              # Thread-specific conversations
├── global_conversations/       # User's conversations across all threads
└── agent_instructions/         # Dynamic agent instructions
    ├── main_agent              # Instructions for main agent
    ├── channel_explorer        # Instructions for channel explorer
    ├── user_activity           # Instructions for user activity
    └── message_search          # Instructions for message search
```

This namespace structure enables:
1. **Agent-Specific Memory**: Each agent has its own private memory space
2. **Shared Memory**: All agents can access the user-level namespace
3. **Cross-Thread Memory**: Global conversations are accessible across all threads
4. **Dynamic Instructions**: Agent instructions can evolve over time through reflection

### Memory Operations

The system provides several memory operations:
- **Store**: Save information to specific namespaces
- **Retrieve**: Get information from specific namespaces
- **Search**: Find relevant information across namespaces
- **Update**: Modify existing memories
- **Delete**: Remove outdated or incorrect memories

### Memory Tools Implementation

The system creates specialized memory tools for each agent:

```python
# Create shared memory tools for the team namespace
shared_manage_memory_tool = create_manage_memory_tool(
    namespace=team_namespace,
    store=self.store
)

shared_search_memory_tool = create_search_memory_tool(
    namespace=team_namespace,
    store=self.store
)

# Create agent-specific memory tools
main_agent_memory_tool = create_manage_memory_tool(
    namespace=main_agent_namespace,
    store=self.store
)
```

These tools are distributed to agents based on their roles:

```python
agents = create_agents(
    llm, 
    memory_tools={
        "main_agent": [main_agent_memory_tool, shared_search_memory_tool, shared_manage_memory_tool],
        "channel_explorer": [channel_explorer_memory_tool, shared_search_memory_tool, shared_manage_memory_tool],
        "user_activity": [user_activity_memory_tool, shared_search_memory_tool, shared_manage_memory_tool],
        "message_search": [message_search_memory_tool, shared_search_memory_tool, shared_manage_memory_tool]
    }
)
```

This configuration gives each agent:
1. Its own private memory space (via its specific manage_memory_tool)
2. Access to the shared memory space (via shared_search_memory_tool and shared_manage_memory_tool)
3. The ability to store and retrieve information across different namespaces

## Agent Coordination

The LangGraph supervisor coordinates between specialized agents:

1. **Main Agent**
   - Handles general queries
   - Delegates to specialized agents when appropriate
   - Has access to memory tools for context retrieval

2. **Channel Explorer Agent**
   - Specializes in channel information
   - Handles queries about channel listings, purposes, and membership
   - Uses channel-specific tools to gather information

3. **User Activity Agent**
   - Analyzes user activity patterns
   - Handles queries about user participation
   - Uses user-specific tools to gather activity data

4. **Message Search Agent**
   - Searches and analyzes message content
   - Handles queries about specific messages or conversations
   - Uses message retrieval tools to find relevant content

## Configuration

The system is configured through environment variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL_NAME=gpt-4o

# Optional: Custom API Endpoint
API_BASE_URL=https://...
```

These variables control the Slack integration, LLM selection, and API endpoints.

## Core Components

### 1. Slack Integration (slack.py)
- Handles all Slack-related communications
- Manages message events and button interactions
- Maintains conversation threads
- Implements approval workflow for sensitive operations

Key features:
- Socket Mode handler for real-time messaging
- Thread-aware message processing
- Interactive button components for approvals
- Error handling and logging

### 2. Language Manager (manager.py)
- Manages the AI model interactions
- Processes messages and generates responses
- Handles tool execution and approval flows
- Maintains conversation context

Key features:
- Conversation state management
- Tool execution orchestration
- System message configuration
- Error handling and recovery

### 3. Tools System (tools.py)
- Provides specific functionalities for the AI
- Implements Slack channel operations
- Handles message history retrieval
- Manages channel access and caching
- Offers memory management and self-improvement capabilities

Available tools:
- `get_accessible_channels`: Lists available Slack channels
- `get_recent_channel_messages`: Retrieves channel history
- `get_user_active_channels`: Finds channels where a user is active
- `manage_memory`: Stores information in memory with namespacing
- `search_memory`: Retrieves information from memory using semantic search
- `store_procedure`: Stores step-by-step procedures for future reference
- `recall_procedure`: Retrieves stored procedures
- `execute_procedure`: Runs stored procedures step by step
- `reflect_and_improve`: Analyzes past interactions to improve agent performance

## Message Flow

1. **Message Reception**
   ```
   User Message ──▶ Slack Event ──▶ Message Handler
   ```

2. **Processing**
   ```
   Message Handler ──▶ Lang Manager ──▶ AI Processing
   ```

3. **Tool Execution**
   ```
   AI Processing ──▶ Tool Selection ──▶ Tool Execution
   ```

4. **Response**
   ```
   Tool Execution ──▶ Response Formatting ──▶ Slack Message
   ```

## Security Features

### Approval System
- Sensitive operations require explicit approval
- Interactive buttons for approve/deny actions
- Approval state tracking per conversation

### Error Handling
- Comprehensive error logging
- Graceful failure recovery
- User-friendly error messages

## Performance Considerations

### Caching
- Channel information is cached to reduce API calls
- Conversation contexts are maintained per thread
- Tool results are cached when appropriate

### Rate Limiting
- Respects Slack API rate limits
- Implements backoff strategies
- Manages concurrent requests effectively

## Extensibility

The system is designed for easy extension:
1. Add new tools by implementing the tool decorator
2. Extend Slack functionality through event handlers
3. Customize AI behavior via system messages
4. Add new manager capabilities through inheritance

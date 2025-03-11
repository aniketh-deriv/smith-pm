# Memory System

The Agentic Office PM system uses LangMem to implement a sophisticated memory system that enables persistent context, shared knowledge, and self-improvement capabilities.

## Overview

LangMem provides the foundation for storing and retrieving information across conversations and between different specialized agents. This enables Smith to:

- Remember user preferences and past interactions
- Share knowledge between specialized agents
- Maintain context across different conversation threads
- Improve performance through reflection and learning

## Memory Architecture

### Store Implementation

The system uses an `InMemoryStore` as the foundation for memory storage:

```python
self.store = InMemoryStore()
```

While this implementation keeps memories in RAM, the architecture supports swapping in other store implementations (like vector databases) without changing the application logic.

### Namespace Structure

Memories are organized in a hierarchical namespace structure:

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

This structure enables:
- Isolation between different users
- Private memory spaces for each agent
- Shared memory accessible to all agents
- Specialized memory categories (preferences, conversations, etc.)

## Memory Tools

### Memory Management Tool

```python
create_manage_memory_tool(namespace=namespace, store=store)
```

This tool allows agents to:
- Create new memories
- Update existing memories
- Delete outdated memories
- Organize memories by category

### Memory Search Tool

```python
create_search_memory_tool(namespace=namespace, store=store)
```

This tool enables agents to:
- Search for relevant memories
- Filter by namespace or content
- Retrieve context for current conversations
- Access shared knowledge

## Memory Types

### 1. Conversation Memory

The system automatically stores conversations for future reference:

```python
# Store conversation in memory
conversation_content = f"User asked: {message}\nAssistant replied: {response}"
self.store.put((namespace, "conversations"), conversation_id, {"memory": conversation_content})
self.store.put((namespace, "global_conversations"), conversation_id, {"memory": conversation_content})
```

This enables:
- Recalling past interactions
- Maintaining context across sessions
- Analyzing conversation patterns

### 2. Preference Memory

The system extracts and stores user preferences:

```python
# Extract preferences using LLM
extraction_prompt = f"""
Extract any user preferences or personal information from this conversation:
User: {message}
Assistant: {response}
"""

# Store preferences
memory_content = f"User preference: {key} = {value}"
self.store.put((namespace, "preferences"), memory_id, memory_content)
```

This enables:
- Personalized interactions
- Remembering user details
- Adapting to user preferences

### 3. Agent Instructions

The system stores and updates agent instructions:

```python
# Store improved instructions
store.put(namespace, key=agent_name, value={"instructions": improved_instructions})
```

This enables:
- Dynamic agent behavior
- Self-improvement over time
- Adaptation to user needs

## Self-Improvement Mechanism

### Periodic Reflection

The system triggers reflection periodically:

```python
def _maybe_trigger_reflection(self):
    # Check if we should reflect (every 10 messages)
    if message_counter % 10 == 0:
        # Create context for reflection
        reflection_context = {
            "agent_name": "main_agent",
            "user_id": user_id,
            "store": self.store
        }
        
        # Use the reflect_and_improve tool
        improvement_summary = reflect_and_improve("", reflection_context)
```

This enables:
- Continuous improvement
- Learning from interactions
- Adaptation to usage patterns

### User-Triggered Improvement

Users can provide explicit feedback:

```python
@app.command("/improve")
def handle_improve_command(ack, body, client):
    # Get the user ID and feedback text
    user_id = body["user_id"]
    feedback = body["text"]
    
    # Use the reflect_and_improve tool with explicit feedback
    improvement_summary = reflect_and_improve(feedback, reflection_context)
```

This enables:
- Direct user feedback
- Targeted improvements
- User-guided learning

## Implementation Details

### Memory Tool Creation

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

### Memory Tool Distribution

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

### Reflection Implementation

The `reflect_and_improve` tool analyzes past interactions and updates agent instructions:

```python
def reflect_and_improve(feedback: str = "", opts: Annotated[dict, InjectedToolArg] = None) -> str:
    # Get the current agent name from the context
    agent_name = opts.get("agent_name", "unknown_agent")
    user_id = opts.get("user_id", "default_user")
    
    # Create namespace for storing agent instructions
    namespace = (f"user:{user_id}", "agent_instructions")
    
    # Get the store from opts
    store = opts.get("store")
    
    # Try to get current instructions
    current_instructions = store.get(namespace, key=agent_name)
    
    # Get recent conversations from memory to analyze
    agent_namespace = (f"user:{user_id}", agent_name)
    conversations = store.list_keys(agent_namespace)
    
    # Use the LLM to generate improved instructions
    reflection_prompt = f"""
    You are an AI improvement specialist. Your task is to analyze recent interactions and update an agent's instructions to improve its performance.
    
    CURRENT INSTRUCTIONS:
    {current_instructions}
    
    RECENT INTERACTIONS:
    {conversation_context}
    
    USER FEEDBACK (if any):
    {feedback}
    
    Based on the above, please:
    1. Identify patterns in how the agent is performing
    2. Note any areas where the agent could improve
    3. Create updated instructions that address these improvements
    4. Preserve the core functionality and purpose of the agent
    """
    
    # Store the improved instructions
    store.put(namespace, key=agent_name, value={"instructions": improved_instructions})
```

## Best Practices

### 1. Memory Organization

- Use consistent namespace patterns
- Store related information together
- Use descriptive keys for easy retrieval

### 2. Memory Retrieval

- Search for relevant context before responding
- Use specific namespaces for targeted searches
- Combine memories from different sources when appropriate

### 3. Memory Management

- Store important information explicitly
- Update outdated information
- Remove irrelevant or incorrect memories

### 4. Self-Improvement

- Analyze conversation patterns
- Identify areas for improvement
- Update agent instructions based on feedback

## Integration with LangGraph

The memory system integrates seamlessly with LangGraph:

```python
# Compile the workflow with checkpointer and store
self.model = workflow.compile(
    name=f"slack_assistant_{supervisor_id}",
    checkpointer=self.checkpointer,
    store=self.store
)
```

This integration enables:
- Persistent state across invocations
- Shared memory between agents
- Context-aware responses
- Continuous improvement through reflection 
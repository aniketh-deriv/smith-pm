# Manager Implementation

The Manager component is the core orchestrator of the Agentic Office PM system, handling AI model interactions, tool execution, and conversation state management.

## Overview

The `LangGraphManager` class serves as the central coordinator, managing:
- AI model initialization and configuration
- Tool execution and workflow
- Conversation state and context
- Message processing and response generation

## Core Components

### 1. LangGraphManager Class

```python
class LangGraphManager:
    def __init__(self, slack_client: Any = None, checkpointer: Any = None):
        self.external_params = {}
        self.model = None
        self.messages = []
        self.slack_client = slack_client
        self.current_thread = {}
        self.store = None
```

The manager maintains conversation state, handles the AI model, and coordinates tool execution.

### 2. Model Initialization

```python
def get_llm_model() -> Any:
    """
    Get the appropriate LLM model based on environment variables.
    """
```

This function initializes the language model based on environment variables:
- Uses `OPENAI_MODEL_NAME` for model selection
- Connects to `API_BASE_URL` if specified
- Configures appropriate parameters for the model

## Key Features

### 1. Agent Creation

```python
def _create_agent(self) -> Any:
    """
    Initialize the AI agent with tools and system message.
    """
```

Features:
- Model initialization
- Tool binding
- System message loading
- Conversation context setup

### 2. Tool Execution

```python
def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
    """
    Execute tool calls and return their messages.
    """
```

Features:
- Tool validation
- Parameter handling
- Error management
- Result formatting

### 3. Message Processing

```python
def process_message(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Process a message using the provided agent.
    """
```

Features:
- Conversation tracking
- Tool execution
- Response generation
- Error handling

### 4. User Preference Detection

The manager includes functionality to detect and store user preferences from conversations:

```python
# Extract user preferences from conversation
preferences = json.loads(content)

# Store preferences in memory store
for key, value in preferences.items():
    memory_content = f"User preference: {key} = {value}"
    memory_id = f"pref_{key}_{int(time.time())}"
    
    # Store in memory
    self.store.put((namespace, "preferences"), key, value)
```

This allows the system to remember user preferences and adapt responses accordingly.

## Conversation Management

### 1. Conversation Instances

```python
conversation_managers: Dict[str, LangGraphManager] = {}
```

The system maintains a dictionary of conversation managers, indexed by conversation ID (typically the Slack thread ID).

### 2. Manager Access

```python
def get_or_create_manager(conversation_id: str, slack_client: Any = None) -> LangGraphManager:
    """
    Get an existing manager or create a new one.
    """
```

This function:
- Retrieves an existing manager if available
- Creates a new manager if needed
- Initializes the manager with the Slack client
- Returns the appropriate manager instance

### 3. Manager Retrieval

```python
def get_manager(conversation_id: str) -> Optional[LangGraphManager]:
    """
    Get an existing manager by conversation ID.
    """
```

This function retrieves an existing manager without creating a new one if it doesn't exist.

## Tool Approval

The system includes a tool approval node that can be used to implement approval workflows:

```python
def tool_approval_node(self, state):
    """
    Node for tool approval in the graph.
    """
```

However, in the current implementation, this is configured to bypass the approval process:

```python
def should_approve(state):
    # Always bypass approval process
    return True
```

## Error Handling

1. **Logging:**
```python
logger = logging.getLogger(__name__)
```

2. **Error Management:**
- Exception catching
- Error reporting
- State recovery
- User notification

## Best Practices

### 1. State Management
- Maintain conversation context
- Track thread information
- Handle tool execution state
- Store user preferences

### 2. Tool Execution
- Validate tool calls
- Handle parameters
- Log execution details
- Format results appropriately

### 3. Error Handling
- Comprehensive logging
- Graceful error recovery
- User-friendly messages
- State preservation

### 4. Performance
- Efficient model usage
- Optimized tool execution
- State caching
- Resource management

## Configuration

### Environment Variables
```bash
OPENAI_MODEL_NAME=gpt-4o        # AI model selection
API_BASE_URL=your-api-base-url   # Optional custom API endpoint
```

### System Message
- Loaded from system.md
- Defines AI behavior
- Sets conversation context
- Configures tool usage

## Testing

1. **Unit Testing:**
- Test tool execution
- Verify approval flow
- Check error handling
- Validate state management

2. **Integration Testing:**
- Test with Slack
- Verify conversation flow
- Check tool integration
- Validate approvals

3. **Performance Testing:**
- Monitor resource usage
- Check response times
- Verify state handling
- Test concurrent conversations

## Memory Integration

The `LangGraphManager` integrates with LangMem to provide sophisticated memory capabilities:

```python
# Initialize the store for LangGraph checkpointing
self.store = InMemoryStore()
```

### Memory Namespaces

The manager creates a hierarchical namespace structure:

```python
# Create a shared team namespace for all agents
team_namespace = f"user:{user_id}"

# Create agent-specific namespaces
main_agent_namespace = (team_namespace, "main_agent")
channel_explorer_namespace = (team_namespace, "channel_explorer")
user_activity_namespace = (team_namespace, "user_activity")
message_search_namespace = (team_namespace, "message_search")
```

This enables:
- User-specific memory isolation
- Agent-specific private memories
- Shared memories accessible to all agents

### Memory Tools

The manager creates specialized memory tools for each agent:

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

These tools are distributed to agents based on their roles, giving each agent:
1. Its own private memory space
2. Access to the shared memory space
3. The ability to store and retrieve information across different namespaces

## Self-Improvement Mechanism

The manager implements a self-improvement mechanism that allows agents to evolve over time:

```python
def _maybe_trigger_reflection(self):
    """Periodically trigger agent reflection to improve performance."""
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

### Periodic Reflection

The system automatically triggers reflection:
- After every 10 messages for the main agent
- Every 30 messages for all specialized agents

### User-Triggered Improvement

Users can provide explicit feedback through the `/improve` Slack command:

```python
@app.command("/improve")
def handle_improve_command(ack, body, client):
    # Get the user ID and feedback text
    user_id = body["user_id"]
    feedback = body["text"]
    
    # Use the reflect_and_improve tool with explicit feedback
    improvement_summary = reflect_and_improve(feedback, reflection_context)
```

### Instruction Management

Agent instructions are stored in the memory system:
- Namespace: `(f"user:{user_id}", "agent_instructions")`
- Key: Agent name (e.g., "main_agent")
- Value: JSON object with instructions

This allows instructions to evolve over time based on usage patterns and feedback.

from typing import Dict, Any, List, Optional
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from tools import list_channels, get_channel_info, list_channel_members

logger = logging.getLogger(__name__)

def create_agents(llm: Any, memory_tools: Optional[Dict[str, List[Any]]] = None) -> Dict[str, Any]:
    """Create specialized agents for different tasks."""
    
    # Base system prompt for all agents
    base_system = """You are a helpful AI assistant for Slack. You can answer questions about Slack channels, users, and messages.
    Always be polite, helpful, and concise in your responses.
    If you don't know something, say so rather than making up information.
    You can also use the search_memory tool to retrieve past conversations.
    
    You have the ability to improve yourself over time by reflecting on your interactions.
    Use the reflect_and_improve tool when:
    - You notice patterns in user questions you could handle better
    - You receive explicit feedback from users
    - You want to improve your capabilities in a specific area
    
    """
    
    # Get agent-specific instructions from memory store
    def get_agent_instructions(store, user_id, agent_name):
        try:
            namespace = (f"user:{user_id}", "agent_instructions")
            instructions = store.get(namespace, key=agent_name)
            if instructions and len(instructions) > 0:
                return instructions[0].value.get("instructions", "")
        except Exception as e:
            logger.error(f"Error retrieving instructions for {agent_name}: {str(e)}")
        return None
    
    # Get the store from memory_tools if available
    store = None
    if memory_tools and "main_agent" in memory_tools and memory_tools["main_agent"]:
        for tool in memory_tools["main_agent"]:
            if hasattr(tool, "store"):
                store = tool.store
                break
    
    # Default user_id
    user_id = "default_user"
    
    # Supervisor agent
    supervisor_instructions = get_agent_instructions(store, user_id, "main_agent") if store else None
    if not supervisor_instructions:
        supervisor_instructions = """
        You are the main supervisor agent that coordinates all interactions.
        You can answer general questions directly or delegate to specialized agents for specific tasks.
        You can also use the search_memory tool to retrieve past conversations.
        
        IMPORTANT: When asked about previous conversations or what the user has asked before,
        use the search_memory tool to retrieve past conversations. Always check memory first
        before saying you don't know about past interactions.
        
        For questions about:
        - Slack channels: Use the channel explorer agent
        - User activity: Use the user activity agent
        - Specific messages or content: Use the message search agent
        - Past conversations: Use the search_memory tool
         
        Only transfer to specialized agents when necessary. For simple questions, answer directly.
        """
    
    supervisor_prompt = ChatPromptTemplate.from_messages([
        ("system", base_system + supervisor_instructions),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Channel explorer agent
    channel_explorer_instructions = get_agent_instructions(store, user_id, "channel_explorer") if store else None
    if not channel_explorer_instructions:
        channel_explorer_instructions = """
        You are a specialized agent for exploring Slack channels.
        You can also use the search_memory tool to retrieve past conversations.
        You can provide information about:
        - Channel listings
        - Channel purposes
        - Channel membership
        - Channel activity
        
        Always format channel names with the # prefix (e.g., #general).
        When asked to list channels, use the list_channels tool to get real channel data.
        For information about a specific channel, use the get_channel_info tool.
        To list members of a channel, use the list_channel_members tool.
        Never make up channel names - only report real channels from the tools.
        
        If you encounter any errors when using tools, explain the issue clearly to the user.
        """
    
    channel_explorer_prompt = ChatPromptTemplate.from_messages([
        ("system", base_system + channel_explorer_instructions),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # User activity agent
    user_activity_instructions = get_agent_instructions(store, user_id, "user_activity") if store else None
    if not user_activity_instructions:
        user_activity_instructions = """
        You are a specialized agent for analyzing user activity in Slack.
        You can also use the search_memory tool to retrieve past conversations.
        You can provide information about:
        - Which channels a user is active in
        - Recent messages from a user
        - User participation patterns
        
        When presenting user information, be concise and organized.
        Format the information in a clear, readable way.
        """
    
    user_activity_prompt = ChatPromptTemplate.from_messages([
        ("system", base_system + user_activity_instructions),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Message search agent
    message_search_instructions = get_agent_instructions(store, user_id, "message_search") if store else None
    if not message_search_instructions:
        message_search_instructions = """
        You are a specialized agent for searching and analyzing Slack messages.
        You can also use the search_memory tool to retrieve past conversations.
        You can help with:
        - Finding specific messages
        - Summarizing conversations
        - Extracting key information from threads
        
        Present message content with proper formatting, including timestamps and authors when available.
        """
    
    message_search_prompt = ChatPromptTemplate.from_messages([
        ("system", base_system + message_search_instructions),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Prepare tools for each agent
    supervisor_tools = [
        transfer_to_channel_explorer,
        transfer_to_user_activity,
        transfer_to_message_search
    ]
    
    # Add Slack tools to channel explorer
    channel_explorer_tools = [
        list_channels,
        get_channel_info,
        list_channel_members,
        transfer_back_to_supervisor
    ]
    
    user_activity_tools = [
        transfer_back_to_supervisor
    ]
    
    message_search_tools = [
        transfer_back_to_supervisor
    ]
    
    # Add memory tools if provided
    if memory_tools:
        if "main_agent" in memory_tools:
            supervisor_tools.extend(memory_tools["main_agent"])
        if "channel_explorer" in memory_tools:
            channel_explorer_tools.extend(memory_tools["channel_explorer"])
        if "user_activity" in memory_tools:
            user_activity_tools.extend(memory_tools["user_activity"])
        if "message_search" in memory_tools:
            message_search_tools.extend(memory_tools["message_search"])
    
    # Create the agents with names and tools
    main_agent = create_react_agent(
        model=llm,
        tools=supervisor_tools,
        prompt=supervisor_prompt,
        name="main_agent"
    )
    
    channel_explorer_agent = create_react_agent(
        model=llm,
        tools=channel_explorer_tools,
        prompt=channel_explorer_prompt,
        name="channel_explorer"
    )
    
    user_activity_agent = create_react_agent(
        model=llm,
        tools=user_activity_tools,
        prompt=user_activity_prompt,
        name="user_activity"
    )
    
    message_search_agent = create_react_agent(
        model=llm,
        tools=message_search_tools,
        prompt=message_search_prompt,
        name="message_search"
    )
    
    # Return the agents
    return {
        "main_agent": main_agent,
        "channel_explorer": channel_explorer_agent,
        "user_activity": user_activity_agent,
        "message_search": message_search_agent
    }

# Define transfer tools
@tool
def transfer_to_channel_explorer(tool_input: str) -> str:
    """Transfer control to the channel explorer agent to look up information about Slack channels."""
    return "Transferring to channel explorer agent"

@tool
def transfer_to_user_activity(tool_input: str) -> str:
    """Transfer control to the user activity agent to look up information about a Slack user's activity."""
    return "Transferring to user activity agent"

@tool
def transfer_to_message_search(tool_input: str) -> str:
    """Transfer control to the message search agent to look up specific messages or conversations."""
    return "Transferring to message search agent"

@tool
def transfer_back_to_supervisor(tool_input: str) -> str:
    """Transfer control back to the supervisor agent."""
    return "Transferring back to supervisor agent"

# Default user
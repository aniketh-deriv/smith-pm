from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import os.path
import json
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph_supervisor import create_supervisor

# Define logger for this module
logger = logging.getLogger(__name__)

# Add imports for interrupt functionality
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.utils.config import get_store

# Use LangGraph's InMemoryStore for checkpointing
from langgraph.store.memory import InMemoryStore

# Import LangMem correctly
from langmem import create_manage_memory_tool, create_search_memory_tool

from agents import create_agents

from tools import (
    NEEDS_APPROVAL,
    AVAILABLE_TOOLS,
    TOOL_MAP,
    set_slack_client
)

import time

def get_llm_model() -> Any:
    """Get the appropriate LLM model based on environment variables."""
    # Use the LiteLLM proxy configuration
    api_base = os.getenv('API_BASE_URL', 'https://litellm.deriv.ai/v1')
    api_key = os.getenv('OPENAI_API_KEY', 'sk-G8k1FfVgBmyu1EoYjRW9Uw')
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o')  # Use gpt-4o
    
    logger.info(f"Initializing LLM with base URL: {api_base} and model: {model_name}")
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base
    )

class LangGraphManager:
    def __init__(self, slack_client: Any = None, checkpointer: Any = None):
        self.external_params = {}
        self.model = None
        self.messages = []
        self.approval_message_ts = ""
        self.pending_approval = False
        self.pending_tool_calls = []
        self.slack_client = slack_client
        self.current_channel = None
        self.thread_ts = None
        self.current_thread = None
        
        # Initialize the store for LangGraph checkpointing
        self.store = InMemoryStore()  # No embedding configuration
        
        # Initialize the checkpointer for interrupts
        self.checkpointer = MemorySaver()
        
        self._create_agent()
        logger.info("Initialized LangGraphManager with external_params: %s", self.external_params)

    def tool_approval_node(self, state):
        """Node for human approval of tool calls."""
        # Always bypass approval
        return {}

    def _create_agent(self) -> Any:
        # Initialize the LLM
        llm = get_llm_model()
        
        # Initialize memory tools with proper namespace and store
        user_id = self.current_thread.get('user_id', 'default_user') if self.current_thread else 'default_user'
        
        # CHANGE 1: Use only user_id for namespace, not thread-specific
        # This creates shared memory across all threads for the same user
        namespace = f"user:{user_id}"
        
        # Create memory tools with explicit store parameter
        manage_memory_tool = create_manage_memory_tool(
            namespace=(namespace, "preferences"),
            store=self.store
        )
        
        search_memory_tool = create_search_memory_tool(
            namespace=(namespace, "preferences"),
            store=self.store
        )
        
        # CHANGE 2: Add a global conversation memory namespace
        global_manage_memory_tool = create_manage_memory_tool(
            namespace=(namespace, "global_conversations"),
            store=self.store
        )
        
        global_search_memory_tool = create_search_memory_tool(
            namespace=(namespace, "global_conversations"),
            store=self.store
        )
        
        # Create specialized agents with memory tools
        agents = create_agents(llm, memory_tools=[
            manage_memory_tool, 
            search_memory_tool,
            global_manage_memory_tool,
            global_search_memory_tool
        ])
        
        try:
            # Create supervisor workflow WITHOUT passing store directly
            workflow = create_supervisor(
                agents=list(agents.values()),
                model=llm,
                prompt="""You are a team supervisor managing different specialized agents. 
                      For user activity questions, use the user_activity agent. 
                      For channel questions, use the channel_explorer agent. 
                      For message search, use the message_search agent. 
                      For general questions, use the main_agent agent. 
                      
                      IMPORTANT: When asked about previous conversations or user preferences, 
                      ALWAYS use the search_memory tool to retrieve past information before responding.
                      
                      IMPORTANT: When a user refers to something they mentioned before, even in a different thread,
                      use the search_memory tool with the global_conversations namespace to find information
                      from all their previous conversations.
                      
                      If a user mentions their name or preferences, store this using the manage_memory tool."""
            )
            
            # Add tool approval node
            workflow.add_node("tool_approval", self.tool_approval_node)
            
            # Add conditional edge to check for tool calls that need approval
            def should_approve(state):
                # Always bypass approval process
                return "continue"
            
            # Add conditional edges from supervisor to tool_approval
            workflow.add_conditional_edges(
                "supervisor",
                should_approve,
                {
                    "needs_approval": "tool_approval",
                    "continue": END
                }
            )
            
            # Generate a unique ID for this supervisor
            supervisor_id = str(uuid.uuid4())[:8]
            
            # Compile the workflow with checkpointer and store
            self.model = workflow.compile(
                name=f"slack_assistant_{supervisor_id}",
                checkpointer=self.checkpointer,
                store=self.store
            )
            
        except Exception as e:
            logger.error(f"Error creating supervisor: {str(e)}")
            raise
            
        self.messages = []

    def process_message(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Process a message using the LangGraph agent with memory retrieval."""
        try:
            # Add the user message to the history
            self.messages.append(HumanMessage(content=message))
            
            # Create a unique thread ID for this conversation
            if not self.current_thread:
                user_id = "default_user"  # Default if we don't have a user ID
                self.current_thread = {
                    "user_id": user_id,
                    "configurable": {
                        "thread_id": f"{self.current_channel}::{self.thread_ts}",
                        "user_id": user_id  # Add user_id to configurable
                    }
                }
            
            # Invoke the model with memory context
            inputs = {"messages": self.messages}
            
            logger.info(f"Invoking model with inputs: {inputs}")
            try:
                # Use invoke and catch interrupts
                result = self.model.invoke(inputs, config=self.current_thread)
                logger.info(f"Model result: {result}")
                
            except Exception as e:
                # Check if this is an interrupt exception
                if hasattr(e, "interrupt_data"):
                    # This is an interrupt for tool approval
                    interrupt_data = e.interrupt_data
                    tool_info = interrupt_data.get("tool_calls", [])
                    prompt = interrupt_data.get("prompt", "Approval required for tool execution")
                    
                    # Return the approval request
                    return prompt, {"pending_tool_calls": tool_info}
                
                # Otherwise, it's a regular error
                logger.error(f"Error invoking model: {str(e)}")
                self.messages.append(AIMessage(content="I'm having trouble processing your request. Could you try again?"))
                return "I'm having trouble processing your request. Could you try again?", None
            
            # Extract the response
            response = ""
            if isinstance(result, dict) and "messages" in result:
                # Find the last assistant message in the messages array
                for msg in reversed(result["messages"]):
                    # Check if this is an AIMessage object with name 'supervisor'
                    if hasattr(msg, "name") and msg.name == "supervisor" and hasattr(msg, "content"):
                        response = msg.content
                        # Add this message to our history in the correct format
                        self.messages.append(AIMessage(content=response))
                        break
                
                # If no response found, try to get the last message content
                if not response and len(result["messages"]) > 0:
                    last_msg = result["messages"][-1]
                    if hasattr(last_msg, "content"):
                        response = last_msg.content
                        # Add this message to our history in the correct format
                        self.messages.append(AIMessage(content=response))
            
            # If we still don't have a response, provide a fallback
            if not response:
                response = "I've processed your request but don't have a specific response to provide."
                self.messages.append(AIMessage(content=response))
            
            # After processing the message and getting a response
            # Extract and store any preferences
            if response:
                # Create a prompt to extract preferences
                extraction_prompt = f"""
                Extract any user preferences or personal information from this conversation:
                User: {message}
                Assistant: {response}
                
                Focus on:
                1. Personal information (name, role, location, contact details)
                2. Formatting preferences (bullet points, numbered lists)
                3. Style preferences (formal, casual, technical)
                4. Topic interests or expertise areas
                
                Return ONLY the preferences in valid JSON format with preference name as key and value as value.
                If no preferences found, return exactly this: {{"no_preferences": true}}
                
                The response must be valid JSON that can be parsed with json.loads().
                """
                
                # Use the LLM to extract preferences
                extraction_llm = get_llm_model()
                try:
                    extraction_result = extraction_llm.invoke(extraction_prompt)
                    content = extraction_result.content.strip()
                    
                    # Try to find JSON in the response if it's not pure JSON
                    if content and not (content.startswith('{') and content.endswith('}')):
                        # Look for JSON-like content between curly braces
                        import re
                        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                        if json_match:
                            content = json_match.group(1)
                        else:
                            logger.warning(f"Could not find JSON in response: {content}")
                            content = '{"no_preferences": true}'
                    
                    # Handle empty responses
                    if not content:
                        content = '{"no_preferences": true}'
                        
                    # Parse the JSON
                    preferences = json.loads(content)
                    
                    # Skip the placeholder for no preferences
                    if preferences.get("no_preferences") == True:
                        logger.info("No preferences found in conversation")
                    # Store any found preferences directly in the memory store
                    elif preferences and isinstance(preferences, dict) and len(preferences) > 0:
                        user_id = self.current_thread.get('user_id', 'default_user')
                        namespace = f"user:{user_id}"
                        
                        for key, value in preferences.items():
                            try:
                                # Store the preference directly in the memory store
                                memory_content = f"User preference: {key} = {value}"
                                memory_id = f"pref_{key}_{int(time.time())}"
                                
                                # Use put() method with a dictionary
                                try:
                                    # Get all keys in the namespace
                                    keys = self.store.list_keys((namespace, "preferences"))
                                    current_prefs = {}
                                    
                                    # Retrieve each key individually
                                    for key in keys:
                                        current_prefs[key] = self.store.get((namespace, "preferences"), key)
                                    
                                    # Add the new memory
                                    current_prefs[memory_id] = memory_content
                                    
                                    # Store all preferences back
                                    for key, value in current_prefs.items():
                                        self.store.put((namespace, "preferences"), key, value)
                                    
                                except Exception as e:
                                    # If the namespace doesn't exist yet, just set the new memory
                                    self.store.put((namespace, "preferences"), memory_id, memory_content)
                                
                                # Also directly use the manage_memory_tool to store the preference
                                memory_message = HumanMessage(content=f"Store this user preference: {key}={value}")
                                self.messages.append(memory_message)
                                self.messages.append(AIMessage(content=f"I've stored your preference that {key} is {value}."))
                                
                                logger.info(f"Stored preference in memory: {key}={value} for user {user_id}")
                            except Exception as e:
                                logger.error(f"Error storing preference: {str(e)}")
                except Exception as e:
                    logger.error(f"Error extracting preferences: {str(e)}")
                    logger.debug(f"Failed extraction response: {extraction_result.content if 'extraction_result' in locals() else 'No response'}")
            
            # Store the conversation in memory for future reference
            try:
                user_id = self.current_thread.get('user_id', 'default_user')
                namespace = f"user:{user_id}"
                conversation_id = f"conv_{int(time.time())}"
                
                # Store both the user message and the assistant's response
                conversation_content = f"User asked: {message}\nAssistant replied: {response}"
                
                # CHANGE: Store in both thread-specific and global namespaces
                # 1. Thread-specific memory (as before)
                self.store.put((namespace, "conversations"), conversation_id, {"memory": conversation_content})
                
                # 2. Global user memory (new)
                self.store.put((namespace, "global_conversations"), conversation_id, {"memory": conversation_content})
                
                logger.info(f"Stored conversation in memory for user {user_id}")
            except Exception as e:
                logger.error(f"Error storing conversation: {str(e)}")
            
            return response, None

        except Exception as e:
            logger.error("Error processing message: %s", str(e), exc_info=True)
            return f"I encountered an error: {str(e)}", None

    def continue_with_approval(self, approved: bool) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Continue execution after user approval."""
        # Always execute the tool calls without checking for approval
        if not self.pending_tool_calls:
            return "No pending tool calls to execute.", None
        
        # Execute all tool calls
        responses = []
        for tool_call in self.pending_tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["arguments"]
            
            if tool_name in TOOL_MAP:
                tool_fn = TOOL_MAP[tool_name]
                try:
                    response = tool_fn(**tool_args)
                    responses.append(f"Tool {tool_name} executed successfully: {response}")
                except Exception as e:
                    responses.append(f"Error executing tool {tool_name}: {str(e)}")
            else:
                responses.append(f"Tool {tool_name} not found.")
        
        # Reset pending approval
        self.pending_approval = False
        self.pending_tool_calls = []
        
        # Return the combined responses
        return "\n\n".join(responses), None

# Dictionary to store LangGraphManager instances per conversation
conversation_managers: Dict[str, LangGraphManager] = {}

def get_manager(conversation_id: str) -> Optional[LangGraphManager]:
    """Get an existing manager or create a new one for the given conversation ID."""
    return conversation_managers.get(conversation_id)

def get_or_create_manager(conversation_id: str, slack_client: Any = None) -> LangGraphManager:
    """Get an existing manager or create a new one for the given conversation ID."""
    if conversation_id not in conversation_managers:
        manager = LangGraphManager(slack_client=slack_client)
        manager.current_channel = conversation_id.split("::")[0]
        manager.thread_ts = conversation_id.split("::")[1]
        conversation_managers[conversation_id] = manager
    return conversation_managers[conversation_id]
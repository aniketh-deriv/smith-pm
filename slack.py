import os
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from typing import Any
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

from manager import LangGraphManager, get_or_create_manager, get_manager
from tools import set_slack_client, reflect_and_improve

# Log environment variables (without revealing full tokens)
bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
app_token = os.environ.get("SLACK_APP_TOKEN", "")
logger.info(f"SLACK_BOT_TOKEN present: {bool(bot_token)}")
logger.info(f"SLACK_APP_TOKEN present: {bool(app_token)}")

# Initialize the Slack app
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

# Log configuration
logger.info(f"SLACK_BOT_TOKEN present: {bool(slack_bot_token)}")
logger.info(f"SLACK_SIGNING_SECRET present: {bool(slack_signing_secret)}")

# Initialize app with available credentials
if slack_signing_secret:
    app = App(
        token=slack_bot_token,
        signing_secret=slack_signing_secret
    )
else:
    # Fall back to token-only initialization for development
    logger.warning("SLACK_SIGNING_SECRET not found. Using token-only initialization.")
    app = App(token=slack_bot_token)

# Set the global Slack client
set_slack_client(app.client)
logger.info("Set global Slack client")

@app.event("app_mention")
def handle_app_mention_events(body):
    """Handle app mention events."""
    logger.info(f"App mention event: {body}")
    
    try:
        event = body.get("event", {})
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        user_id = event.get("user")
        
        # Get the bot user ID
        bot_user_id = app.client.auth_test()["user_id"]
        
        # Remove the bot mention from the text
        text = text.replace(f"<@{bot_user_id}>", "").strip()
        
        # Create a unique conversation ID
        conversation_id = f"{channel_id}::{thread_ts}"
        
        # Get or create a manager for this conversation
        manager = get_or_create_manager(conversation_id, app.client)
        
        # Set user ID in the thread context
        if not manager.current_thread:
            manager.current_thread = {
                "user_id": user_id,
                "configurable": {
                    "thread_id": conversation_id,
                    "user_id": user_id
                }
            }
        
        # Process the message
        response, metadata = manager.process_message(text)
        
        # Automatically approve any tool calls
        if metadata and "pending_tool_calls" in metadata:
            # Auto-approve all tool calls
            response, _ = manager.continue_with_approval(True)
        
        # Send the response to Slack
        if response:
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=response
            )
        
    except Exception as e:
        logger.error(f"Error handling app mention event: {str(e)}", exc_info=True)
        app.client.chat_postMessage(
            channel=body["event"]["channel"],
            thread_ts=body["event"]["thread_ts"] if "thread_ts" in body["event"] else body["event"]["ts"],
            text=f"Error processing message: {str(e)}"
        )

@app.event("message")
def handle_message_events(body):
    """Handle message events."""
    logger.info(f"Message event: {body}")
    
    try:
        event = body.get("event", {})
        
        # Skip messages from bots to avoid infinite loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return
            
        # Skip app_mention events - they're handled by the app_mention handler
        if "app_mention" in event.get("type", ""):
            logger.info("Skipping message event that is also an app_mention")
            return
        
        # Skip messages that contain a mention of the bot - these will be handled by app_mention
        bot_user_id = app.client.auth_test()["user_id"]
        if f"<@{bot_user_id}>" in event.get("text", ""):
            logger.info(f"Skipping message that mentions the bot: {event.get('text', '')}")
            return
        
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        user_id = event.get("user")
        
        # Check if this is a reply in a thread
        if "thread_ts" in event:
            # Create a unique conversation ID
            conversation_id = f"{channel_id}::{event['thread_ts']}"
            
            # Get the manager for this conversation
            manager = get_manager(conversation_id)
            
            # Only respond if we have a manager for this thread (meaning the bot is part of it)
            if manager:
                # Set user ID in the thread context if not already set
                if not manager.current_thread:
                    manager.current_thread = {
                        "user_id": user_id,
                        "configurable": {
                            "thread_id": conversation_id,
                            "user_id": user_id
                        }
                    }
                
                # Process the message normally
                response, metadata = manager.process_message(text)
                
                # Automatically approve any tool calls
                if metadata and "pending_tool_calls" in metadata:
                    response, _ = manager.continue_with_approval(True)
                
                # Send the response to Slack
                if response:
                    app.client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=thread_ts,
                        text=response
                    )
            return
        
        # Check if this is a DM
        is_dm = event.get("channel_type") == "im"
        
        # Only respond to DMs (not to regular messages in channels)
        if not is_dm:
            logger.info("Skipping non-DM message")
            return
        
        # Create a unique conversation ID
        conversation_id = f"{channel_id}::{thread_ts}"
        
        # Get or create a manager for this conversation
        manager = get_or_create_manager(conversation_id, app.client)
        
        # Set user ID in the thread context
        if not manager.current_thread:
            manager.current_thread = {
                "user_id": user_id,
                "configurable": {
                    "thread_id": conversation_id,
                    "user_id": user_id
                }
            }
        
        # Process the message
        response, metadata = manager.process_message(text)
        
        # Automatically approve any tool calls
        if metadata and "pending_tool_calls" in metadata:
            # Auto-approve all tool calls
            response, _ = manager.continue_with_approval(True)
        
        # Send the response to Slack
        if response:
            logger.info(f"Sending response to Slack: {response[:100]}...")
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=response
            )
        
    except Exception as e:
        logger.error(f"Error handling message event: {str(e)}", exc_info=True)
        app.client.chat_postMessage(
            channel=body["event"]["channel"],
            thread_ts=body["event"]["thread_ts"] if "thread_ts" in body["event"] else body["event"]["ts"],
            text=f"Error processing message: {str(e)}"
        )

@app.command("/improve")
def handle_improve_command(ack, body, client):
    """Handle the /improve command to provide feedback for agent improvement."""
    ack()
    
    try:
        # Get the user ID and feedback text
        user_id = body["user_id"]
        feedback = body["text"]
        
        # Get the channel ID
        channel_id = body["channel_id"]
        
        # Create a unique conversation ID for this feedback
        conversation_id = f"{channel_id}::{time.time()}"
        
        # Get or create a manager for this conversation
        manager = get_or_create_manager(conversation_id, client)
        
        # Set user ID in the thread context
        if not manager.current_thread:
            manager.current_thread = {
                "user_id": user_id,
                "configurable": {
                    "thread_id": conversation_id,
                    "user_id": user_id
                }
            }
        
        # Create context for reflection
        reflection_context = {
            "agent_name": "main_agent",  # Start with the main agent
            "user_id": user_id,
            "store": manager.store
        }
        
        # Use the reflect_and_improve tool with explicit feedback
        improvement_summary = reflect_and_improve(feedback, reflection_context)
        
        # Send a response to the user
        client.chat_postMessage(
            channel=channel_id,
            text=f"Thank you for your feedback! I've used it to improve:\n\n{improvement_summary}"
        )
        
    except Exception as e:
        logger.error(f"Error handling improve command: {str(e)}")
        client.chat_postMessage(
            channel=body["channel_id"],
            text=f"Error processing improvement feedback: {str(e)}"
        )

# Start the app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
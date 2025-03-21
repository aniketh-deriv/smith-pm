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

# At module level
processed_messages = {}

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
            logger.info(f"Sending to Slack - Length: {len(response)} chars")
            result = app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=response
            )
            logger.info(f"Slack API response: {result.get('ok')}")
        
    except Exception as e:
        logger.error(f"Error handling app mention event: {str(e)}", exc_info=True)
        app.client.chat_postMessage(
            channel=body["event"]["channel"],
            thread_ts=body["event"]["thread_ts"] if "thread_ts" in body["event"] else body["event"]["ts"],
            text=f"Error processing message: {str(e)}"
        )

@app.event("message")
def handle_message_events(body):
    """Handle message events with deduplication."""
    try:
        event = body.get("event", {})
        
        # Create a unique message identifier
        message_id = event.get("client_msg_id") or event.get("ts")
        
        # Skip if we've already processed this message
        if message_id in processed_messages:
            logger.info(f"Skipping already processed message {message_id}")
            return
            
        # Mark this message as processed
        processed_messages[message_id] = time.time()
        
        # Cleanup old processed messages (keep last 100)
        if len(processed_messages) > 100:
            # Remove oldest entries
            sorted_ids = sorted(processed_messages.items(), key=lambda x: x[1])
            for old_id, _ in sorted_ids[:len(processed_messages) - 100]:
                processed_messages.pop(old_id, None)
        
        # Get the bot ID of the message sender
        sender_bot_id = event.get("bot_id")
        
        # List of allowed bot IDs that Smith should respond to
        allowed_bot_ids = ["B08JP065D44"]  # Pentester bot ID from your logs
        
        # Skip messages from bots EXCEPT those in the allowed list
        if sender_bot_id and sender_bot_id not in allowed_bot_ids:
            return
        
        # Also skip if it's a system bot message
        if event.get("subtype") == "bot_message" and not sender_bot_id:
            return
            
        # Process the message as you normally would
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        
        # Create a user_id that indicates this is from a bot
        user_id = f"bot_{sender_bot_id}" if sender_bot_id else event.get("user")
        
        # Create a unique conversation ID
        conversation_id = f"{channel_id}::{thread_ts}"
        
        # Get or create a manager for this conversation
        manager = get_or_create_manager(conversation_id, app.client)
        
        # Set thread context
        manager.current_thread = {
            "user_id": user_id,
            "configurable": {
                "thread_id": conversation_id,
                "checkpoint_ns": "bot_communication",
                "checkpoint_id": conversation_id
            },
            "is_bot_communication": bool(sender_bot_id),
            "source_bot_id": sender_bot_id
        }
        
        # Process the message
        response, metadata = manager.process_message(text)
        
        # Send the response to Slack
        if response:
            logger.info(f"Sending response to {sender_bot_id or 'user'}: {response[:100]}...")
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=response
            )
    
    except Exception as e:
        logger.error(f"Error handling message event: {str(e)}")
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
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool, InjectedToolArg
from typing_extensions import Annotated
from datetime import datetime, timedelta
import logging
import os
import json
import time
from langchain_openai import ChatOpenAI
from collections import defaultdict

logger = logging.getLogger(__name__)

# Global variable to store channels
_cached_channels = None

# Dictionary to track tools that need approval
NEEDS_APPROVAL: Dict[str, bool] = {
    "create_channel": False,
    "archive_channel": False,
    "invite_user": False,
    "remove_user": False,
    "post_message": False,
    "delete_message": False,
}

# Global slack client variable that can be set from outside
_SLACK_CLIENT = None

def set_slack_client(client: Any) -> None:
    """Set the global Slack client."""
    global _SLACK_CLIENT
    _SLACK_CLIENT = client
    logger.info(f"Slack client set: {_SLACK_CLIENT is not None}")

def get_slack_client() -> Optional[Any]:
    """Get the global Slack client."""
    return _SLACK_CLIENT

def requires_approval(func):
    # This is now a no-op decorator - it doesn't actually require approval
    NEEDS_APPROVAL[func.__name__] = False
    return func

# At the beginning of the file, define it as a list
AVAILABLE_TOOLS = []

def enabled_tool(func):
    AVAILABLE_TOOLS.append(func)
    return func

class SlackMessageHandler:
    @staticmethod
    def _extract_message_text(msg: Dict[str, Any]) -> str:
        """
        Extract text from a Slack message, handling blocks and attachments properly.
        
        Args:
            msg: The Slack message object
            
        Returns:
            The extracted text content
        """
        # Initialize message text
        text = msg.get("text", "")
        original_text = text
        
        # Check for blocks that might contain text
        if msg.get("blocks"):
            block_texts = []
            for block in msg["blocks"]:
                if block.get("type") == "section":
                    # Handle both plain_text and mrkdwn types
                    block_text = block.get("text", {})
                    if isinstance(block_text, dict):
                        block_texts.append(block_text.get("text", ""))
                    else:
                        block_texts.append(block_text)
            if block_texts:
                text = "\n".join(block_texts)
        
        # Check for attachments
        if msg.get("attachments"):
            attachment_texts = []
            for attachment in msg["attachments"]:
                if attachment.get("text"):
                    attachment_texts.append(attachment["text"])
                elif attachment.get("fallback"):
                    attachment_texts.append(attachment["fallback"])
            if attachment_texts:
                text = text + "\n" + "\n".join(attachment_texts)
        
        # If we lost the text somehow, restore the original
        if not text.strip():
            return original_text
            
        return text

@enabled_tool
@tool
def get_accessible_channels(opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Get a list of public channels that are not archived.
    Returns a formatted string with each channel's name and ID on a new line.
    Uses a global cache to avoid expensive API calls on subsequent requests.
    
    Returns:
        A string with each line formatted as "channel_name: id" with "(current)" appended for the current channel
    """
    global _cached_channels
    current_channel = opts.get("current_channel") if opts else None
    
    # Use cached channels if available
    if _cached_channels is not None:
        channels = _cached_channels
    else:
        try:
            # Get all channels
            response = get_slack_client().conversations_list(
                exclude_archived=True,
                types="public_channel"
            )
            channels = response["channels"]
            _cached_channels = channels
        except Exception as e:
            logger.error(f"Error fetching channels: {str(e)}")
            return f"Error: Could not fetch channels: {str(e)}"
    
    # Format the output
    formatted_channels = []
    for channel in channels:
        channel_name = channel.get("name", "unknown")
        channel_id = channel.get("id", "unknown")
        is_current = " (current)" if channel_id == current_channel else ""
        formatted_channels.append(f"{channel_name}: {channel_id}{is_current}")
    
    return "\n".join(formatted_channels)

@enabled_tool
@tool
def get_recent_channel_messages(channel_ids: List[str], days: int, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Fetch messages from multiple channels from the last specified number of days including their threads.
    
    Args:
        channel_ids: List of channel IDs to fetch messages from (max 5 channels)
        days: Number of days to look back
    
    Returns:
        A formatted string containing messages and their threads in chronological order (oldest to newest),
        with timestamps and user information. Empty string if an error occurs.
    """
    if len(channel_ids) > 5:
        return "Error: Maximum 5 channels allowed"

    client = get_slack_client()
    all_formatted_text = []
    oldest_time = (datetime.now() - timedelta(days=days)).timestamp()
    
    try:
        for channel_id in channel_ids:
            logger.info(f"Starting to check channel {channel_id}")
            # Check if bot is in the channel
            channel_info = client.conversations_info(channel=channel_id)
            if not channel_info['channel'].get('is_member', False):
                # Bot is not in channel, try to join
                try:
                    client.conversations_join(channel=channel_id)
                    logger.info(f"Bot joined channel {channel_id}")
                except Exception as join_error:
                    logger.error(f"Failed to join channel: {str(join_error)}")
                    all_formatted_text.append(f"=== Channel {channel_id} ===\nUnable to access channel messages. Failed to join the channel.\n")
                    continue

            # Get channel history with pagination
            messages = []
            cursor = None
            
            while True:
                logger.info(f"Fetching more messages from channel {channel_id}" + (f" (cursor: {cursor})" if cursor else ""))
                # Get next page of results
                result = client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest_time),
                    cursor=cursor,
                    limit=1000  # Fetch maximum allowed per request
                )
                
                # Add messages from this page
                messages.extend(result.get('messages', []))
                
                # Rate limiting delay
                time.sleep(1)
                
                # Get cursor for next page
                cursor = result.get('response_metadata', {}).get('next_cursor')
                
                # If no cursor, we've reached the end
                if not cursor:
                    break
            messages_with_threads = []
            
            logger.info(f"Found {len(messages)} messages in channel {channel_id}, checking for threads")
            # Fetch threads for each message
            for msg in messages:
                message_data = {
                    'timestamp': msg.get('ts'),
                    'text': msg.get('text'),
                    'user': msg.get('user'),
                    'thread_messages': []
                }
                
                # If message has replies, fetch the thread
                if msg.get('thread_ts'):
                    thread_result = client.conversations_replies(
                        channel=channel_id,
                        ts=msg['thread_ts'],
                        limit=1000
                    )
                    message_data['thread_messages'] = thread_result.get('messages', [])[1:]  # Exclude parent message
                    
                messages_with_threads.append(message_data)
            
            # Reverse the list to get chronological order (oldest to newest)
            messages_with_threads.reverse()
            
            # Convert messages to text format
            channel_name = channel_info['channel']['name']
            formatted_text = [f"=== Channel #{channel_name} ({channel_id}) Message History ==="]
            for msg in messages_with_threads:
                # Format main message
                main_text = SlackMessageHandler._extract_message_text(msg)
                message_text = f"[{datetime.fromtimestamp(float(msg['timestamp']))}] User {msg['user']}: {main_text}"
                formatted_text.append(message_text)
                
                # Format thread replies
                if msg['thread_messages']:
                    formatted_text.append("Thread replies:")
                    for reply in msg['thread_messages']:
                        reply_text = SlackMessageHandler._extract_message_text(reply)
                        thread_text = f"  └─ [{datetime.fromtimestamp(float(reply['ts']))}] User {reply['user']}: {reply_text}"
                        formatted_text.append(thread_text)
                    formatted_text.append("")  # Add spacing between messages
            
            all_formatted_text.extend(formatted_text)
            all_formatted_text.append("")  # Add spacing between channel
        
        return "\n".join(all_formatted_text)
        
    except Exception as e:
        logger.error(f"Error fetching channel history: {str(e)}")
        return f"We faced an issue: {str(e)}"

@enabled_tool
@tool
def get_user_active_channels(user_identifier: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Get a list of channels where a specific user is active.
    
    Args:
        user_identifier: The Slack user ID or name to check
    
    Returns:
        A formatted string with each channel's name and activity level
    """
    try:
        # Check if we need to look up the user ID from a name
        user_id = user_identifier
        if not user_identifier.startswith("U"):  # Slack user IDs typically start with U
            # Try to look up the user ID from the name
            if opts and opts.get("slack_client"):
                client = opts["slack_client"]
                response = client.users_list()
                if response["ok"]:
                    found = False
                    for user in response["members"]:
                        user_real_name = user.get("real_name", "").lower()
                        user_display_name = user.get("profile", {}).get("display_name", "").lower()
                        search_name = user_identifier.lower()
                        
                        if search_name in user_real_name or search_name in user_display_name:
                            user_id = user["id"]
                            found = True
                            break
                    
                    if not found:
                        return f"Could not find a user matching '{user_identifier}'. Please try with a Slack user ID instead."
            else:
                return "Slack client not available for user lookup. Please use a Slack user ID instead."
        
        # Look for the activity file in the current directory
        activity_file = 'slack_user_activity.json'
        
        if not os.path.exists(activity_file):
            # If not found, try to generate it on the fly
            generate_user_activity_data()
            
            # Check if generation was successful
            if not os.path.exists(activity_file):
                return "Error: Could not find or generate user activity data."
        
        # Load the user activity data
        with open(activity_file, 'r', encoding='utf-8') as f:
            user_activity = json.load(f)
        
        # Check if the user exists in the activity data
        if user_id not in user_activity:
            return f"No activity data found for user {user_identifier} (ID: {user_id})."
        
        # Get the channels where the user is active
        user_channels = user_activity[user_id]
        
        # Sort channels by activity level (message count)
        sorted_channels = sorted(user_channels.items(), key=lambda x: x[1], reverse=True)
        
        # Format the response
        if not sorted_channels:
            return f"User {user_identifier} is not active in any channels."
        
        # Get channel names for the IDs
        channel_info = []
        for channel_id, count in sorted_channels:
            channel_name = get_channel_name(channel_id, opts)
            activity_level = "high" if count > 50 else "medium" if count > 10 else "low"
            channel_info.append(f"{channel_name} ({channel_id}): {activity_level} activity ({count} messages)")
        
        return f"User {user_identifier} is active in the following channels:\n" + "\n".join(channel_info)
    
    except Exception as e:
        logger.error(f"Error processing user activity: {str(e)}")
        return f"Error retrieving user activity: {str(e)}"

def generate_user_activity_data():
    """Generate the user activity data file by processing Slack data."""
    try:
        slack_dir = "../data/"  # Path to your Slack data directory
        
        # Dictionary to store user post counts per channel
        user_posts = defaultdict(lambda: defaultdict(int))
        
        # Walk through all files in the directory
        for root, dirs, files in os.walk(slack_dir):
            for file in files:
                if file.endswith('.json'):
                    channel_id = os.path.basename(root)
                    # Skip private channels and DMs
                    if channel_id.startswith('D') or channel_id.startswith('mpdm-') or not channel_id.replace('-', '').replace('_', '').isalnum():
                        continue
                    
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            messages = json.load(f)
                            # Count messages per user in this channel
                            for msg in messages:
                                if 'user' in msg and msg.get('subtype') not in ['message_deleted', 'message_changed']:
                                    user_posts[msg['user']][channel_id] += 1
                    except Exception as e:
                        logger.error(f"Error processing file {file}: {str(e)}")
        
        # Convert defaultdict to regular dict for JSON serialization
        output_data = {user_id: dict(channels) for user_id, channels in user_posts.items()}
        
        # Save to JSON file
        with open('slack_user_activity.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info("User activity data has been generated and saved to slack_user_activity.json")
        return True
    
    except Exception as e:
        logger.error(f"Error generating user activity data: {str(e)}")
        return False

def get_channel_name(channel_id, opts):
    """Get the channel name for a given channel ID."""
    # Try to get the channel name from the Slack API if available
    if opts and opts.get("slack_client"):
        try:
            response = opts["slack_client"].conversations_info(channel=channel_id)
            if response["ok"]:
                return response["channel"]["name"]
        except Exception:
            pass
    
    # Fallback to just returning the ID
    return channel_id

@enabled_tool
@tool
def manage_memory(content: str, key: str = None, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Store important information from the conversation in memory.
    
    Args:
        content: The information to store in memory
        key: Optional key to use for storing the memory (if not provided, a timestamp will be used)
    
    Returns:
        Confirmation message
    """
    memory_store = opts.get("store", None)
    if not memory_store:
        return "Error: Memory store not available"
        
    # Generate a key if not provided
    if not key:
        key = f"memory_{int(time.time())}"
        
    memory_store.store(key, content)
    return f"Memory stored successfully with key: {key}"

@enabled_tool
@tool
def search_memory(query: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Search for relevant information in memory.
    
    Args:
        query: The search query
    
    Returns:
        Relevant memories found
    """
    memory_store = opts.get("store", None)
    if not memory_store:
        return "Error: Memory store not available"
        
    results = memory_store.search(query)
    if not results:
        return "No relevant memories found"
        
    return "\n".join(results)

@enabled_tool
@tool
def store_procedure(name: str, steps: List[str], opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Store a step-by-step procedure for future reference.
    
    Args:
        name: The name of the procedure
        steps: A list of steps to follow in the procedure
    
    Returns:
        Confirmation message
    """
    # Get the memory store from the injected options
    memory_store = opts.get("store", None)
    if memory_store:
        memory_store.store(f"procedure:{name}", steps)
        return f"Procedure '{name}' stored successfully with {len(steps)} steps."
    return "Error: Memory store not available"

@enabled_tool
@tool
def recall_procedure(name: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Recall a previously stored procedure.
    
    Args:
        name: The name of the procedure to recall
    
    Returns:
        The steps of the procedure if found, otherwise an error message
    """
    # Get the memory store from the injected options
    memory_store = opts.get("store", None)
    if memory_store:
        result = memory_store.retrieve(f"procedure:{name}")
        if isinstance(result, list):
            return f"Procedure '{name}':\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(result)])
        return result
    return "Error: Memory store not available"

@enabled_tool
@tool
def execute_procedure(name: str, opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Execute a previously stored procedure step by step.
    
    Args:
        name: The name of the procedure to execute
    
    Returns:
        The result of executing the procedure
    """
    # Get the memory store from the injected options
    memory_store = opts.get("store", None)
    if memory_store:
        steps = memory_store.retrieve(f"procedure:{name}")
        if isinstance(steps, list):
            return f"Executing procedure '{name}':\n" + "\n".join([f"✓ {i+1}. {step}" for i, step in enumerate(steps)])
        return f"Cannot execute procedure: {steps}"
    return "Error: Memory store not available"

@enabled_tool
@tool
def transfer_to_channel_explorer(tool_input: str = "") -> str:
    """
    Transfer control to the channel explorer agent.
    
    Args:
        tool_input: Optional input (can be empty)
    
    Returns:
        Confirmation message
    """
    return "Successfully transferred to channel_explorer"

@enabled_tool
@tool
def transfer_back_to_supervisor(tool_input: str = "") -> str:
    """
    Transfer control back to the supervisor agent.
    
    Returns:
        Confirmation message
    """
    return "Successfully transferred back to supervisor"

def search_user_by_name(name: str, slack_client: Any) -> Optional[str]:
    """Search for a user by name and return their ID if found."""
    try:
        # Use the users.list API to get all users
        response = slack_client.users_list()
        if response["ok"]:
            users = response["members"]
            # Search for users whose name contains the search term (case insensitive)
            matching_users = []
            for user in users:
                # Check various name fields
                real_name = user.get("real_name", "").lower()
                display_name = user.get("profile", {}).get("display_name", "").lower()
                name_lower = name.lower()
                
                if name_lower in real_name or name_lower in display_name:
                    matching_users.append({
                        "id": user["id"],
                        "real_name": user.get("real_name", ""),
                        "display_name": user.get("profile", {}).get("display_name", "")
                    })
            
            return matching_users
        else:
            logger.error(f"Error searching for user: {response.get('error', 'Unknown error')}")
            return None
    except Exception as e:
        logger.error(f"Exception searching for user: {str(e)}")
        return None

def get_user_channels(user_id: str, slack_client: Any) -> List[Dict[str, Any]]:
    """Get all channels a user is a member of."""
    try:
        # Get all public channels
        channels_response = slack_client.conversations_list(types="public_channel")
        channels = []
        
        if channels_response["ok"]:
            for channel in channels_response["channels"]:
                # Check if user is a member of this channel
                try:
                    members_response = slack_client.conversations_members(channel=channel["id"])
                    if members_response["ok"] and user_id in members_response["members"]:
                        channels.append({
                            "id": channel["id"],
                            "name": channel["name"],
                            "is_member": True
                        })
                except Exception as e:
                    logger.error(f"Error checking channel membership: {str(e)}")
        
        return channels
    except Exception as e:
        logger.error(f"Exception getting user channels: {str(e)}")
        return []

def get_user_activity(user_id: str, slack_client: Any) -> Dict[str, Any]:
    """Get recent activity for a user across channels."""
    try:
        # Get channels the user is a member of
        channels = get_user_channels(user_id, slack_client)
        activity = []
        
        # For each channel, get recent messages from the user
        for channel in channels:
            try:
                # Get recent messages in the channel
                history_response = slack_client.conversations_history(channel=channel["id"], limit=100)
                if history_response["ok"]:
                    # Filter messages from the specified user
                    user_messages = [msg for msg in history_response["messages"] if msg.get("user") == user_id]
                    if user_messages:
                        activity.append({
                            "channel_id": channel["id"],
                            "channel_name": channel["name"],
                            "message_count": len(user_messages),
                            "recent_messages": user_messages[:5]  # Include up to 5 recent messages
                        })
            except Exception as e:
                logger.error(f"Error getting channel history: {str(e)}")
        
        return {
            "user_id": user_id,
            "channels": channels,
            "activity": activity
        }
    except Exception as e:
        logger.error(f"Exception getting user activity: {str(e)}")
        return {"error": str(e)}

def user_activity_tool(tool_input: str, slack_client: Any = None) -> str:
    """Tool to get user activity information."""
    try:
        # Parse the input to get user information
        input_data = json.loads(tool_input) if tool_input else {}
        user_id = input_data.get("user_id", "")
        user_name = input_data.get("user_name", "")
        
        if not user_id and user_name:
            # Search for user by name
            matching_users = search_user_by_name(user_name, slack_client)
            if matching_users and len(matching_users) > 0:
                # If we found exactly one user, use their ID
                if len(matching_users) == 1:
                    user_id = matching_users[0]["id"]
                else:
                    # If we found multiple users, return the list
                    return json.dumps({
                        "status": "multiple_matches",
                        "matching_users": matching_users
                    })
            else:
                return json.dumps({
                    "status": "user_not_found",
                    "message": f"Could not find user with name: {user_name}"
                })
        
        if user_id:
            # Get user activity
            activity_data = get_user_activity(user_id, slack_client)
            return json.dumps(activity_data)
        else:
            return json.dumps({
                "status": "error",
                "message": "No user ID or name provided"
            })
    except Exception as e:
        logger.error(f"Error in user_activity_tool: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

# Slack API tools
@tool
def list_channels() -> str:
    """List all channels in the Slack workspace."""
    slack_client = get_slack_client()
    if not slack_client:
        logger.error("Slack client not available for list_channels")
        return "Error: Slack client not available. Please check your configuration."
    
    try:
        logger.info("Calling Slack API to list channels")
        # Call Slack API to list channels
        result = slack_client.conversations_list(
            types="public_channel",
            limit=100
        )
        
        channels = result["channels"]
        channel_list = []
        
        for channel in channels:
            channel_name = channel["name"]
            channel_id = channel["id"]
            is_archived = channel.get("is_archived", False)
            
            if not is_archived:
                topic = channel.get("topic", {}).get("value", "No topic set")
                purpose = channel.get("purpose", {}).get("value", "No purpose set")
                
                channel_info = f"#{channel_name} (ID: {channel_id})"
                if topic:
                    channel_info += f"\n   Topic: {topic}"
                if purpose:
                    channel_info += f"\n   Purpose: {purpose}"
                
                channel_list.append(channel_info)
        
        if not channel_list:
            return "No channels found in this workspace."
        
        return "Channels in this workspace:\n\n" + "\n\n".join(channel_list)
    
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}")
        error_msg = str(e)
        
        # Check for missing permissions
        if "missing_scope" in error_msg:
            return "Error: The Slack bot doesn't have the necessary permissions to list channels. Please add the 'channels:read' scope to your Slack app."
        
        return f"Error listing channels: {error_msg}"

@tool
def get_channel_info(channel_id_or_name: str) -> str:
    """Get detailed information about a specific channel."""
    slack_client = get_slack_client()
    if not slack_client:
        logger.error("Slack client not available for get_channel_info")
        return "Error: Slack client not available. Please check your configuration."
    
    try:
        # Handle channel name (convert to ID)
        if channel_id_or_name.startswith('#'):
            channel_name = channel_id_or_name[1:]  # Remove the # prefix
            # Get channel ID from name
            result = slack_client.conversations_list(types="public_channel")
            for channel in result["channels"]:
                if channel["name"] == channel_name:
                    channel_id = channel["id"]
                    break
            else:
                return f"Channel {channel_id_or_name} not found."
        else:
            channel_id = channel_id_or_name
        
        # Get channel info
        result = slack_client.conversations_info(channel=channel_id)
        channel = result["channel"]
        
        # Extract channel details
        name = channel["name"]
        is_private = channel.get("is_private", False)
        is_archived = channel.get("is_archived", False)
        created = channel.get("created", 0)
        creator_id = channel.get("creator", "Unknown")
        topic = channel.get("topic", {}).get("value", "No topic set")
        purpose = channel.get("purpose", {}).get("value", "No purpose set")
        member_count = channel.get("num_members", 0)
        
        # Format created date
        from datetime import datetime
        created_date = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Get creator info if available
        creator_name = "Unknown"
        if creator_id != "Unknown":
            try:
                creator_info = slack_client.users_info(user=creator_id)
                creator = creator_info["user"]
                creator_name = creator.get("real_name") or creator.get("name") or "Unknown"
            except Exception:
                pass
        
        # Compile channel info
        info = [
            f"Channel: #{name} (ID: {channel_id})",
            f"Type: {'Private' if is_private else 'Public'}",
            f"Status: {'Archived' if is_archived else 'Active'}",
            f"Created: {created_date}",
            f"Created by: {creator_name}",
            f"Members: {member_count}",
            f"Topic: {topic}",
            f"Purpose: {purpose}"
        ]
        
        return "\n".join(info)
    
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}")
        return f"Error getting channel info: {str(e)}"

@tool
def list_channel_members(channel_id_or_name: str) -> str:
    """List members of a specific channel."""
    slack_client = get_slack_client()
    if not slack_client:
        logger.error("Slack client not available for list_channel_members")
        return "Error: Slack client not available. Please check your configuration."
    
    try:
        # Handle channel name (convert to ID)
        if channel_id_or_name.startswith('#'):
            channel_name = channel_id_or_name[1:]  # Remove the # prefix
            # Get channel ID from name
            result = slack_client.conversations_list(types="public_channel")
            for channel in result["channels"]:
                if channel["name"] == channel_name:
                    channel_id = channel["id"]
                    break
            else:
                return f"Channel {channel_id_or_name} not found."
        else:
            channel_id = channel_id_or_name
        
        # Get channel members
        result = slack_client.conversations_members(channel=channel_id)
        member_ids = result["members"]
        
        if not member_ids:
            return "No members found in this channel."
        
        # Get user info for each member
        members = []
        for member_id in member_ids:
            user_info = slack_client.users_info(user=member_id)
            user = user_info["user"]
            display_name = user.get("profile", {}).get("display_name") or user.get("real_name") or user.get("name")
            is_bot = user.get("is_bot", False)
            status_text = user.get("profile", {}).get("status_text", "")
            
            member_info = f"{display_name} (ID: {member_id})"
            if is_bot:
                member_info += " [BOT]"
            if status_text:
                member_info += f" - Status: {status_text}"
            
            members.append(member_info)
        
        # Get channel info for the header
        channel_info = slack_client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]
        
        return f"Members in #{channel_name} ({len(members)} total):\n\n" + "\n".join(members)
    
    except Exception as e:
        logger.error(f"Error listing channel members: {str(e)}")
        return f"Error listing channel members: {str(e)}"

# Available tools
TOOL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "list_channels": {
        "name": "list_channels",
        "description": "List all channels in the Slack workspace",
        "parameters": {}
    },
    "get_channel_info": {
        "name": "get_channel_info",
        "description": "Get detailed information about a specific channel",
        "parameters": {
            "channel_id_or_name": {
                "type": "string",
                "description": "ID or name of the channel (with # prefix)"
            }
        }
    },
    "list_channel_members": {
        "name": "list_channel_members",
        "description": "List members of a specific channel",
        "parameters": {
            "channel_id_or_name": {
                "type": "string",
                "description": "ID or name of the channel (with # prefix)"
            }
        }
    }
}

# Map of tool names to their implementations
TOOL_MAP: Dict[str, Any] = {
    "list_channels": list_channels,
    "get_channel_info": get_channel_info,
    "list_channel_members": list_channel_members,
}

# Make sure we're using gpt-4o here too
def get_llm():
    """Get the LLM model for tools."""
    api_base = os.getenv('API_BASE_URL', 'https://litellm.deriv.ai/v1')
    api_key = os.getenv('OPENAI_API_KEY', 'sk-cM-lFYMVyUyDPxcS-nquvQ')
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o')  # Use gpt-4o
    
    logger.info(f"Initializing tool LLM with base URL: {api_base} and model: {model_name}")
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base
    )

@enabled_tool
@tool
def reflect_and_improve(feedback: str = "", opts: Annotated[dict, InjectedToolArg] = None) -> str:
    """
    Reflect on recent interactions and update agent instructions to improve performance.
    
    Args:
        feedback: Optional explicit feedback from the user
    
    Returns:
        A summary of the improvements made
    """
    try:
        # Get the current agent name from the context
        agent_name = opts.get("agent_name", "unknown_agent")
        user_id = opts.get("user_id", "default_user")
        
        # Create namespace for storing agent instructions
        namespace = (f"user:{user_id}", "agent_instructions")
        
        # Get the store from opts
        store = opts.get("store")
        if not store:
            return "Error: Memory store not available for reflection"
        
        # Try to get current instructions
        try:
            current_instructions = store.get(namespace, key=agent_name)
            if current_instructions:
                current_instructions = current_instructions[0].value.get("instructions", "")
            else:
                # If no instructions exist yet, use default ones based on agent type
                if agent_name == "main_agent":
                    current_instructions = "You are the main supervisor agent that coordinates all interactions."
                elif agent_name == "channel_explorer":
                    current_instructions = "You are a specialized agent for exploring Slack channels."
                elif agent_name == "user_activity":
                    current_instructions = "You are a specialized agent for analyzing user activity in Slack."
                elif agent_name == "message_search":
                    current_instructions = "You are a specialized agent for searching and analyzing Slack messages."
                else:
                    current_instructions = "You are a helpful AI assistant for Slack."
        except Exception as e:
            logger.error(f"Error retrieving current instructions: {str(e)}")
            current_instructions = "No previous instructions found."
        
        # Get recent conversations from memory to analyze
        try:
            # Get recent conversations from the agent's namespace
            agent_namespace = (f"user:{user_id}", agent_name)
            conversations = store.list_keys(agent_namespace)
            
            # Filter for conversation entries
            conversation_keys = [k for k in conversations if k.startswith("conv_")]
            recent_conversations = []
            
            # Get the content of recent conversations (up to 5)
            for key in conversation_keys[-5:]:
                conv = store.get(agent_namespace, key)
                if conv and len(conv) > 0:
                    recent_conversations.append(conv[0].value.get("memory", ""))
            
            conversation_context = "\n\n".join(recent_conversations)
        except Exception as e:
            logger.error(f"Error retrieving conversations: {str(e)}")
            conversation_context = "No recent conversations found."
        
        # Use the LLM to generate improved instructions
        llm = get_llm()
        
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
        
        Return ONLY the new instructions without any explanation or additional text.
        """
        
        # Get the improved instructions
        response = llm.invoke(reflection_prompt)
        improved_instructions = response.content.strip()
        
        # Store the improved instructions
        store.put(namespace, key=agent_name, value={"instructions": improved_instructions})
        
        # Return a summary of the changes
        summary_prompt = f"""
        Summarize how the agent instructions have been improved:
        
        BEFORE:
        {current_instructions}
        
        AFTER:
        {improved_instructions}
        
        Provide a brief, bullet-point summary of the key improvements.
        """
        
        summary_response = llm.invoke(summary_prompt)
        return summary_response.content.strip()
        
    except Exception as e:
        logger.error(f"Error in reflect_and_improve: {str(e)}")
        return f"Error improving agent: {str(e)}"

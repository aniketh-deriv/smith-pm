import json
import os
from collections import defaultdict

slack_dir = "../data/"

# Dictionary to store user post counts per channel
user_posts = defaultdict(lambda: defaultdict(int))

# Walk through all files in the directory
for root, dirs, files in os.walk(slack_dir):
    for file in files:
        if file.endswith('.json'):
            channel_id = os.path.basename(root)
            # Skip private channels (starting with D) and multi-person DMs (starting with mpdm-)
            if channel_id.startswith('D') or channel_id.startswith('mpdm-') or not channel_id.replace('-', '').replace('_', '').isalnum():
                continue
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                try:
                    messages = json.load(f)
                    # Count messages per user in this channel
                    for msg in messages:
                        if 'user' in msg and msg.get('subtype') not in ['message_deleted', 'message_changed']:  # Only count direct messages, not system messages, deleted, or changed messages
                            user_posts[msg['user']][channel_id] += 1
                except json.JSONDecodeError:
                    print(f"Error reading {file}")
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")

# Convert defaultdict to regular dict for JSON serialization
output_data = {user_id: dict(channels) for user_id, channels in user_posts.items()}

# Save to JSON file
with open('slack_user_activity.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2)

print("User activity data has been saved to slack_user_activity.json")

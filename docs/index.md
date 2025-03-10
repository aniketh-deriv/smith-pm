# Agentic Office - Smith The PM Agent

Smith is an intelligent Project Management Assistant that integrates with Slack to help teams track and manage their projects more effectively. This AI-powered bot provides real-time project updates, status tracking, and team activity monitoring through natural language interactions.

## Overview

Smith serves as your virtual project manager, capable of:

- Monitoring multiple Slack channels simultaneously
- Providing concise project status updates
- Tracking team activities and progress
- Identifying blockers and potential risks
- Summarizing project-related discussions
- Responding to queries about project status and team activities

## Key Features

### 1. Natural Language Interaction
- Communicate with Smith using natural language in Slack
- Ask questions about project status, team activities, or specific tasks
- Get instant updates on ongoing projects

### 2. Smart Channel Management
- Automatically identifies relevant project channels
- Monitors public channels for project-related discussions
- Tracks conversations across multiple channels

### 3. Intelligent Reporting
- Provides concise, well-structured status reports
- Uses standardized status indicators (✅ On Track, ⚠️ At Risk, ❌ Blocked)
- Adapts report detail level based on the timeframe requested

### 4. Context-Aware Responses
- Understands project context from channel discussions
- Identifies and tracks team member contributions
- Maintains awareness of project timelines and deadlines

## Getting Started

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your environment variables:
```bash
SLACK_BOT_TOKEN=your-bot-token
SLACK_APP_TOKEN=your-app-token
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL_NAME=gpt-4o # or your preferred model
API_BASE_URL=your-api-base-url # if using a custom API endpoint
```

3. Run the Slack bot:
```bash
python slack.py
```

## Usage Examples

1. Get a quick project update:
```
@Smith what's the status of Project Alpha?
```

2. Check recent team activity:
```
@Smith show me the updates from the last 3 days
```

3. Monitor specific channels:
```
@Smith what's happening in the backend team?
```

4. Check a team member's activity:
```
@Smith what has @username been working on?
```

5. Get a project timeline:
```
@Smith when is the deadline for Project Beta?
```

Visit the other sections of this documentation to learn more about:
- [System Architecture](system.md)
- [Available Tools](tools.md)
- [Slack Integration](slack.md)
- [Manager Implementation](manager.md)

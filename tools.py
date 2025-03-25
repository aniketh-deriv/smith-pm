import re

def sanitize_message(message: str) -> str:
    """Redact potential PII from the message."""
    # Regex patterns for emails, SSNs, and other forms of PII
    message = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', message) # Example SSN pattern
    message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED EMAIL]', message) # Simple Email pattern
    return message

def process_response(agent_response: str) -> str:
    """ Process and sanitize the response before sending it back to the user."""
    sanitized_response = sanitize_message(agent_response)
    return sanitized_response

def handle_user_messages(message):
    # Process incoming message
    response = agent.generate_response(message)

    # Sanitize response to remove PII
    safe_response = process_response(response)
    
    # Return the safe response
    return safe_response

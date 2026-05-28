"""
System-Level Prompts
"""
from typing import Optional


def get_security_prompt() -> str:
    """Security-related system prompt"""
    return """Security Guidelines:
- Never expose sensitive credentials or API keys
- Sanitize user input before processing
- Validate file paths to prevent path traversal
- Use secure defaults for all operations
- Log security-relevant events"""


def get_privacy_prompt() -> str:
    """Privacy-related system prompt"""
    return """Privacy Guidelines:
- Do not store sensitive user data
- Handle personal information with care
- Anonymize logs and diagnostics
- Respect user privacy preferences"""


def get_reliability_prompt() -> str:
    """Reliability and error handling prompt"""
    return """Reliability Guidelines:
- Handle errors gracefully with informative messages
- Provide fallbacks when primary methods fail
- Log errors for debugging
- Never crash on invalid input"""


def get_system_prompt(
    include_security: bool = True,
    include_privacy: bool = True,
    include_reliability: bool = True
) -> str:
    """Get combined system prompt"""
    parts = []

    if include_security:
        parts.append(get_security_prompt())
    if include_privacy:
        parts.append(get_privacy_prompt())
    if include_reliability:
        parts.append(get_reliability_prompt())

    return "\n\n".join(parts)


def get_version_prompt() -> str:
    """Version and compatibility prompt"""
    return "WOLF 2.0 - Python Backend"
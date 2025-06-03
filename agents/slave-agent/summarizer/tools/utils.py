"""
Utility functions for text processing and sanitization
"""
import re
import logging

logger = logging.getLogger(__name__)


def sanitize_content(content: str) -> str:
    """
    Sanitize content to remove invalid control characters that can cause JSON serialization errors.
    
    Args:
        content: The text content to sanitize
        
    Returns:
        Sanitized content with invalid control characters removed
    """
    if not content:
        return ""
    
    # Remove invalid control characters but keep common ones like \n, \t, \r
    # This regex removes characters in ranges:
    # \x00-\x08: NULL, SOH, STX, ETX, EOT, ENQ, ACK, BEL, BS
    # \x0B: Vertical Tab (keep \n=\x0A and \t=\x09, \r=\x0D)
    # \x0C: Form Feed
    # \x0E-\x1F: SO, SI, DLE, DC1-4, NAK, SYN, ETB, CAN, EM, SUB, ESC, FS, GS, RS, US
    # \x7F-\x9F: DEL and C1 control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
    
    # Also remove any remaining null bytes or other problematic characters
    sanitized = sanitized.replace('\x00', '')
    
    return sanitized.strip()


def validate_json_serializable(text: str) -> bool:
    """
    Check if a string can be safely serialized to JSON.
    
    Args:
        text: The text to validate
        
    Returns:
        True if the text is JSON serializable, False otherwise
    """
    import json
    try:
        json.dumps(text)
        return True
    except (TypeError, ValueError) as e:
        logger.warning(f"Text is not JSON serializable: {e}")
        return False

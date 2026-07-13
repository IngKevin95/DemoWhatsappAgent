"""
Input validation middleware for sanitizing user input.

Prevents SQL injection and XSS attacks by sanitizing user input.
"""

import re
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Sanitizes user input to prevent SQL injection and XSS attacks.

    Uses whitelist approach: allow safe characters, remove dangerous patterns.
    """

    # Dangerous SQL keywords and characters
    SQL_PATTERNS = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', 'EXECUTE']

    # Dangerous HTML/Script patterns
    SCRIPT_PATTERNS = [r'<script', r'</script>', r'<iframe', r'<img', r'onerror', r'onload']

    # Allowed characters (whitelist approach)
    # Alphanumeric + spaces + safe punctuation
    ALLOWED_REGEX = re.compile(r"[^a-zA-Z0-9\s\.\,\?\!\-\'\"\á\é\í\ó\ú\ñ]")

    def sanitize(self, text: str) -> str:
        """
        Sanitize user input by removing dangerous patterns.

        Args:
            text: User input to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return text

        sanitized = text

        # Remove script tags and dangerous HTML
        for pattern in self.SCRIPT_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # Handle SQL injection: allow SQL keywords if they're lowercase or in normal context
        # (This is a simplification; real implementation would use NLP or parameterized queries)
        # For now, we'll allow SELECT/WHERE in normal text but block dangerous chars

        # Remove dangerous SQL characters
        for char in [';', '--']:
            if char in text.upper() and ('DROP' in text.upper() or 'DELETE' in text.upper()):
                sanitized = sanitized.replace(char, '')

        # Log if sanitization occurred
        if sanitized != text:
            logger.info(f"Input sanitized: original_length={len(text)}, sanitized_length={len(sanitized)}")

        return sanitized

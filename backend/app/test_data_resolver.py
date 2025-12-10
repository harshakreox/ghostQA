"""
Test Data Resolver
Intelligently resolves test data from multiple sources based on context.

Priority:
1. Explicit values in steps (e.g., "john@test.com")
2. Project credentials (configured in project setup)
3. Auto-generated values (if enabled)

The resolver is smart enough to detect when a value needs resolution
based on natural language patterns in Gherkin steps.
"""

import re
from typing import Optional, Dict, Any, Tuple
from test_data_generator import TestDataGenerator, get_generator


class TestDataResolver:
    """
    Resolves test data intelligently from multiple sources.
    Designed to work with natural language Gherkin steps.
    """

    # Patterns that indicate a value should be resolved dynamically
    # These are natural language patterns that users might write
    # Using .+ instead of \w+ to match multi-word field types like "first name"
    DYNAMIC_VALUE_PATTERNS = [
        # "my username", "my password", "my email", "my first name"
        r'^my\s+(.+)$',
        # "a valid email", "a valid password", "a valid first name"
        r'^(?:a\s+)?valid\s+(.+)$',
        # "the username", "the password", "the first name"
        r'^the\s+(.+)$',
        # "any email", "any username"
        r'^any\s+(.+)$',
        # "test email", "test password", "test user"
        r'^test\s+(.+)$',
        # "new email", "new password" (for registration)
        r'^(?:a\s+)?new\s+(.+)$',
        # "random email", "random username"
        r'^(?:a\s+)?random\s+(.+)$',
        # "generated email", "auto-generated password"
        r'^(?:auto[- ]?)?generated\s+(.+)$',
        # "sample data", "dummy data"
        r'^(?:sample|dummy)\s+(.+)$',
        # Single words that are field type indicators
        r'^(username|password|email|phone|address|name)$',
    ]

    # Map of field types to project credential fields
    CREDENTIAL_FIELD_MAP = {
        'username': 'test_username',
        'user': 'test_username',
        'login': 'test_username',
        'user_name': 'test_username',
        'email': 'test_email',
        'e-mail': 'test_email',
        'mail': 'test_email',
        'password': 'test_password',
        'passwd': 'test_password',
        'pwd': 'test_password',
        'admin_username': 'test_admin_username',
        'admin_password': 'test_admin_password',
        'admin': 'test_admin_username',
    }

    # Field types that typically need unique values
    UNIQUE_FIELD_TYPES = {'email', 'username', 'phone'}

    def __init__(self, project_credentials: Optional[Dict[str, Any]] = None,
                 auto_generate_enabled: bool = True):
        """
        Initialize the resolver.

        Args:
            project_credentials: Dict with test_username, test_password, etc.
            auto_generate_enabled: Whether to fall back to auto-generation
        """
        self.project_credentials = project_credentials or {}
        self.auto_generate_enabled = auto_generate_enabled
        self.generator = get_generator()
        self._resolved_cache: Dict[str, str] = {}  # Cache for session consistency

    def resolve_value(self, value: str, field_name: str) -> Tuple[str, str]:
        """
        Resolve the actual value to use for a field.

        Args:
            value: The value from the Gherkin step
            field_name: The name of the field being filled

        Returns:
            Tuple of (resolved_value, source) where source is one of:
            - "explicit": Value was used as-is
            - "project": Value came from project credentials
            - "generated": Value was auto-generated
        """
        # Normalize inputs
        value_lower = value.lower().strip()
        field_lower = field_name.lower().strip()

        # Step 1: Check if value is explicit (not a dynamic pattern)
        if not self._is_dynamic_value(value_lower):
            return value, "explicit"

        # Step 2: Try to get from project credentials
        cred_value = self._get_from_credentials(field_lower, value_lower)
        if cred_value:
            return cred_value, "project"

        # Step 3: Auto-generate if enabled
        if self.auto_generate_enabled:
            generated = self._generate_value(field_lower)
            return generated, "generated"

        # Step 4: No value available
        raise ValueError(
            f"Cannot resolve value for field '{field_name}'. "
            f"No project credentials found and auto-generation is disabled. "
            f"Please either:\n"
            f"  1. Provide an explicit value in the step\n"
            f"  2. Configure credentials in Project Setup\n"
            f"  3. Enable auto test data generation"
        )

    def _is_dynamic_value(self, value: str) -> bool:
        """Check if the value indicates dynamic resolution is needed."""
        # Empty or whitespace-only
        if not value or not value.strip():
            return True

        # Check against dynamic patterns
        for pattern in self.DYNAMIC_VALUE_PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                return True

        return False

    def _get_from_credentials(self, field_name: str, value_hint: str) -> Optional[str]:
        """Try to get value from project credentials."""
        if not self.project_credentials:
            return None

        # Direct field name match
        field_normalized = field_name.replace(' ', '_').replace('-', '_')

        # Check credential map
        cred_key = self.CREDENTIAL_FIELD_MAP.get(field_normalized)
        if cred_key and cred_key in self.project_credentials:
            cred_value = self.project_credentials.get(cred_key)
            if cred_value:
                return cred_value

        # Check if field name directly matches a credential key
        for key in ['test_username', 'test_password', 'test_admin_username', 'test_admin_password']:
            if field_normalized in key or key.replace('test_', '') == field_normalized:
                cred_value = self.project_credentials.get(key)
                if cred_value:
                    return cred_value

        # Extract field type from value hint (e.g., "my username" -> "username")
        for pattern in self.DYNAMIC_VALUE_PATTERNS:
            match = re.match(pattern, value_hint, re.IGNORECASE)
            if match and match.groups():
                extracted_type = match.group(1).lower()
                cred_key = self.CREDENTIAL_FIELD_MAP.get(extracted_type)
                if cred_key:
                    cred_value = self.project_credentials.get(cred_key)
                    if cred_value:
                        return cred_value

        return None

    def _generate_value(self, field_name: str) -> str:
        """Generate a value using the test data generator."""
        # Check cache first for session consistency
        cache_key = field_name.lower().replace(' ', '_')
        if cache_key in self._resolved_cache:
            return self._resolved_cache[cache_key]

        # Generate new value
        make_unique = any(ut in field_name.lower() for ut in self.UNIQUE_FIELD_TYPES)
        generated = self.generator.generate_for_field(field_name, make_unique)

        # Cache it
        self._resolved_cache[cache_key] = generated
        return generated

    def reset_session(self):
        """Reset caches for a new test session."""
        self._resolved_cache.clear()
        self.generator.reset_session()

    def set_credentials(self, credentials: Dict[str, Any]):
        """Update project credentials."""
        self.project_credentials = credentials or {}


# Convenience function for step definitions
_resolver: Optional[TestDataResolver] = None

def get_resolver() -> TestDataResolver:
    """Get or create the global resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = TestDataResolver()
    return _resolver

def configure_resolver(project_credentials: Dict[str, Any] = None,
                       auto_generate_enabled: bool = True):
    """Configure the global resolver with project settings."""
    global _resolver
    _resolver = TestDataResolver(project_credentials, auto_generate_enabled)
    return _resolver

def resolve_test_value(value: str, field_name: str) -> Tuple[str, str]:
    """
    Convenience function to resolve a test value.

    Returns:
        Tuple of (resolved_value, source)
    """
    return get_resolver().resolve_value(value, field_name)


if __name__ == "__main__":
    # Demo
    print("=== Test Data Resolver Demo ===\n")

    # Scenario 1: With project credentials
    print("--- Scenario 1: With Project Credentials ---")
    resolver = TestDataResolver(
        project_credentials={
            'test_username': 'project_user',
            'test_password': 'project_pass123',
        },
        auto_generate_enabled=True
    )

    test_cases = [
        ("john@example.com", "Email"),      # Explicit
        ("my username", "Username"),         # From project creds
        ("my password", "Password"),         # From project creds
        ("a valid email", "Email"),          # Auto-generated (no email in creds)
        ("new password", "Confirm Password"), # Auto-generated
    ]

    for value, field in test_cases:
        resolved, source = resolver.resolve_value(value, field)
        print(f'  "{value}" in "{field}" -> "{resolved}" (from {source})')

    # Scenario 2: Without project credentials
    print("\n--- Scenario 2: Without Project Credentials ---")
    resolver2 = TestDataResolver(auto_generate_enabled=True)
    resolver2.reset_session()

    for value, field in test_cases:
        resolved, source = resolver2.resolve_value(value, field)
        print(f'  "{value}" in "{field}" -> "{resolved}" (from {source})')

    # Scenario 3: Auto-generation disabled, no creds
    print("\n--- Scenario 3: Auto Disabled, No Creds ---")
    resolver3 = TestDataResolver(auto_generate_enabled=False)

    try:
        resolver3.resolve_value("my username", "Username")
    except ValueError as e:
        print(f"  Error (expected): {e}")

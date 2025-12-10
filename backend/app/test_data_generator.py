"""
Smart Test Data Generator
Generates contextually appropriate test data based on field names/types
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import re

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None

# Import learner for adaptive field classification
try:
    from test_data_learner import get_learner, classify_field as learner_classify
    LEARNER_AVAILABLE = True
except ImportError:
    LEARNER_AVAILABLE = False


class TestDataGenerator:
    """
    Generates realistic test data based on field context.
    Uses field name patterns to determine appropriate data type.
    """

    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.faker = Faker(locale) if fake else None
        self.generated_data: Dict[str, Any] = {}  # Cache for consistent data within a session
        self.unique_suffix = self._generate_unique_suffix()

        # Field patterns mapped to generator functions
        # Order matters\! More specific patterns should come first
        self.field_patterns = {
            # Username MUST be before name patterns to avoid matching 'name' in 'username'
            r'(user[_\s]?name|username|login|user[_\s]?id)': self.generate_username,
            
            # Identity fields
            r'(first[_\s]?name|fname|given[_\s]?name)': self.generate_first_name,
            r'(last[_\s]?name|lname|surname|family[_\s]?name)': self.generate_last_name,
            r'(full[_\s]?name|name)': self.generate_full_name,

            # Contact fields
            r'(email|e-mail|mail)': self.generate_email,
            r'(phone|telephone|mobile|cell)': self.generate_phone,

            # Authentication fields - confirm password uses cached password value
            r'(confirm[_\s]?password|password[_\s]?confirm|re-?type[_\s]?password|repeat[_\s]?password)': self.generate_confirm_password,
            r'(password|passwd|pwd|secret)': self.generate_password,

            # Address fields
            r'(street|address[_\s]?line|address1)': self.generate_street_address,
            r'(city|town)': self.generate_city,
            r'(state|province|region)': self.generate_state,
            r'(zip|postal|postcode)': self.generate_zip_code,
            r'(country)': self.generate_country,

            # Business fields
            r'(company|organization|org|business)': self.generate_company,
            r'(job[_\s]?title|title|position|role)': self.generate_job_title,

            # Financial fields
            r'(card[_\s]?number|credit[_\s]?card|cc[_\s]?number)': self.generate_credit_card,
            r'(cvv|cvc|security[_\s]?code)': self.generate_cvv,
            r'(exp|expir)': self.generate_expiry_date,

            # Date/Time fields
            r'(date[_\s]?of[_\s]?birth|dob|birth[_\s]?date|birthday)': self.generate_date_of_birth,
            r'(date|day)': self.generate_date,
            r'(time)': self.generate_time,

            # Numeric fields
            r'(age)': self.generate_age,
            r'(amount|price|cost|total)': self.generate_amount,
            r'(quantity|qty|count|number)': self.generate_quantity,

            # Text fields
            r'(description|desc|about|bio|summary)': self.generate_description,
            r'(comment|note|message|feedback)': self.generate_comment,
            r'(url|website|link|homepage)': self.generate_url,
        }

    def _generate_unique_suffix(self) -> str:
        """Generate a unique suffix for this test session"""
        timestamp = datetime.now().strftime("%H%M%S")
        random_chars = ''.join(random.choices(string.ascii_lowercase, k=4))
        return f"{timestamp}{random_chars}"

    def generate_for_field(self, field_name: str, make_unique: bool = True) -> str:
        """
        Generate appropriate test data based on field name.

        Args:
            field_name: The name/label of the field
            make_unique: If True, appends unique suffix to avoid duplicates

        Returns:
            Generated test data as string
        """
        field_lower = field_name.lower().strip()

        # Check if we already generated data for this field in this session
        cache_key = f"{field_lower}_{make_unique}"
        if cache_key in self.generated_data:
            return self.generated_data[cache_key]

        # Find matching pattern
        for pattern, generator in self.field_patterns.items():
            if re.search(pattern, field_lower, re.IGNORECASE):
                value = generator(make_unique)
                self.generated_data[cache_key] = value
                return value

        # Pattern not found - try the learner for adaptive classification
        if LEARNER_AVAILABLE:
            data_type, generator_name, confidence = learner_classify(field_name)
            if confidence > 0 and hasattr(self, generator_name):
                generator_func = getattr(self, generator_name)
                value = generator_func(make_unique)
                self.generated_data[cache_key] = value
                return value

        # Default: generate generic text
        value = self.generate_generic_text(field_name)
        self.generated_data[cache_key] = value
        return value

    # ==================== Generator Methods ====================

    def generate_first_name(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.first_name()
        names = ["John", "Jane", "Alex", "Sam", "Chris", "Taylor", "Jordan", "Casey"]
        return random.choice(names)

    def generate_last_name(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.last_name()
        names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller"]
        return random.choice(names)

    def generate_full_name(self, unique: bool = False) -> str:
        return f"{self.generate_first_name()} {self.generate_last_name()}"

    def generate_username(self, unique: bool = True) -> str:
        if self.faker:
            base = self.faker.user_name()
        else:
            base = f"user{random.randint(100, 999)}"

        if unique:
            return f"{base}_{self.unique_suffix}"
        return base

    def generate_email(self, unique: bool = True) -> str:
        if unique:
            # Always generate unique email to avoid "already registered" errors
            random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            return f"test_{random_part}_{self.unique_suffix}@ghostqa-test.com"

        if self.faker:
            return self.faker.email()
        return f"test_{random.randint(1000, 9999)}@test.com"

    def generate_phone(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.phone_number()
        return f"+1{random.randint(200, 999)}{random.randint(100, 999)}{random.randint(1000, 9999)}"

    def generate_password(self, unique: bool = False) -> str:
        """Generate a password that meets most requirements"""
        # Check if we already generated a password in this session
        if 'password' in self.generated_data:
            return self.generated_data['password']

        # Ensure: uppercase, lowercase, digit, special char, min 8 chars
        password = f"Test{random.randint(100, 999)}!Pwd"
        self.generated_data['password'] = password
        return password

    def generate_confirm_password(self, unique: bool = False) -> str:
        """Return the same password as the primary password field"""
        return self.generate_password(unique)

    def generate_street_address(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.street_address()
        return f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Park'])} Street"

    def generate_city(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.city()
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle"]
        return random.choice(cities)

    def generate_state(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.state_abbr()
        states = ["CA", "NY", "TX", "FL", "WA", "IL", "PA"]
        return random.choice(states)

    def generate_zip_code(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.zipcode()
        return str(random.randint(10000, 99999))

    def generate_country(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.country()
        return "United States"

    def generate_company(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.company()
        prefixes = ["Tech", "Global", "Digital", "Smart", "Pro"]
        suffixes = ["Solutions", "Systems", "Corp", "Inc", "Labs"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    def generate_job_title(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.job()
        titles = ["Software Engineer", "Product Manager", "Data Analyst", "Designer", "QA Engineer"]
        return random.choice(titles)

    def generate_credit_card(self, unique: bool = False) -> str:
        # Generate test credit card number (Stripe test format)
        return "4242424242424242"

    def generate_cvv(self, unique: bool = False) -> str:
        return str(random.randint(100, 999))

    def generate_expiry_date(self, unique: bool = False) -> str:
        # Future expiry date
        future = datetime.now() + timedelta(days=365 * 2)
        return future.strftime("%m/%y")

    def generate_date_of_birth(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.date_of_birth(minimum_age=18, maximum_age=65).strftime("%Y-%m-%d")
        # Generate adult birth date
        year = random.randint(1960, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"

    def generate_date(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.date_this_year().strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")

    def generate_time(self, unique: bool = False) -> str:
        hour = random.randint(9, 17)
        minute = random.choice([0, 15, 30, 45])
        return f"{hour:02d}:{minute:02d}"

    def generate_age(self, unique: bool = False) -> str:
        return str(random.randint(18, 65))

    def generate_amount(self, unique: bool = False) -> str:
        return f"{random.randint(10, 1000)}.{random.randint(0, 99):02d}"

    def generate_quantity(self, unique: bool = False) -> str:
        return str(random.randint(1, 10))

    def generate_description(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.paragraph(nb_sentences=2)
        return "This is a test description generated by GhostQA automated testing."

    def generate_comment(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.sentence()
        return "Test comment from automated testing."

    def generate_url(self, unique: bool = False) -> str:
        if self.faker:
            return self.faker.url()
        return "https://example.com"

    def generate_generic_text(self, field_name: str) -> str:
        """Generate generic text based on field name"""
        return f"Test {field_name.title()}"

    # ==================== Utility Methods ====================

    def reset_session(self):
        """Reset generated data cache and create new unique suffix"""
        self.generated_data.clear()
        self.unique_suffix = self._generate_unique_suffix()

    def get_generated_data(self) -> Dict[str, Any]:
        """Return all generated data for this session"""
        return self.generated_data.copy()


# Global instance for convenience
_generator = None

def get_generator() -> TestDataGenerator:
    """Get or create the global test data generator"""
    global _generator
    if _generator is None:
        _generator = TestDataGenerator()
    return _generator

def generate_test_data(field_name: str, unique: bool = True) -> str:
    """Convenience function to generate test data for a field"""
    return get_generator().generate_for_field(field_name, unique)


# ==================== Gherkin Data Placeholder Support ====================

# Placeholder pattern: {{field_type}} or {{auto}}
PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')

def resolve_placeholders(text: str) -> str:
    """
    Replace placeholders in text with generated test data.

    Examples:
        "{{email}}" -> "test_abc123@ghostqa-test.com"
        "{{first_name}}" -> "John"
        "{{auto}}" -> generates based on context
    """
    def replace_match(match):
        placeholder = match.group(1).lower()
        if placeholder == 'auto':
            return generate_test_data('generic')
        return generate_test_data(placeholder)

    return PLACEHOLDER_PATTERN.sub(replace_match, text)


if __name__ == "__main__":
    # Demo
    generator = TestDataGenerator()

    print("=== Test Data Generator Demo ===\n")

    fields = [
        "First name", "Last name", "Username", "Email",
        "Password", "Confirm password", "Phone",
        "Street Address", "City", "State", "Zip Code",
        "Date of Birth", "Company", "Job Title"
    ]

    for field in fields:
        value = generator.generate_for_field(field)
        print(f"{field:20} -> {value}")

    print("\n=== Placeholder Resolution ===\n")

    templates = [
        'I enter "{{email}}" in the Email field',
        'I enter "{{first_name}}" in the First Name field',
        'I enter "{{password}}" in the Password field',
    ]

    for template in templates:
        resolved = resolve_placeholders(template)
        print(f"Original: {template}")
        print(f"Resolved: {resolved}\n")

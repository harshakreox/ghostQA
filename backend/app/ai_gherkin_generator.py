"""
AI Test Case Generator - Gherkin/BDD Version
Generates test cases in Gherkin format (Given-When-Then)
"""

# Load environment variables first
from dotenv import load_dotenv
import pathlib
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from pydantic import BaseModel
from typing import List, Optional
from models_gherkin import (
    GherkinFeature, GherkinScenario, GherkinStep, StepKeyword,
    TraditionalTestCase, TraditionalTestSuite, TestCredential
)
from models import UIFrameworkConfig
from framework_library import build_framework_context
from data_dictionary_parser import DataDictionary, FieldDefinition, parse_data_dictionary_raw
from gherkin_parser import GherkinParser
import os
import json
import requests
from datetime import datetime


class GenerateGherkinRequest(BaseModel):
    """Request to generate Gherkin test cases from BRD"""
    brd_content: str
    project_id: Optional[str] = None
    project_context: Optional[str] = None
    base_url: Optional[str] = None


class GenerateGherkinResponse(BaseModel):
    """Response containing generated Gherkin feature"""
    feature: GherkinFeature
    brd_summary: str
    suggestions: List[str] = []


class AIGherkinGenerator:
    """Universal AI Generator for BDD/Gherkin Test Cases"""
    
    def __init__(self):
        """Auto-detect and configure LLM connection"""
        self.api_url = None
        self.model = None
        self.api_type = None
        self.api_key = None
        
        self._detect_llm()
    
    def _detect_llm(self):
        """Auto-detect which LLM service to use"""
        
        # Option 1: Custom LLM_API_URL
        if os.getenv("LLM_API_URL"):
            self.api_url = os.getenv("LLM_API_URL")
            self.model = os.getenv("LLM_MODEL", "local-model")
            self.api_type = os.getenv("LLM_API_TYPE", "openai")
            self.api_key = os.getenv("LLM_API_KEY")
            print(f"[OK] Using custom LLM: {self.api_url}")
            return
        
        # Option 2: Check for Ollama
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.api_url = "http://localhost:11434/api/generate"
                self.api_type = "ollama"
                
                models_data = response.json().get('models', [])
                available_models = [m['name'] for m in models_data]
                
                preferred_model = os.getenv("OLLAMA_MODEL")
                
                if preferred_model:
                    matching = [m for m in available_models if preferred_model in m]
                    if matching:
                        self.model = matching[0]
                    else:
                        self.model = available_models[0] if available_models else "llama3.1"
                else:
                    self.model = available_models[0] if available_models else "llama3.1"
                
                print(f"[OK] Using Ollama: {self.model}")
                return
        except:
            pass
        
        # Option 3: Check for Anthropic API key
        if os.getenv("ANTHROPIC_API_KEY"):
            self.api_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-sonnet-4-20250514"
            self.api_type = "anthropic"
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            print("[OK] Using Anthropic Claude")
            return
        
        raise ValueError("No AI service configured!")
    
    def generate_gherkin(
        self,
        brd_content: str,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        end_to_end: bool = False,
        ui_config: Optional[UIFrameworkConfig] = None,
        credentials: Optional[List[TestCredential]] = None
    ) -> GenerateGherkinResponse:
        """Generate Gherkin test scenarios from BRD"""

        print(f" Generating Gherkin test scenarios with {self.api_type}...")
        print(f"   Mode: {'End-to-End (15-25 scenarios)' if end_to_end else 'Focused (10-15 scenarios)'}")
        if ui_config and ui_config.frameworks:
            print(f"   Frameworks: {', '.join(ui_config.frameworks)}")
        if credentials:
            print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        # Choose prompt based on mode
        if end_to_end:
            prompt = self._build_e2e_prompt(brd_content, project_context, base_url, ui_config, credentials)
        else:
            prompt = self._build_focused_prompt(brd_content, project_context, base_url, ui_config, credentials)

        ai_response = self._call_llm(prompt)

        # Parse the Gherkin feature
        feature = self._parse_gherkin_response(ai_response)
        brd_summary = self._extract_summary(ai_response)
        suggestions = self._extract_suggestions(ai_response)

        print(f"    Generated {len(feature.scenarios)} scenarios")

        return GenerateGherkinResponse(
            feature=feature,
            brd_summary=brd_summary,
            suggestions=suggestions if isinstance(suggestions, list) else []
        )

    def generate_traditional(
        self,
        brd_content: str,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        end_to_end: bool = False,
        ui_config: Optional[UIFrameworkConfig] = None,
        credentials: Optional[List[TestCredential]] = None
    ) -> dict:
        """Generate Traditional table format test cases from BRD"""

        print(f" Generating Traditional test cases with {self.api_type}...")
        print(f"   Mode: {'End-to-End (comprehensive)' if end_to_end else 'Focused (10-15 test cases)'}")
        if ui_config and ui_config.frameworks:
            print(f"   Frameworks: {', '.join(ui_config.frameworks)}")
        if credentials:
            print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        prompt = self._build_traditional_prompt(brd_content, project_context, base_url, end_to_end, ui_config, credentials)
        ai_response = self._call_llm(prompt)

        # Parse the traditional test cases
        test_suite = self._parse_traditional_response(ai_response)
        brd_summary = self._extract_summary(ai_response)
        suggestions = self._extract_suggestions(ai_response)

        print(f"    Generated {len(test_suite.test_cases)} traditional test cases")

        return {
            "test_suite": test_suite,
            "brd_summary": brd_summary,
            "suggestions": suggestions if isinstance(suggestions, list) else []
        }

    # Token limits for different models (input context limits)
    MODEL_TOKEN_LIMITS = {
        "ollama": 8000,      # Conservative for local models
        "openai": 12000,     # Leave room for response
        "anthropic": 150000  # Claude has large context
    }

    # Recommended batch sizes (rows per batch) - smaller batches = more complete scenarios per batch
    BATCH_SIZE_ROWS = 15  # Process 15 rows at a time (expecting 30-60 scenarios per batch)

    def generate_from_data_dictionary(
        self,
        data_dictionary: DataDictionary,
        form_name: Optional[str] = None,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        output_format: str = "gherkin"  # "gherkin" or "traditional"
    ) -> dict:
        """Generate validation test scenarios from data dictionary with automatic batching"""

        total_rows = len(data_dictionary.raw_rows) if data_dictionary.raw_rows else len(data_dictionary.fields)
        estimated_tokens = data_dictionary.estimate_tokens()
        token_limit = self.MODEL_TOKEN_LIMITS.get(self.api_type, 8000)

        print(f" Generating validation scenarios from data dictionary with {self.api_type}...")
        print(f"   Total entries: {total_rows}")
        print(f"   Estimated tokens: ~{estimated_tokens:,}")
        print(f"   Model token limit: ~{token_limit:,}")
        print(f"   Output Format: {output_format}")

        # Check if we need batching:
        # 1. Input tokens exceed limit, OR
        # 2. Too many rows (output will be huge) - max 15 rows per batch to avoid truncation
        prompt_overhead = 2000
        input_exceeds_limit = (estimated_tokens + prompt_overhead) > token_limit
        too_many_rows = total_rows > self.BATCH_SIZE_ROWS  # More than 15 rows = batch

        needs_batching = input_exceeds_limit or too_many_rows

        if needs_batching and data_dictionary.raw_rows:
            if too_many_rows and not input_exceeds_limit:
                print(f"   [BATCH MODE] {total_rows} rows would generate huge output, processing in batches of {self.BATCH_SIZE_ROWS}...")
            else:
                print(f"   [BATCH MODE] Data exceeds token limit, processing in batches...")
            return self._generate_batched(data_dictionary, form_name, project_context, base_url, output_format)
        else:
            # Single request - data fits within limits
            return self._generate_single(data_dictionary, form_name, project_context, base_url, output_format)

    def _generate_single(
        self,
        data_dictionary: DataDictionary,
        form_name: Optional[str] = None,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        output_format: str = "gherkin"
    ) -> dict:
        """Generate scenarios in a single request (data fits within token limits)"""

        total_fields = len(data_dictionary.raw_rows) if data_dictionary.raw_rows else len(data_dictionary.fields)
        expected_min_scenarios = total_fields * 2  # At least 2 scenarios per field

        prompt = self._build_data_dictionary_prompt(data_dictionary, form_name, project_context, base_url, output_format)
        ai_response = self._call_llm(prompt)

        warnings = []

        if output_format == "traditional":
            test_suite = self._parse_traditional_response(ai_response)
            summary = self._extract_summary(ai_response)
            suggestions = self._extract_suggestions(ai_response)

            actual_count = len(test_suite.test_cases)
            print(f"    Generated {actual_count} validation test cases (expected ~{expected_min_scenarios}+)")

            # Check if we got fewer scenarios than expected
            if actual_count < expected_min_scenarios:
                warning_msg = f"Generated {actual_count} test cases for {total_fields} fields. Expected ~{expected_min_scenarios}+. Some validations may be missing."
                warnings.append(warning_msg)
                print(f"    [WARNING] {warning_msg}")

            return {
                "test_suite": test_suite,
                "summary": summary,
                "suggestions": suggestions if isinstance(suggestions, list) else [],
                "warnings": warnings,
                "field_count": total_fields,
                "scenario_count": actual_count
            }
        else:
            feature = self._parse_gherkin_response(ai_response)
            summary = self._extract_summary(ai_response)
            suggestions = self._extract_suggestions(ai_response)

            actual_count = len(feature.scenarios)
            print(f"    Generated {actual_count} validation scenarios (expected ~{expected_min_scenarios}+)")

            # Check if we got fewer scenarios than expected
            if actual_count < expected_min_scenarios:
                warning_msg = f"Generated {actual_count} scenarios for {total_fields} fields. Expected ~{expected_min_scenarios}+. Some validations may be missing."
                warnings.append(warning_msg)
                print(f"    [WARNING] {warning_msg}")

            return {
                "feature": feature,
                "summary": summary,
                "suggestions": suggestions if isinstance(suggestions, list) else [],
                "warnings": warnings,
                "field_count": total_fields,
                "scenario_count": actual_count
            }

    def _generate_batched(
        self,
        data_dictionary: DataDictionary,
        form_name: Optional[str] = None,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        output_format: str = "gherkin"
    ) -> dict:
        """Generate scenarios in batches for large data dictionaries"""

        total_rows = len(data_dictionary.raw_rows)
        batch_size = self.BATCH_SIZE_ROWS
        num_batches = (total_rows + batch_size - 1) // batch_size
        expected_min_scenarios = total_rows * 2  # At least 2 scenarios per field

        print(f"   Processing {num_batches} batches of ~{batch_size} entries each...")

        all_scenarios = []
        all_test_cases = []
        all_suggestions = set()
        combined_summary = []
        warnings = []

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            batch_data = data_dictionary.get_batch(start_idx, batch_size)
            batch_rows = len(batch_data.raw_rows)
            batch_expected = batch_rows * 2

            print(f"   Batch {batch_num + 1}/{num_batches}: rows {start_idx + 1}-{start_idx + batch_rows} (expecting ~{batch_expected}+ scenarios)")

            prompt = self._build_data_dictionary_prompt(batch_data, form_name, project_context, base_url, output_format)
            ai_response = self._call_llm(prompt)

            if output_format == "traditional":
                test_suite = self._parse_traditional_response(ai_response)
                batch_count = len(test_suite.test_cases)
                all_test_cases.extend(test_suite.test_cases)
                print(f"      -> Got {batch_count} test cases")
                summary = self._extract_summary(ai_response)
                if summary:
                    combined_summary.append(summary)
            else:
                feature = self._parse_gherkin_response(ai_response)
                batch_count = len(feature.scenarios)
                all_scenarios.extend(feature.scenarios)
                print(f"      -> Got {batch_count} scenarios")
                summary = self._extract_summary(ai_response)
                if summary:
                    combined_summary.append(summary)

            suggestions = self._extract_suggestions(ai_response)
            if suggestions:
                all_suggestions.update(suggestions)

        # Combine results
        if output_format == "traditional":
            # Re-number test cases sequentially
            for idx, tc in enumerate(all_test_cases, 1):
                tc.test_case_no = idx

            combined_suite = TraditionalTestSuite(
                id=f"traditional_{datetime.now().timestamp()}",
                name=f"Data Validation Test Suite - {form_name or data_dictionary.name}",
                description=f"Comprehensive validation testing for {total_rows} fields",
                test_cases=all_test_cases
            )

            actual_count = len(all_test_cases)
            print(f"    Generated {actual_count} total validation test cases from {num_batches} batches (expected ~{expected_min_scenarios}+)")

            if actual_count < expected_min_scenarios:
                warning_msg = f"Generated {actual_count} test cases for {total_rows} fields. Expected ~{expected_min_scenarios}+. Some validations may be missing."
                warnings.append(warning_msg)
                print(f"    [WARNING] {warning_msg}")

            return {
                "test_suite": combined_suite,
                "summary": f"Generated {actual_count} validation test cases for {total_rows} data dictionary entries.",
                "suggestions": list(all_suggestions)[:10],
                "warnings": warnings,
                "batches_processed": num_batches,
                "field_count": total_rows,
                "scenario_count": actual_count
            }
        else:
            combined_feature = GherkinFeature(
                id=f"feature_{datetime.now().timestamp()}",
                name=f"Data Validation - {form_name or data_dictionary.name}",
                description=f"Comprehensive validation testing for {total_rows} fields",
                scenarios=all_scenarios
            )

            actual_count = len(all_scenarios)
            print(f"    Generated {actual_count} total validation scenarios from {num_batches} batches (expected ~{expected_min_scenarios}+)")

            if actual_count < expected_min_scenarios:
                warning_msg = f"Generated {actual_count} scenarios for {total_rows} fields. Expected ~{expected_min_scenarios}+. Some validations may be missing."
                warnings.append(warning_msg)
                print(f"    [WARNING] {warning_msg}")

            return {
                "feature": combined_feature,
                "summary": f"Generated {actual_count} validation scenarios for {total_rows} data dictionary entries.",
                "suggestions": list(all_suggestions)[:10],
                "warnings": warnings,
                "batches_processed": num_batches,
                "field_count": total_rows,
                "scenario_count": actual_count
            }

    def _build_data_dictionary_prompt(
        self,
        data_dictionary: DataDictionary,
        form_name: Optional[str] = None,
        project_context: Optional[str] = None,
        base_url: Optional[str] = None,
        output_format: str = "gherkin"
    ) -> str:
        """Build prompt for data dictionary validation scenarios"""

        context_info = f"\n\nProject Context:\n{project_context}" if project_context else ""
        base_url_info = f"\n\nApplication URL: {base_url}" if base_url else ""
        form_info = f"\n\nForm/Page Name: {form_name}" if form_name else ""

        # Use raw table format if available (AI interprets the structure)
        if data_dictionary.headers and data_dictionary.raw_rows:
            raw_table = data_dictionary.to_raw_table()  # Include ALL rows
            return self._build_smart_data_dict_prompt(raw_table, form_info, context_info, base_url_info, output_format)
        else:
            # Fallback to legacy parsed format
            field_definitions = data_dictionary.to_prompt_context()
            if output_format == "traditional":
                return self._build_data_dict_traditional_prompt(field_definitions, form_info, context_info, base_url_info)
            else:
                return self._build_data_dict_gherkin_prompt(field_definitions, form_info, context_info, base_url_info)

    def _build_smart_data_dict_prompt(
        self,
        raw_table: str,
        form_info: str,
        context_info: str,
        base_url_info: str,
        output_format: str = "gherkin"
    ) -> str:
        """Build optimized prompt for data dictionary - explicit about scenario count"""

        # Count rows to set expectations
        row_count = raw_table.count('\n') - 2  # Subtract header lines

        # Compact format instructions
        if output_format == "gherkin":
            format_instructions = """OUTPUT: Gherkin JSON
{{"summary":"...","feature_name":"Data Validation - [Form]","scenarios":[{{"name":"...","tags":["@validation"],"steps":[{{"keyword":"Given|When|Then|And","text":"..."}}]}}],"suggestions":[]}}
Keywords: Given, When, Then, And, But only"""
        else:
            format_instructions = """OUTPUT: Traditional JSON
{{"summary":"...","suite_name":"Data Validation","test_cases":[{{"test_case_no":1,"scenario_name":"...","precondition":"...","steps":"1...\\n2...","expected_outcome":"...","post_condition":"...","tags":[]}}],"suggestions":[]}}"""

        return f"""QA Engineer: Generate validation tests from this DATA DICTIONARY.
{raw_table}{form_info}{context_info}{base_url_info}

ANALYZE columns for: field names, data types, mandatory flags (Y/N), validation rules, field types.

CRITICAL: Generate 2-4 SEPARATE scenarios PER FIELD based on its attributes:
1. If MANDATORY=Y: Create "Verify [field] is required" scenario (leave empty, expect error)
2. If has DATA TYPE: Create "Verify [field] accepts only [type]" scenario (enter invalid type, expect error)
3. If has BUSINESS RULE: Create "Verify [field] rule: [rule]" scenario (violate rule, expect error)
4. ALWAYS create "Verify [field] accepts valid input" scenario (positive case)

Expected output: ~{row_count * 2}-{row_count * 4} scenarios for {row_count} fields.
DO NOT consolidate multiple fields into one scenario. Each scenario tests ONE field.

{format_instructions}

REQUIREMENTS:
- Generate SEPARATE scenarios for EACH field (2-4 scenarios per field)
- Use actual field names from the data
- Return ONLY valid JSON, no truncation"""

    def _build_data_dict_gherkin_prompt(
        self,
        field_definitions: str,
        form_info: str,
        context_info: str,
        base_url_info: str
    ) -> str:
        """Build Gherkin prompt for data dictionary validation"""

        return f"""You are an expert QA engineer creating VALIDATION test scenarios in Gherkin format.

{field_definitions}{form_info}{context_info}{base_url_info}

Generate comprehensive Gherkin validation scenarios based on the data dictionary above.

REQUIREMENTS:

1. GENERATE VALIDATION SCENARIOS FOR EACH FIELD:
   For each field in the data dictionary, create scenarios for:

   a) REQUIRED FIELD VALIDATION (if field is required):
      - Empty/blank value should show error
      - Valid value should be accepted

   b) DATA TYPE VALIDATION:
      - Invalid type should show error (e.g., letters in number field)
      - Valid type should be accepted

   c) LENGTH VALIDATION (if min/max length defined):
      - Below minimum length should show error
      - Above maximum length should show error
      - Exactly at minimum length should be accepted
      - Exactly at maximum length should be accepted

   d) VALUE RANGE VALIDATION (if min/max value defined):
      - Below minimum value should show error
      - Above maximum value should show error
      - Boundary values should be tested

   e) ALLOWED VALUES VALIDATION (if options defined):
      - Invalid option should show error
      - Each valid option should be accepted

   f) PATTERN VALIDATION (if pattern defined):
      - Invalid format should show error
      - Valid format should be accepted

2. USE SCENARIO OUTLINES for similar validations with different data

3. PROPER JSON FORMAT:

{{
  "summary": "Validation test scenarios for [form name] based on data dictionary",
  "feature_name": "Data Validation - [Form/Feature Name]",
  "feature_description": "Comprehensive validation testing based on data dictionary specifications",
  "scenarios": [
    {{
      "name": "Required field - [Field Name] cannot be empty",
      "tags": ["@validation", "@required", "@negative"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the form page"}},
        {{"keyword": "When", "text": "I leave the \"[Field Name]\" field empty"}},
        {{"keyword": "And", "text": "I submit the form"}},
        {{"keyword": "Then", "text": "I should see an error message \"[Field Name] is required\""}}
      ]
    }},
    {{
      "name": "Length validation - [Field Name] minimum length",
      "tags": ["@validation", "@boundary", "@negative"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the form page"}},
        {{"keyword": "When", "text": "I enter a value with less than [min] characters in \"[Field Name]\""}},
        {{"keyword": "And", "text": "I submit the form"}},
        {{"keyword": "Then", "text": "I should see an error message about minimum length"}}
      ]
    }},
    {{
      "name": "Data type validation - [Field Name] accepts only [type]",
      "tags": ["@validation", "@datatype", "@negative"],
      "is_outline": true,
      "steps": [
        {{"keyword": "Given", "text": "I am on the form page"}},
        {{"keyword": "When", "text": "I enter <invalid_value> in the \"[Field Name]\" field"}},
        {{"keyword": "And", "text": "I submit the form"}},
        {{"keyword": "Then", "text": "I should see <expected_error>"}}
      ],
      "examples": [
        {{"invalid_value": "abc", "expected_error": "Please enter a valid number"}},
        {{"invalid_value": "12.34.56", "expected_error": "Invalid format"}}
      ]
    }}
  ],
  "suggestions": [
    "Test field interactions and dependencies",
    "Test form submission with all valid data",
    "Test error message clarity and positioning"
  ]
}}

4. KEYWORD RULES (ONLY USE THESE 5):
   Given, When, Then, And, But

5. PLAIN ENGLISH STEPS - NO technical locators

6. GENERATE scenarios for ALL fields in the data dictionary

Return ONLY valid JSON, no markdown blocks, no explanations."""

    def _build_data_dict_traditional_prompt(
        self,
        field_definitions: str,
        form_info: str,
        context_info: str,
        base_url_info: str
    ) -> str:
        """Build Traditional prompt for data dictionary validation"""

        return f"""You are an expert QA engineer creating VALIDATION test cases in TRADITIONAL TABLE FORMAT.

{field_definitions}{form_info}{context_info}{base_url_info}

Generate comprehensive validation test cases based on the data dictionary above.

REQUIREMENTS:

1. GENERATE TEST CASES FOR EACH FIELD covering:
   - Required field validation
   - Data type validation
   - Length validation (min/max)
   - Value range validation (min/max)
   - Allowed values validation
   - Pattern/format validation
   - Boundary value testing

2. PROPER JSON FORMAT:

{{
  "summary": "Validation test cases for [form name] based on data dictionary",
  "suite_name": "Data Validation Test Suite",
  "suite_description": "Comprehensive validation testing based on data dictionary specifications",
  "test_cases": [
    {{
      "test_case_no": 1,
      "scenario_name": "Verify [Field Name] is required",
      "precondition": "1. User is on the form page\\n2. Form is empty",
      "steps": "1. Leave [Field Name] field empty\\n2. Fill all other required fields with valid data\\n3. Click Submit button",
      "expected_outcome": "1. Form is not submitted\\n2. Error message displays: '[Field Name] is required'\\n3. [Field Name] field is highlighted",
      "post_condition": "User remains on form page with error displayed",
      "tags": ["@validation", "@required", "@negative"]
    }},
    {{
      "test_case_no": 2,
      "scenario_name": "Verify [Field Name] minimum length validation",
      "precondition": "1. User is on the form page\\n2. [Field Name] has min length of [X] characters",
      "steps": "1. Enter [X-1] characters in [Field Name]\\n2. Click Submit button",
      "expected_outcome": "1. Validation error displays\\n2. Message indicates minimum length requirement",
      "post_condition": "Form not submitted, error shown",
      "tags": ["@validation", "@boundary", "@negative"]
    }},
    {{
      "test_case_no": 3,
      "scenario_name": "Verify [Field Name] accepts valid [data type]",
      "precondition": "1. User is on the form page",
      "steps": "1. Enter valid [data type] value in [Field Name]\\n2. Submit form",
      "expected_outcome": "1. Field accepts the value\\n2. No validation error for this field",
      "post_condition": "Field value is accepted",
      "tags": ["@validation", "@positive"]
    }}
  ],
  "suggestions": [
    "Test field interactions",
    "Test with boundary values",
    "Test error message clarity"
  ]
}}

3. TAGS TO USE:
   - @validation - All validation tests
   - @required - Required field tests
   - @boundary - Boundary value tests
   - @positive - Valid input tests
   - @negative - Invalid input tests
   - @datatype - Data type validation

4. Generate test cases for ALL fields in the data dictionary

Return ONLY valid JSON, no markdown blocks, no explanations."""

    def _build_credentials_context(self, credentials: Optional[List[TestCredential]]) -> str:
        """Build context string for available credentials/roles"""
        if not credentials or len(credentials) == 0:
            return ""

        roles_list = [f"  - {cred.role_name}" for cred in credentials]

        return f"""

AVAILABLE USER ROLES (use these in test scenarios):
{chr(10).join(roles_list)}

When writing login/authentication steps, reference these roles directly:
- "I log in as {credentials[0].role_name}" - Uses {credentials[0].role_name} credentials
- "I am logged in as admin" - Uses admin credentials (if available)
- "I authenticate as standard_user" - Uses standard_user credentials (if available)

The test executor will automatically use the correct credentials for each role."""

    def _build_traditional_prompt(self, brd_content: str, project_context: Optional[str] = None, base_url: Optional[str] = None, end_to_end: bool = False, ui_config: Optional[UIFrameworkConfig] = None, credentials: Optional[List[TestCredential]] = None) -> str:
        """Build prompt for Traditional table format test cases"""
        context_info = f"\n\nProject Context:\n{project_context}" if project_context else ""
        base_url_info = f"\n\nApplication URL: {base_url}" if base_url else ""

        # Build framework context if available
        framework_context = ""
        if ui_config and ui_config.frameworks:
            framework_context = build_framework_context(
                ui_config.frameworks,
                ui_config.primary_framework
            )

        # Build credentials context
        credentials_context = self._build_credentials_context(credentials)

        scenario_count = "15-25" if end_to_end else "10-15"

        return f"""You are an expert QA engineer creating test cases in TRADITIONAL TABLE FORMAT.

Business Requirements Document:
{brd_content}{context_info}{base_url_info}{framework_context}{credentials_context}

Generate {scenario_count} test cases in TRADITIONAL TABLE FORMAT with these columns:
- Test Case No: Sequential number (TC001, TC002, etc.)
- Scenario Name: Clear, descriptive name of the test scenario
- Precondition: What must be true BEFORE the test starts
- Steps: Numbered steps to execute (1. Step one 2. Step two)
- Expected Outcome: What should happen when steps are executed correctly
- Post Condition: State of system AFTER test completes

REQUIREMENTS:

1. BALANCED COVERAGE:
   - Positive scenarios (5-6): Successful operations, happy paths
   - Negative scenarios (3-4): Error handling, validation failures
   - Edge cases (2-3): Boundary conditions, special inputs
   - Alternative flows (1-2): Different valid approaches

2. EACH TEST CASE MUST HAVE:
   - Clear, unique scenario name
   - Specific preconditions (not vague)
   - Numbered steps (1. 2. 3. etc.)
   - Measurable expected outcomes
   - Post conditions describing system state

3. PROPER JSON FORMAT:

{{
  "summary": "2-3 sentence summary of what these test cases cover",
  "suite_name": "Feature Name - Test Suite",
  "suite_description": "Brief description of the test suite",
  "test_cases": [
    {{
      "test_case_no": 1,
      "scenario_name": "Verify successful user login with valid credentials",
      "precondition": "1. User account exists in system\\n2. User is on login page\\n3. User has valid credentials",
      "steps": "1. Enter valid username in username field\\n2. Enter valid password in password field\\n3. Click Login button",
      "expected_outcome": "1. User is redirected to dashboard\\n2. Welcome message displays username\\n3. User session is created",
      "post_condition": "1. User is logged in\\n2. Session token is stored\\n3. Login timestamp is recorded",
      "tags": ["@smoke", "@positive", "@login"]
    }},
    {{
      "test_case_no": 2,
      "scenario_name": "Verify error message for invalid password",
      "precondition": "1. User account exists\\n2. User is on login page",
      "steps": "1. Enter valid username\\n2. Enter incorrect password\\n3. Click Login button",
      "expected_outcome": "1. Error message 'Invalid credentials' displays\\n2. User remains on login page\\n3. Password field is cleared",
      "post_condition": "1. User is not logged in\\n2. Failed login attempt is logged",
      "tags": ["@negative", "@validation", "@login"]
    }},
    {{
      "test_case_no": 3,
      "scenario_name": "Verify password field minimum length validation",
      "precondition": "1. User is on registration/login page\\n2. Password policy requires minimum 8 characters",
      "steps": "1. Enter username\\n2. Enter password with only 5 characters\\n3. Attempt to submit",
      "expected_outcome": "1. Validation error shows 'Password must be at least 8 characters'\\n2. Form is not submitted",
      "post_condition": "1. User remains on current page\\n2. Form data is preserved",
      "tags": ["@edge-case", "@boundary", "@validation"]
    }}
  ],
  "suggestions": [
    "Test with different user roles",
    "Verify session timeout behavior",
    "Test concurrent login attempts"
  ]
}}

4. TAGS TO USE:
   - @smoke - Critical path tests
   - @positive - Happy path scenarios
   - @negative - Error/failure scenarios
   - @edge-case - Boundary conditions
   - @validation - Input validation tests
   - @regression - Full regression tests

5. CRITICAL REMINDERS:
   - Generate exactly {scenario_count} test cases
   - Use \\n for line breaks within fields
   - Number all steps and conditions
   - Be specific, not vague
   - Include measurable outcomes

Return ONLY valid JSON, no markdown blocks, no explanations."""

    def _parse_traditional_response(self, response: str) -> TraditionalTestSuite:
        """Parse AI response into TraditionalTestSuite object with truncation repair"""

        try:
            # Clean the response
            cleaned = response.strip()

            # Remove markdown code blocks if present
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            cleaned = cleaned.strip()

            # Extract JSON if wrapped in text
            if not cleaned.startswith("{"):
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned = cleaned[start:end]

            # Try to parse JSON, repair if truncated
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON parse failed, attempting repair: {str(e)[:100]}")
                repaired = self._repair_truncated_json(cleaned)
                try:
                    data = json.loads(repaired)
                    print(f"[OK] JSON repair successful")
                except json.JSONDecodeError:
                    print(f"[WARN] Repair failed, extracting partial data...")
                    data = self._extract_partial_traditional_json(cleaned)

            # Extract test cases
            test_cases = []
            for idx, tc_data in enumerate(data.get("test_cases", [])):
                test_case = TraditionalTestCase(
                    test_case_no=tc_data.get("test_case_no", idx + 1),
                    scenario_name=tc_data.get("scenario_name", f"Test Case {idx + 1}"),
                    precondition=tc_data.get("precondition", ""),
                    steps=tc_data.get("steps", ""),
                    expected_outcome=tc_data.get("expected_outcome", ""),
                    post_condition=tc_data.get("post_condition", ""),
                    tags=tc_data.get("tags", [])
                )
                test_cases.append(test_case)

            # Create test suite
            test_suite = TraditionalTestSuite(
                id=f"traditional_{datetime.now().timestamp()}",
                name=data.get("suite_name", "Generated Test Suite"),
                description=data.get("suite_description"),
                test_cases=test_cases
            )

            return test_suite

        except Exception as e:
            print(f"[ERR] Parse Error: {str(e)}")
            print(f"Response: {response[:500]}")
            raise Exception(f"Failed to parse Traditional response: {str(e)}")

    def _build_e2e_prompt(self, brd_content: str, project_context: Optional[str] = None, base_url: Optional[str] = None, ui_config: Optional[UIFrameworkConfig] = None, credentials: Optional[List[TestCredential]] = None) -> str:
        """Build E2E prompt for ONE comprehensive end-to-end scenario"""
        context_info = f"\n\nProject Context:\n{project_context}" if project_context else ""
        base_url_info = f"\n\nApplication URL: {base_url}" if base_url else ""

        # Build framework context if available
        framework_context = ""
        if ui_config and ui_config.frameworks:
            framework_context = build_framework_context(
                ui_config.frameworks,
                ui_config.primary_framework
            )

        # Build credentials context
        credentials_context = self._build_credentials_context(credentials)

        return f"""You are an expert QA engineer creating ONE comprehensive END-TO-END test scenario in Gherkin format.

Business Requirements Document:
{brd_content}{context_info}{base_url_info}{framework_context}{credentials_context}

Generate a SINGLE, COMPREHENSIVE Gherkin scenario that covers the COMPLETE HAPPY PATH user journey from start to finish.

REQUIREMENTS FOR END-TO-END SCENARIO:

1. ONE COMPLETE USER JOURNEY (15-30 steps):
   - Start from the very beginning (login, home page, landing page)
   - Include EVERY step the user takes
   - Include ALL page transitions
   - Include ALL data entry and selections
   - End with final success and cleanup
   - Be thorough and detailed - don't skip steps

2. HAPPY PATH ONLY:
   - This is the successful, ideal journey
   - No errors, no edge cases, no negative scenarios
   - Everything works perfectly
   - User completes the full workflow successfully

3. PROPER JSON FORMAT:

{{
  "summary": "Complete end-to-end happy path from start to finish",
  "feature_name": "End-to-End [Feature Name] - Complete User Journey",
  "feature_description": "Comprehensive test covering the complete happy path workflow",
  "background": [
    {{"keyword": "Given", "text": "the application is running"}},
    {{"keyword": "And", "text": "I have access to the system"}}
  ],
  "scenarios": [
    {{
      "name": "Complete end-to-end happy path - Full user journey",
      "tags": ["@e2e", "@happy-path", "@smoke", "@critical"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the [start page]"}},
        {{"keyword": "When", "text": "I [first action]"}},
        {{"keyword": "And", "text": "I [second action]"}},
        {{"keyword": "And", "text": "I [third action]"}},
        {{"keyword": "Then", "text": "I should see [first result]"}},
        {{"keyword": "When", "text": "I navigate to [next page]"}},
        {{"keyword": "And", "text": "I [next action]"}},
        {{"keyword": "And", "text": "I [continue workflow]"}},
        {{"keyword": "Then", "text": "I should see [progress]"}},
        {{"keyword": "When", "text": "I complete [final steps]"}},
        {{"keyword": "Then", "text": "I should see success"}},
        {{"keyword": "And", "text": "the workflow should be complete"}}
      ]
    }}
  ],
  "suggestions": [
    "Consider testing error scenarios separately",
    "Test with different user types",
    "Verify data persistence"
  ]
}}

4. KEYWORD RULES (USE ONLY THESE 5):
   [OK] Given, When, Then, And, But
   [ERR] NEVER: Or, Also, Additionally, Furthermore, Moreover, However, Though, Although

5. PLAIN ENGLISH STEPS (CRITICAL - NO TECHNICAL LOCATORS):
   [ERR] NEVER include CSS selectors, XPath, data-testid, or any technical locators in steps
   [ERR] WRONG: I fill in '[data-testid="email"]' with 'test@example.com'
   [ERR] WRONG: I click '[data-test="submit-btn"]'

   [OK] CORRECT: I fill in the "Email" field with my email
   [OK] CORRECT: I click the "Submit" button
   [OK] CORRECT: I select "Option A" from the "Category" dropdown

   RULES FOR FIELD REFERENCES:
   - Use human-readable labels in double quotes: "First Name", "Email", "Password"
   - Describe buttons by their visible text: the "Sign Up" button
   - Use descriptive names, not technical IDs or selectors

6. CRITICAL REMINDERS:
   - Generate EXACTLY ONE scenario
   - That ONE scenario should have 15-30 detailed steps
   - Cover the COMPLETE workflow from start to finish
   - This is HAPPY PATH ONLY - everything succeeds
   - Include every step - be thorough

GENERATE ONE COMPREHENSIVE SCENARIO WITH 15-30 STEPS.
Return ONLY valid JSON, no markdown blocks, no explanations."""

    def _build_focused_prompt(self, brd_content: str, project_context: Optional[str] = None, base_url: Optional[str] = None, ui_config: Optional[UIFrameworkConfig] = None, credentials: Optional[List[TestCredential]] = None) -> str:
        """Build focused prompt for 10-15 specific scenarios"""
        context_info = f"\n\nProject Context:\n{project_context}" if project_context else ""
        base_url_info = f"\n\nApplication URL: {base_url}" if base_url else ""

        # Build framework context if available
        framework_context = ""
        if ui_config and ui_config.frameworks:
            framework_context = build_framework_context(
                ui_config.frameworks,
                ui_config.primary_framework
            )

        # Build credentials context
        credentials_context = self._build_credentials_context(credentials)

        return f"""You are an expert QA engineer creating focused test scenarios in Gherkin format.

Business Requirements Document:
{brd_content}{context_info}{base_url_info}{framework_context}{credentials_context}

Generate a Gherkin feature file with 10-15 practical, functional test scenarios.

REQUIREMENTS:

1. FOCUSED TESTING (10-15 scenarios):
   - Test specific features/functions
   - Isolated, independent scenarios
   - Clear, concise test cases
   - Each scenario tests ONE specific aspect

2. BALANCED COVERAGE:
   - Positive scenarios (5-6): Successful operations, happy paths
   - Negative scenarios (3-4): Error handling, validation failures
   - Edge cases (2-3): Boundary conditions, special inputs
   - Alternative flows (1-2): Different valid approaches

3. PROPER GHERKIN STRUCTURE with JSON FORMAT:

{{
  "summary": "2-3 sentence summary of what this feature does",
  "feature_name": "Clear, user-friendly feature name",
  "feature_description": "Brief description of the feature",
  "background": [
    {{"keyword": "Given", "text": "I am on the application"}},
    {{"keyword": "And", "text": "I am logged in as a user"}}
  ],
  "scenarios": [
    {{
      "name": "User successfully creates an account",
      "tags": ["@smoke", "@positive"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the registration page"}},
        {{"keyword": "When", "text": "I fill in the \"First Name\" field with a valid first name"}},
        {{"keyword": "And", "text": "I fill in the \"Last Name\" field with the last name"}},
        {{"keyword": "And", "text": "I fill in the \"Email\" field with my email"}},
        {{"keyword": "And", "text": "I fill in the \"Password\" field with my password"}},
        {{"keyword": "And", "text": "I click the \"Sign Up\" button"}},
        {{"keyword": "Then", "text": "I should see a welcome message"}},
        {{"keyword": "And", "text": "I should be redirected to the dashboard"}}
      ]
    }},
    {{
      "name": "Validation fails with missing required field",
      "tags": ["@negative", "@validation"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the registration form"}},
        {{"keyword": "When", "text": "I leave the \"Email\" field empty"}},
        {{"keyword": "And", "text": "I click the \"Submit\" button"}},
        {{"keyword": "Then", "text": "I should see an error message \"Email is required\""}},
        {{"keyword": "And", "text": "the form should not be submitted"}}
      ]
    }},
    {{
      "name": "Input validation with various data types",
      "tags": ["@negative", "@validation"],
      "is_outline": true,
      "steps": [
        {{"keyword": "Given", "text": "I am on the input form"}},
        {{"keyword": "When", "text": "I enter <input>"}},
        {{"keyword": "And", "text": "I submit"}},
        {{"keyword": "Then", "text": "I should see <result>"}}
      ],
      "examples": [
        {{"input": "valid_data", "result": "success"}},
        {{"input": "", "result": "error: required"}},
        {{"input": "invalid_format", "result": "error: invalid format"}},
        {{"input": "too_short", "result": "error: minimum length"}},
        {{"input": "too_long", "result": "error: maximum length"}}
      ]
    }},
    {{
      "name": "Boundary - Minimum valid value accepted",
      "tags": ["@edge-case", "@boundary"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the input form"}},
        {{"keyword": "When", "text": "I enter the minimum valid value"}},
        {{"keyword": "And", "text": "I submit"}},
        {{"keyword": "Then", "text": "the input should be accepted"}}
      ]
    }},
    {{
      "name": "Boundary - Maximum valid value accepted",
      "tags": ["@edge-case", "@boundary"],
      "steps": [
        {{"keyword": "Given", "text": "I am on the input form"}},
        {{"keyword": "When", "text": "I enter the maximum valid value"}},
        {{"keyword": "And", "text": "I submit"}},
        {{"keyword": "Then", "text": "the input should be accepted"}}
      ]
    }}
  ],
  "suggestions": [
    "Test with different user roles",
    "Verify data persistence",
    "Test concurrent user actions",
    "Verify audit logging"
  ]
}}

4. KEYWORD RULES (CRITICAL - ONLY USE THESE 5):
   [OK] Given - Setup/preconditions
   [OK] When - Actions/events
   [OK] Then - Expected results
   [OK] And - Continue previous keyword
   [OK] But - Negative continuation

   [ERR] NEVER use: Or, Also, Additionally, Furthermore, Moreover, However, Though, Although

5. PLAIN ENGLISH STEPS (CRITICAL - NO TECHNICAL LOCATORS):
   [ERR] NEVER include CSS selectors, XPath, data-testid, or any technical locators in steps
   [ERR] WRONG: I fill in '[data-testid="first-name"]' with 'John'
   [ERR] WRONG: I click the element '[data-test="submit"]'
   [ERR] WRONG: I enter text in '#username'

   [OK] CORRECT: I fill in the "First Name" field with a valid first name
   [OK] CORRECT: I click the "Submit" button
   [OK] CORRECT: I enter my email in the "Email" field
   [OK] CORRECT: I select "United States" from the "Country" dropdown

   RULES FOR FIELD REFERENCES:
   - Use human-readable labels in double quotes: "First Name", "Email", "Password"
   - Describe buttons by their visible text: the "Sign Up" button, the "Login" button
   - Describe links by their text: the "Forgot Password" link
   - Use descriptive names, not technical IDs or selectors
   - The test executor will automatically find the correct element

   TEST DATA VALUES (CRITICAL - USE NATURAL LANGUAGE, NOT HARDCODED):
   [ERR] WRONG: I enter "john@example.com" in the "Email" field (hardcoded)
   [ERR] WRONG: I fill in the "Password" field with "SecurePass123" (hardcoded)
   
   [OK] CORRECT: I enter my email in the "Email" field
   [OK] CORRECT: I enter my username in the "Username" field  
   [OK] CORRECT: I enter my password in the "Password" field
   [OK] CORRECT: I enter my password in the "Confirm Password" field
   [OK] CORRECT: I fill in the "First Name" field with a valid first name
   [OK] CORRECT: I fill in the "Last Name" field with the last name
   [OK] CORRECT: I enter a valid phone number in the "Phone" field
   [OK] CORRECT: I fill in the "Address" field with a valid address

   NATURAL LANGUAGE PATTERNS FOR TEST DATA:
   - "my {{field}}" - for credential fields (username, password, email)
   - "a valid {{field}}" - for fields needing generated valid data
   - "the {{field}}" - for general fields
   - "a new {{field}}" - for registration/creation scenarios
   
   The test framework will automatically resolve these to:
   1. Project credentials (if configured)
   2. Auto-generated realistic data (if enabled)

6. SCENARIO DISTRIBUTION FOR FOCUSED (10-15 total):
   - 5-6 positive scenarios (successful operations)
   - 3-4 negative scenarios (validation, error handling)
   - 2-3 edge cases (boundaries, special inputs)
   - 1-2 alternative flows

GENERATE 10-15 FOCUSED SCENARIOS.
Return ONLY valid JSON, no markdown blocks, no explanations."""
    
    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM"""
        
        if self.api_type == "ollama":
            return self._call_ollama(prompt)
        elif self.api_type == "openai":
            return self._call_openai(prompt)
        elif self.api_type == "anthropic":
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown API type: {self.api_type}")
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        response = requests.post(self.api_url, json=payload, timeout=600)
        response.raise_for_status()
        return response.json().get("response", "")
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 32000  # Increased for larger outputs
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(self.api_url, json=payload, headers=headers, timeout=300)  # Increased timeout
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API with streaming for long requests"""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        # Use streaming to handle long-running requests
        full_response = ""
        with client.messages.stream(
            model=self.model,
            max_tokens=16000,  # Reasonable limit per request
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                full_response += text

        return full_response
    
    def _sanitize_step_keyword(self, keyword_str: str) -> str:
        """Auto-correct invalid Gherkin keywords"""
        keyword_str = str(keyword_str).strip()
    
        valid_keywords = ["Given", "When", "Then", "And", "But"]
        if keyword_str in valid_keywords:
            return keyword_str
    
        invalid_to_valid = {
            "Or": "And",
            "Also": "And",
            "Additionally": "And",
            "Furthermore": "And",
            "Moreover": "And",
            "However": "But",
            "Though": "But",
            "Although": "But",
        }
    
        if keyword_str in invalid_to_valid:
            print(f"[WARN] Warning: Invalid keyword '{keyword_str}' replaced with '{invalid_to_valid[keyword_str]}'")
            return invalid_to_valid[keyword_str]
    
        print(f"[WARN] Warning: Unknown keyword '{keyword_str}' replaced with 'And'")
        return "And"
    
    def _repair_truncated_json(self, json_str: str) -> str:
        """Attempt to repair truncated JSON by closing open structures"""
        # Count open brackets/braces
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')

        # Check for unterminated strings
        in_string = False
        escaped = False
        for char in json_str:
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == '"':
                in_string = not in_string

        repaired = json_str

        # Close unterminated string
        if in_string:
            repaired += '"'

        # Remove trailing comma if present before closing
        repaired = repaired.rstrip()
        if repaired.endswith(','):
            repaired = repaired[:-1]

        # Close open brackets and braces
        repaired += ']' * open_brackets
        repaired += '}' * open_braces

        return repaired

    def _extract_partial_json(self, json_str: str) -> dict:
        """Extract partial data from truncated JSON - last resort"""
        import re

        # Try to find and extract complete scenarios
        scenarios = []

        # Find all complete scenario objects using regex
        # Look for patterns like {"name": "...", "tags": [...], "steps": [...]}
        scenario_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"tags"\s*:\s*\[[^\]]*\]\s*,\s*"steps"\s*:\s*\[(?:[^\[\]]*|\[(?:[^\[\]]*|\[[^\[\]]*\])*\])*\]\s*\}'

        matches = re.findall(scenario_pattern, json_str, re.DOTALL)
        for match in matches:
            try:
                scenario = json.loads(match)
                scenarios.append(scenario)
            except:
                continue

        # Extract feature name and summary if present
        feature_name = "Partial Data Validation"
        summary = "Partial extraction due to truncated response"

        name_match = re.search(r'"feature_name"\s*:\s*"([^"]+)"', json_str)
        if name_match:
            feature_name = name_match.group(1)

        summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', json_str)
        if summary_match:
            summary = summary_match.group(1)

        print(f"[INFO] Extracted {len(scenarios)} complete scenarios from truncated response")

        return {
            "summary": summary,
            "feature_name": feature_name,
            "feature_description": "Partially recovered from truncated AI response",
            "scenarios": scenarios,
            "suggestions": ["Response was truncated - some scenarios may be missing"]
        }

    def _extract_partial_traditional_json(self, json_str: str) -> dict:
        """Extract partial traditional test cases from truncated JSON"""
        import re

        test_cases = []

        # Find complete test case objects
        tc_pattern = r'\{\s*"test_case_no"\s*:\s*\d+\s*,\s*"scenario_name"\s*:\s*"[^"]*"[^}]*"post_condition"\s*:\s*"[^"]*"[^}]*\}'

        matches = re.findall(tc_pattern, json_str, re.DOTALL)
        for match in matches:
            try:
                # Try to parse as-is first
                tc = json.loads(match)
                test_cases.append(tc)
            except:
                # Try to repair the match
                try:
                    repaired = self._repair_truncated_json(match)
                    tc = json.loads(repaired)
                    test_cases.append(tc)
                except:
                    continue

        # Extract suite name if present
        suite_name = "Partial Test Suite"
        name_match = re.search(r'"suite_name"\s*:\s*"([^"]+)"', json_str)
        if name_match:
            suite_name = name_match.group(1)

        print(f"[INFO] Extracted {len(test_cases)} complete test cases from truncated response")

        return {
            "summary": "Partial extraction due to truncated response",
            "suite_name": suite_name,
            "suite_description": "Partially recovered from truncated AI response",
            "test_cases": test_cases,
            "suggestions": ["Response was truncated - some test cases may be missing"]
        }

    def _parse_gherkin_response(self, response: str) -> GherkinFeature:
        """Parse AI response into GherkinFeature object with truncation repair"""

        data = None

        try:
            # Clean the response
            cleaned = response.strip()

            # Remove markdown code blocks if present
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            cleaned = cleaned.strip()

            # Extract JSON if wrapped in text
            if not cleaned.startswith("{"):
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned = cleaned[start:end]

            # Try to parse JSON with multiple fallback strategies
            # Strategy 1: Direct parse
            try:
                data = json.loads(cleaned)
                print(f"[OK] JSON parsed successfully")
            except json.JSONDecodeError as e1:
                print(f"[WARN] JSON parse failed: {str(e1)[:80]}")

                # Strategy 2: Repair truncated JSON
                try:
                    repaired = self._repair_truncated_json(cleaned)
                    data = json.loads(repaired)
                    print(f"[OK] JSON repair successful")
                except Exception as e2:
                    print(f"[WARN] Repair failed: {str(e2)[:80]}")

                    # Strategy 3: Extract partial data using regex
                    try:
                        data = self._extract_partial_json(cleaned)
                        print(f"[OK] Partial extraction got {len(data.get('scenarios', []))} scenarios")
                    except Exception as e3:
                        print(f"[ERR] Partial extraction failed: {str(e3)[:80]}")
                        # Create empty result rather than failing completely
                        data = {
                            "summary": "Failed to parse AI response",
                            "feature_name": "Parse Error",
                            "scenarios": [],
                            "suggestions": ["AI response was truncated or malformed"]
                        }

            # Ensure data is valid
            if not isinstance(data, dict):
                data = {"scenarios": [], "feature_name": "Unknown", "summary": "Invalid response"}
            
            # Extract background steps
            background_steps = []
            if data.get("background"):
                for step_data in data["background"]:
                    keyword_str = self._sanitize_step_keyword(step_data["keyword"])
                    step = GherkinStep(
                        keyword=StepKeyword(keyword_str),
                        text=step_data["text"]
                    )
                    background_steps.append(step)
            
            # Extract scenarios
            scenarios = []
            for scenario_data in data.get("scenarios", []):
                steps = []
                for step_data in scenario_data.get("steps", []):
                    keyword_str = self._sanitize_step_keyword(step_data["keyword"])
                    step = GherkinStep(
                        keyword=StepKeyword(keyword_str),
                        text=step_data["text"]
                    )
                    steps.append(step)
                
                scenario = GherkinScenario(
                    name=scenario_data.get("name", "Untitled Scenario"),
                    tags=scenario_data.get("tags", []),
                    steps=steps
                )
                scenarios.append(scenario)
            
            # Create feature
            from datetime import datetime
            feature = GherkinFeature(
                id=f"feature_{datetime.now().timestamp()}",
                name=data.get("feature_name", "Generated Feature"),
                description=data.get("feature_description"),
                background=background_steps if background_steps else None,
                scenarios=scenarios
            )
            
            return feature
            
        except Exception as e:
            print(f"[ERR] Parse Error: {str(e)}")
            print(f"Response: {response[:500]}")
            raise Exception(f"Failed to parse Gherkin response: {str(e)}")
    
    def _extract_summary(self, response: str) -> str:
        """Extract BRD summary from response"""
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            cleaned = cleaned.strip()
            if not cleaned.startswith("{"):
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned = cleaned[start:end]
            
            data = json.loads(cleaned)
            return data.get("summary", "")
        except:
            return ""
    
    def _extract_suggestions(self, response: str) -> List[str]:
        """Extract suggestions from response"""
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            cleaned = cleaned.strip()
            if not cleaned.startswith("{"):
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned = cleaned[start:end]
            
            data = json.loads(cleaned)
            return data.get("suggestions", [])
        except:
            return []


# ============================================
# HELPER FUNCTIONS (Outside the class)
# ============================================

def get_gherkin_generator():
    """Get configured Gherkin AI generator"""
    return AIGherkinGenerator()


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except ImportError:
        raise Exception("python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        import pdfplumber 
        with pdfplumber.open(file_path) as pdf:
            return '\n'.join([page.extract_text() for page in pdf.pages])
    except ImportError:
        raise Exception("pdfplumber not installed. Run: pip install pdfplumber")
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def extract_text_from_file(file_path: str) -> str:
    """Extract text from file based on extension"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.txt':
        return extract_text_from_txt(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.pdf':
        return extract_text_from_pdf(file_path)
    else:
        raise Exception(f"Unsupported file format: {ext}")
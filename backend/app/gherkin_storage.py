"""
Gherkin Storage - Extends your existing Storage class
"""

import json
import os
from typing import List, Optional
from datetime import datetime
import uuid

from models_gherkin import (
    GherkinFeature, GherkinScenario, GherkinStep, StepKeyword,
    TraditionalTestSuite, TraditionalTestCase
)


class GherkinStorage:
    """Handle Gherkin feature and Traditional test case storage in JSON files"""

    def __init__(self, data_folder: str = "data"):
        self.features_folder = os.path.join(data_folder, "features")
        self.results_folder = os.path.join(data_folder, "results")
        self.traditional_folder = os.path.join(data_folder, "traditional")

        # Create folders if they don't exist
        os.makedirs(self.features_folder, exist_ok=True)
        os.makedirs(self.results_folder, exist_ok=True)
        os.makedirs(self.traditional_folder, exist_ok=True)
    
    def save_feature(self, feature: GherkinFeature, project_id: str = None, folder_id: str = None) -> dict:
        """Save a Gherkin feature to JSON"""

        # Use folder_id from feature if not explicitly provided
        effective_folder_id = folder_id if folder_id is not None else getattr(feature, 'folder_id', None)

        feature_dict = {
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "created_at": feature.created_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "project_id": project_id,
            "folder_id": effective_folder_id,
            "background": [
                {"keyword": step.keyword.value, "text": step.text}
                for step in (feature.background or [])
            ],
            "scenarios": [
                {
                    "name": scenario.name,
                    "tags": scenario.tags,
                    "description": scenario.description,
                    "steps": [
                        {"keyword": step.keyword.value, "text": step.text}
                        for step in scenario.steps
                    ]
                }
                for scenario in feature.scenarios
            ],
            "gherkin_content": feature.to_gherkin()
        }
        
        # Save to file
        file_path = os.path.join(self.features_folder, f"{feature.id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(feature_dict, f, indent=2, ensure_ascii=False)
        
        return feature_dict
    
    def load_feature(self, feature_id: str) -> Optional[GherkinFeature]:
        """Load a Gherkin feature from JSON"""
        
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to GherkinFeature
        background = None
        if data.get("background"):
            background = [
                GherkinStep(keyword=StepKeyword(step["keyword"]), text=step["text"])
                for step in data["background"]
            ]
        
        scenarios = []
        for scenario_data in data.get("scenarios", []):
            steps = [
                GherkinStep(keyword=StepKeyword(step["keyword"]), text=step["text"])
                for step in scenario_data["steps"]
            ]
            
            scenario = GherkinScenario(
                name=scenario_data["name"],
                tags=scenario_data.get("tags", []),
                steps=steps,
                description=scenario_data.get("description")
            )
            scenarios.append(scenario)
        
        feature = GherkinFeature(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            background=background,
            scenarios=scenarios,
            folder_id=data.get("folder_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
        
        return feature
    
    def load_feature_dict(self, feature_id: str) -> Optional[dict]:
        """Load feature as dictionary"""
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_features(self, project_id: str = None) -> List[dict]:
        """List all features"""
        features = []
        
        for filename in os.listdir(self.features_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.features_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    feature_data = json.load(f)
                    
                    if project_id is None or feature_data.get("project_id") == project_id:
                        scenarios = feature_data.get("scenarios", [])
                        # Add id to each scenario if missing
                        for idx, scenario in enumerate(scenarios):
                            if "id" not in scenario:
                                scenario["id"] = f"{feature_data['id']}_scenario_{idx}"

                        features.append({
                            "id": feature_data["id"],
                            "name": feature_data["name"],
                            "description": feature_data.get("description"),
                            "scenarios": scenarios,
                            "scenario_count": len(scenarios),
                            "created_at": feature_data["created_at"],
                            "updated_at": feature_data["updated_at"],
                            "project_id": feature_data.get("project_id"),
                            "folder_id": feature_data.get("folder_id")
                        })
        
        return features
    
    def save_execution_result(self, result: dict) -> dict:
        """Save test execution result"""
        
        if "id" not in result:
            result["id"] = str(uuid.uuid4())
        
        result["executed_at"] = datetime.now().isoformat()
        
        file_path = os.path.join(self.results_folder, f"{result['id']}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result
    
    def load_execution_results(self, feature_id: str = None, limit: int = 10) -> List[dict]:
        """Load execution results"""
        results = []

        for filename in os.listdir(self.results_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.results_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)

                    if feature_id is None or result_data.get("feature_id") == feature_id:
                        results.append(result_data)

        results.sort(key=lambda x: x.get("executed_at", ""), reverse=True)
        return results[:limit]


    def update_feature_folder(self, feature_id: str, folder_id: str = None) -> Optional[dict]:
        """Update a feature's folder_id"""
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            feature_data = json.load(f)

        feature_data["folder_id"] = folder_id
        feature_data["updated_at"] = datetime.now().isoformat()

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(feature_data, f, indent=2, ensure_ascii=False)

        return feature_data

    def list_features_by_folder(self, project_id: str, folder_id: str = None) -> List[dict]:
        """List features in a specific folder (None = root level)"""
        features = []

        for filename in os.listdir(self.features_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.features_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    feature_data = json.load(f)

                    # Check project_id and folder_id match
                    if feature_data.get("project_id") == project_id:
                        feature_folder_id = feature_data.get("folder_id")
                        if feature_folder_id == folder_id:
                            scenarios = feature_data.get("scenarios", [])
                            # Add id to each scenario if missing
                            for idx, scenario in enumerate(scenarios):
                                if "id" not in scenario:
                                    scenario["id"] = f"{feature_data['id']}_scenario_{idx}"

                            features.append({
                                "id": feature_data["id"],
                                "name": feature_data["name"],
                                "description": feature_data.get("description"),
                                "scenarios": scenarios,
                                "scenario_count": len(scenarios),
                                "created_at": feature_data["created_at"],
                                "updated_at": feature_data["updated_at"],
                                "project_id": feature_data.get("project_id"),
                                "folder_id": feature_folder_id
                            })

        return features

    def delete_feature(self, feature_id: str) -> bool:
        """Delete a Gherkin feature"""
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def add_discovered_steps_to_scenario(
        self,
        feature_id: str,
        scenario_name: str,
        discovered_steps: List[dict],
        insert_before_step_keyword: str = "When",
        update_related_scenarios: bool = True
    ) -> bool:
        """
        Add discovered steps to a scenario in the Gherkin feature.

        This is called when the AI discovers missing steps during execution.
        The steps are added to the Gherkin file so future runs don't need AI.

        Args:
            feature_id: The feature ID
            scenario_name: Name of the scenario to update
            discovered_steps: List of steps to add, each with:
                - keyword: "And" or step keyword
                - text: Step text like 'I enter "value" in the "Confirm Password" field'
                - field_name: The field name (for smart duplicate detection)
            insert_before_step_keyword: Insert steps before first step with this keyword
            update_related_scenarios: If True, also update similar scenarios in the same feature

        Returns:
            True if updated successfully
        """
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")

        if not os.path.exists(file_path):
            print(f"[GHERKIN-UPDATE] Feature file not found: {feature_id}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                feature_data = json.load(f)

            updated = False
            scenarios_updated = []

            # Determine which scenarios to update
            scenarios_to_update = []
            for scenario in feature_data.get("scenarios", []):
                if scenario["name"] == scenario_name:
                    scenarios_to_update.append(scenario)
                elif update_related_scenarios:
                    # Check if this scenario uses the same page/form
                    if self._scenarios_share_context(scenario, scenario_name, feature_data):
                        scenarios_to_update.append(scenario)

            for scenario in scenarios_to_update:
                existing_steps = scenario.get("steps", [])

                # Find insertion point (before first "When" or "Then" step)
                insert_idx = len(existing_steps)
                for i, step in enumerate(existing_steps):
                    if step.get("keyword", "").lower() in [insert_before_step_keyword.lower(), "then"]:
                        insert_idx = i
                        break

                # SMART DUPLICATE DETECTION
                new_steps = []
                for step in discovered_steps:
                    field_name = step.get("field_name", "").lower()
                    step_text = step.get("text", "")

                    # Check if this field is already being handled
                    if self._field_already_handled(field_name, step_text, existing_steps):
                        print(f"[GHERKIN-UPDATE] Skipping '{field_name}' - already handled in '{scenario['name']}'")
                        continue

                    new_steps.append({
                        "keyword": step.get("keyword", "And"),
                        "text": step_text
                    })

                if new_steps:
                    # Insert new steps
                    for i, step in enumerate(new_steps):
                        existing_steps.insert(insert_idx + i, step)

                    scenario["steps"] = existing_steps
                    updated = True
                    scenarios_updated.append(scenario["name"])
                    print(f"[GHERKIN-UPDATE] Added {len(new_steps)} step(s) to scenario '{scenario['name']}'")
                    for step in new_steps:
                        print(f"  + {step['keyword']} {step['text']}")

            if updated:
                # Update timestamp
                feature_data["updated_at"] = datetime.now().isoformat()

                # Regenerate gherkin_content
                feature_data["gherkin_content"] = self._regenerate_gherkin_content(feature_data)

                # Save back
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(feature_data, f, indent=2, ensure_ascii=False)

                print(f"[GHERKIN-UPDATE] Feature '{feature_id}' updated - {len(scenarios_updated)} scenario(s) modified")
                return True
            else:
                print(f"[GHERKIN-UPDATE] No new steps to add (all fields already handled)")
                return False

        except Exception as e:
            print(f"[GHERKIN-UPDATE] Error updating feature: {e}")
            return False

    def _field_already_handled(self, field_name: str, step_text: str, existing_steps: List[dict]) -> bool:
        """
        Smart duplicate detection - check if a field is already being handled.

        Checks for:
        1. Exact step text match
        2. Field name mentioned in any existing step
        3. Similar field patterns (e.g., "password" matches "confirm password" context)
        """
        field_name_lower = field_name.lower()
        step_text_lower = step_text.lower()

        # Extract key identifiers from field name
        field_keywords = [w for w in field_name_lower.split() if len(w) > 2]

        for existing in existing_steps:
            existing_text = existing.get("text", "").lower()

            # Check 1: Exact or near-exact match
            if step_text_lower in existing_text or existing_text in step_text_lower:
                return True

            # Check 2: Field name explicitly mentioned
            if field_name_lower in existing_text:
                return True

            # Check 3: All key words from field name appear in step
            if field_keywords and all(kw in existing_text for kw in field_keywords):
                return True

            # Check 4: Common field patterns
            # e.g., if we're adding "confirm password" and there's already a step with "confirm" and "password"
            if 'confirm' in field_name_lower:
                base_field = field_name_lower.replace('confirm', '').strip()
                if base_field and base_field in existing_text and 'confirm' in existing_text:
                    return True

        return False

    def _scenarios_share_context(self, scenario: dict, reference_scenario_name: str, feature_data: dict) -> bool:
        """
        Check if two scenarios share the same page/form context.

        Scenarios are considered related if they:
        1. Have similar names (e.g., "User Registration" and "Registration Validation")
        2. Share the same Given steps (same starting page)
        3. Are in the same feature and have similar step patterns
        """
        scenario_name = scenario.get("name", "").lower()
        reference_lower = reference_scenario_name.lower()

        # Extract key words from scenario names
        ref_keywords = set(w for w in reference_lower.split() if len(w) > 3)
        scenario_keywords = set(w for w in scenario_name.split() if len(w) > 3)

        # Check 1: Significant keyword overlap (>50%)
        if ref_keywords and scenario_keywords:
            overlap = len(ref_keywords & scenario_keywords)
            if overlap >= len(ref_keywords) * 0.5:
                return True

        # Check 2: Same page indicators
        page_indicators = ['registration', 'register', 'signup', 'sign up', 'login', 'signin',
                          'checkout', 'payment', 'profile', 'settings', 'account']

        ref_page = None
        scenario_page = None

        for indicator in page_indicators:
            if indicator in reference_lower:
                ref_page = indicator
            if indicator in scenario_name:
                scenario_page = indicator

        if ref_page and scenario_page and ref_page == scenario_page:
            return True

        # Check 3: Check Given steps for same page navigation
        scenario_steps = scenario.get("steps", [])
        ref_scenario = None
        for s in feature_data.get("scenarios", []):
            if s.get("name") == reference_scenario_name:
                ref_scenario = s
                break

        if ref_scenario:
            ref_given_steps = [s.get("text", "").lower() for s in ref_scenario.get("steps", [])
                              if s.get("keyword", "").lower() == "given"]
            scenario_given_steps = [s.get("text", "").lower() for s in scenario_steps
                                   if s.get("keyword", "").lower() == "given"]

            # If they share Given steps, they're on the same page
            if ref_given_steps and scenario_given_steps:
                if any(g in scenario_given_steps for g in ref_given_steps):
                    return True

        return False

    def analyze_and_create_background(self, feature_id: str) -> bool:
        """
        Analyze scenarios and create a Background from common steps.

        This is how an experienced tester thinks:
        1. Look at all scenarios
        2. Find steps that appear in ALL scenarios (usually Given steps)
        3. Extract them to a Background section
        4. Remove duplicates from individual scenarios

        Returns:
            True if Background was created/updated
        """
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")

        if not os.path.exists(file_path):
            print(f"[BACKGROUND] Feature file not found: {feature_id}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                feature_data = json.load(f)

            scenarios = feature_data.get("scenarios", [])
            existing_background = feature_data.get("background", [])

            if len(scenarios) < 2:
                print(f"[BACKGROUND] Need at least 2 scenarios to extract Background")
                return False

            # Find common steps across ALL scenarios
            common_steps = self._find_common_steps(scenarios)

            if not common_steps:
                print(f"[BACKGROUND] No common steps found across scenarios")
                return False

            # Filter to only Given/And steps (setup steps)
            setup_steps = []
            for step in common_steps:
                keyword = step.get("keyword", "").lower()
                if keyword in ["given", "and"]:
                    setup_steps.append(step)

            if not setup_steps:
                print(f"[BACKGROUND] No common setup steps (Given/And) found")
                return False

            # Check if these steps are already in Background
            existing_texts = [s.get("text", "").lower() for s in existing_background]
            new_background_steps = []

            for step in setup_steps:
                step_text = step.get("text", "").lower()
                if not any(step_text in existing or existing in step_text for existing in existing_texts):
                    new_background_steps.append(step)

            if not new_background_steps:
                print(f"[BACKGROUND] Common steps already in Background")
                return False

            # Create/update Background
            if existing_background:
                feature_data["background"] = existing_background + new_background_steps
            else:
                # Convert first step to "Given" keyword
                new_background_steps[0]["keyword"] = "Given"
                for step in new_background_steps[1:]:
                    step["keyword"] = "And"
                feature_data["background"] = new_background_steps

            # Remove common steps from individual scenarios
            for scenario in scenarios:
                scenario["steps"] = self._remove_common_steps(scenario["steps"], new_background_steps)

            # Update timestamp
            feature_data["updated_at"] = datetime.now().isoformat()

            # Regenerate gherkin_content
            feature_data["gherkin_content"] = self._regenerate_gherkin_content(feature_data)

            # Save back
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(feature_data, f, indent=2, ensure_ascii=False)

            print(f"[BACKGROUND] Created Background with {len(new_background_steps)} step(s):")
            for step in new_background_steps:
                print(f"  + {step['keyword']} {step['text']}")

            return True

        except Exception as e:
            print(f"[BACKGROUND] Error analyzing feature: {e}")
            return False

    def _find_common_steps(self, scenarios: List[dict]) -> List[dict]:
        """Find steps that appear in ALL scenarios"""
        if not scenarios:
            return []

        # Get steps from first scenario as candidates
        first_scenario_steps = scenarios[0].get("steps", [])

        common_steps = []
        for step in first_scenario_steps:
            step_text = step.get("text", "").lower().strip()

            # Check if this step appears in ALL other scenarios
            appears_in_all = True
            for scenario in scenarios[1:]:
                scenario_steps = scenario.get("steps", [])
                found = False
                for s in scenario_steps:
                    s_text = s.get("text", "").lower().strip()
                    # Check for exact match or semantic similarity
                    if step_text == s_text or self._steps_are_similar(step_text, s_text):
                        found = True
                        break
                if not found:
                    appears_in_all = False
                    break

            if appears_in_all:
                common_steps.append(step.copy())

        return common_steps

    def _steps_are_similar(self, step1: str, step2: str) -> bool:
        """Check if two steps are semantically similar"""
        # Extract key parts
        s1_words = set(w for w in step1.split() if len(w) > 3)
        s2_words = set(w for w in step2.split() if len(w) > 3)

        if not s1_words or not s2_words:
            return False

        # Calculate overlap
        overlap = len(s1_words & s2_words)
        total = max(len(s1_words), len(s2_words))

        # Consider similar if >70% overlap
        return (overlap / total) >= 0.7

    def _remove_common_steps(self, scenario_steps: List[dict], common_steps: List[dict]) -> List[dict]:
        """Remove common steps from a scenario's step list"""
        common_texts = [s.get("text", "").lower().strip() for s in common_steps]

        filtered_steps = []
        for step in scenario_steps:
            step_text = step.get("text", "").lower().strip()

            # Check if this step is in common steps
            is_common = False
            for common_text in common_texts:
                if step_text == common_text or self._steps_are_similar(step_text, common_text):
                    is_common = True
                    break

            if not is_common:
                filtered_steps.append(step)

        # Ensure first remaining step has proper keyword
        if filtered_steps:
            first_keyword = filtered_steps[0].get("keyword", "").lower()
            if first_keyword == "and":
                # Change to appropriate keyword based on context
                filtered_steps[0]["keyword"] = "When"

        return filtered_steps

    def suggest_background_from_kb(self, feature_id: str, knowledge_base_path: str = "data/agent_knowledge") -> List[dict]:
        """
        Suggest Background steps based on learned knowledge about the page.

        This uses the Knowledge Base to understand:
        1. What page this feature operates on
        2. What setup steps are typically needed for that page
        3. What the system has learned from previous executions

        Returns:
            List of suggested Background steps
        """
        file_path = os.path.join(self.features_folder, f"{feature_id}.json")

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                feature_data = json.load(f)

            feature_name = feature_data.get("name", "").lower()
            scenarios = feature_data.get("scenarios", [])

            # Determine what page/flow this feature is about
            page_indicators = {
                "registration": ["navigate to registration page", "open registration form"],
                "login": ["navigate to login page", "open login form"],
                "checkout": ["navigate to checkout", "open shopping cart"],
                "profile": ["navigate to profile page", "open user profile"],
                "search": ["navigate to search page", "open search"],
            }

            suggested_steps = []

            # Check feature name for page indicators
            for page, setup_steps in page_indicators.items():
                if page in feature_name:
                    # Check if scenarios already have navigation
                    has_navigation = False
                    for scenario in scenarios:
                        for step in scenario.get("steps", []):
                            step_text = step.get("text", "").lower()
                            if "navigate" in step_text or "open" in step_text or "go to" in step_text:
                                has_navigation = True
                                break

                    if not has_navigation:
                        suggested_steps.append({
                            "keyword": "Given",
                            "text": f"I navigate to the {page} page"
                        })
                    break

            # Check KB for learned setup steps
            kb_learnings_dir = os.path.join(knowledge_base_path, "scenario_learnings")
            if os.path.exists(kb_learnings_dir):
                for filename in os.listdir(kb_learnings_dir):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(kb_learnings_dir, filename), 'r') as f:
                                learning = json.load(f)

                            # Check if this learning is relevant to our feature
                            learning_page = learning.get("page", "").lower()
                            if any(indicator in feature_name for indicator in learning_page.split("/")):
                                # Add discovered fields as potential setup
                                for field in learning.get("discovered_fields", []):
                                    if field.get("is_required"):
                                        field_name = field.get("field_name", "")
                                        suggested_steps.append({
                                            "keyword": "And",
                                            "text": f"the {field_name} field is visible",
                                            "source": "learned_from_kb"
                                        })
                        except:
                            continue

            return suggested_steps

        except Exception as e:
            print(f"[KB-SUGGEST] Error: {e}")
            return []

    def _regenerate_gherkin_content(self, feature_data: dict) -> str:
        """Regenerate the Gherkin text content from feature data"""
        lines = []

        # Feature header
        lines.append(f"Feature: {feature_data.get('name', 'Unknown')}")
        if feature_data.get("description"):
            for desc_line in feature_data["description"].split("\n"):
                lines.append(f"  {desc_line}")
        lines.append("")

        # Background
        if feature_data.get("background"):
            lines.append("  Background:")
            for step in feature_data["background"]:
                lines.append(f"    {step['keyword']} {step['text']}")
            lines.append("")

        # Scenarios
        for scenario in feature_data.get("scenarios", []):
            # Tags
            if scenario.get("tags"):
                lines.append(f"  {' '.join(scenario['tags'])}")

            lines.append(f"  Scenario: {scenario['name']}")

            if scenario.get("description"):
                lines.append(f"    {scenario['description']}")

            for step in scenario.get("steps", []):
                lines.append(f"    {step['keyword']} {step['text']}")

            lines.append("")

        return "\n".join(lines)

    # ============ TRADITIONAL TEST SUITE METHODS ============

    def save_traditional_suite(self, suite: TraditionalTestSuite, project_id: str = None) -> dict:
        """Save a Traditional test suite to JSON"""

        suite_dict = {
            "id": suite.id,
            "name": suite.name,
            "description": suite.description,
            "created_at": suite.created_at.isoformat() if hasattr(suite.created_at, 'isoformat') else str(suite.created_at),
            "updated_at": datetime.now().isoformat(),
            "project_id": project_id,
            "test_cases": [
                {
                    "test_case_no": tc.test_case_no,
                    "scenario_name": tc.scenario_name,
                    "precondition": tc.precondition,
                    "steps": tc.steps,
                    "expected_outcome": tc.expected_outcome,
                    "post_condition": tc.post_condition,
                    "tags": tc.tags
                }
                for tc in suite.test_cases
            ]
        }

        # Save to file
        file_path = os.path.join(self.traditional_folder, f"{suite.id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(suite_dict, f, indent=2, ensure_ascii=False)

        return suite_dict

    def load_traditional_suite(self, suite_id: str) -> Optional[TraditionalTestSuite]:
        """Load a Traditional test suite from JSON"""

        file_path = os.path.join(self.traditional_folder, f"{suite_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert back to TraditionalTestSuite
        test_cases = []
        for tc_data in data.get("test_cases", []):
            test_case = TraditionalTestCase(
                test_case_no=tc_data["test_case_no"],
                scenario_name=tc_data["scenario_name"],
                precondition=tc_data["precondition"],
                steps=tc_data["steps"],
                expected_outcome=tc_data["expected_outcome"],
                post_condition=tc_data["post_condition"],
                tags=tc_data.get("tags", [])
            )
            test_cases.append(test_case)

        suite = TraditionalTestSuite(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            test_cases=test_cases,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

        return suite

    def load_traditional_suite_dict(self, suite_id: str) -> Optional[dict]:
        """Load Traditional test suite as dictionary"""
        file_path = os.path.join(self.traditional_folder, f"{suite_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_traditional_suites(self, project_id: str = None) -> List[dict]:
        """List all Traditional test suites"""
        suites = []

        if not os.path.exists(self.traditional_folder):
            return suites

        for filename in os.listdir(self.traditional_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.traditional_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    suite_data = json.load(f)

                    if project_id is None or suite_data.get("project_id") == project_id:
                        suites.append({
                            "id": suite_data["id"],
                            "name": suite_data["name"],
                            "description": suite_data.get("description"),
                            "test_case_count": len(suite_data.get("test_cases", [])),
                            "created_at": suite_data["created_at"],
                            "updated_at": suite_data["updated_at"],
                            "project_id": suite_data.get("project_id")
                        })

        return suites

    def delete_traditional_suite(self, suite_id: str) -> bool:
        """Delete a Traditional test suite"""
        file_path = os.path.join(self.traditional_folder, f"{suite_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def update_traditional_suite_folder(self, suite_id: str, folder_id: str = None) -> Optional[dict]:
        """Update a traditional suite's folder"""
        file_path = os.path.join(self.traditional_folder, f"{suite_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            suite_data = json.load(f)

        suite_data["folder_id"] = folder_id
        suite_data["updated_at"] = datetime.now().isoformat()

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(suite_data, f, indent=2, ensure_ascii=False)

        return suite_data

    def list_traditional_suites_by_folder(self, project_id: str, folder_id: str = None) -> List[dict]:
        """List traditional suites by folder (None = root/uncategorized)"""
        suites = []

        if not os.path.exists(self.traditional_folder):
            return suites

        for filename in os.listdir(self.traditional_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.traditional_folder, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        suite_data = json.load(f)

                        # Filter by project if specified
                        if project_id and suite_data.get("project_id") != project_id:
                            continue

                        # Filter by folder
                        suite_folder_id = suite_data.get("folder_id")
                        if suite_folder_id == folder_id:
                            suites.append({
                                "id": suite_data["id"],
                                "name": suite_data["name"],
                                "description": suite_data.get("description"),
                                "test_case_count": len(suite_data.get("test_cases", [])),
                                "folder_id": suite_folder_id,
                                "created_at": suite_data.get("created_at"),
                                "project_id": suite_data.get("project_id")
                            })
                except Exception as e:
                    print(f"Error loading suite {filename}: {e}")
                    continue

        return suites



# Singleton
_gherkin_storage = None

def get_gherkin_storage(data_folder: str = "data") -> GherkinStorage:
    """Get Gherkin storage instance"""
    global _gherkin_storage
    if _gherkin_storage is None:
        _gherkin_storage = GherkinStorage(data_folder)
    return _gherkin_storage
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
                        features.append({
                            "id": feature_data["id"],
                            "name": feature_data["name"],
                            "description": feature_data.get("description"),
                            "scenario_count": len(feature_data.get("scenarios", [])),
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
                            features.append({
                                "id": feature_data["id"],
                                "name": feature_data["name"],
                                "description": feature_data.get("description"),
                                "scenario_count": len(feature_data.get("scenarios", [])),
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
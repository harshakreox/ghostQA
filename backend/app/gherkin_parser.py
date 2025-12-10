"""
Gherkin Parser
Parses .feature files into structured GherkinFeature objects
"""

import re
from typing import List, Optional
from models_gherkin import GherkinFeature, GherkinScenario, GherkinStep, StepKeyword


class GherkinParser:
    """Parse Gherkin .feature files into structured objects"""
    
    @staticmethod
    def parse_feature(content: str, feature_id: str = None) -> GherkinFeature:
        """
        Parse a complete .feature file content into a GherkinFeature object
        
        Args:
            content: The .feature file content as string
            feature_id: Optional ID for the feature
            
        Returns:
            GherkinFeature object
        """
        lines = content.strip().split('\n')
        
        # Parse feature name and description
        feature_name = ""
        feature_description = ""
        background_steps = []
        scenarios = []
        
        current_section = None
        current_scenario = None
        current_steps = []
        current_tags = []
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                i += 1
                continue
            
            # Feature declaration
            if stripped.startswith('Feature:'):
                feature_name = stripped.replace('Feature:', '').strip()
                current_section = 'feature'
                i += 1
                continue
            
            # Feature description (indented text after Feature:)
            if current_section == 'feature' and line.startswith('  ') and not stripped.startswith(('Background:', 'Scenario:', '@', 'Given', 'When', 'Then', 'And', 'But', '#')):
                feature_description += stripped + ' '
                i += 1
                continue
            
            # Background section
            if stripped.startswith('Background:'):
                current_section = 'background'
                current_steps = []
                i += 1
                continue
            
            # Tags (start with @)
            if stripped.startswith('@'):
                current_tags = stripped.split()
                i += 1
                continue
            
            # Scenario declaration
            if stripped.startswith('Scenario:'):
                # Save previous scenario if exists
                if current_scenario and current_steps:
                    current_scenario.steps = current_steps
                    scenarios.append(current_scenario)
                
                # Start new scenario
                scenario_name = stripped.replace('Scenario:', '').strip()
                current_scenario = GherkinScenario(
                    name=scenario_name,
                    tags=current_tags,
                    steps=[]
                )
                current_steps = []
                current_tags = []
                current_section = 'scenario'
                i += 1
                continue
            
            # Comment lines (skip)
            if stripped.startswith('#'):
                i += 1
                continue
            
            # Gherkin steps (Given, When, Then, And, But)
            step_match = re.match(r'\s*(Given|When|Then|And|But)\s+(.+)', line)
            if step_match:
                keyword_str, text = step_match.groups()
                keyword = StepKeyword(keyword_str)
                step = GherkinStep(keyword=keyword, text=text.strip())
                
                if current_section == 'background':
                    background_steps.append(step)
                elif current_section == 'scenario':
                    current_steps.append(step)
                
                i += 1
                continue
            
            i += 1
        
        # Save last scenario
        if current_scenario and current_steps:
            current_scenario.steps = current_steps
            scenarios.append(current_scenario)
        
        # Create feature object
        from datetime import datetime
        feature = GherkinFeature(
            id=feature_id or f"feature_{datetime.now().timestamp()}",
            name=feature_name,
            description=feature_description.strip() or None,
            background=background_steps if background_steps else None,
            scenarios=scenarios
        )
        
        return feature
    
    @staticmethod
    def parse_feature_from_file(file_path: str) -> GherkinFeature:
        """Parse a .feature file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import os
        feature_id = os.path.splitext(os.path.basename(file_path))[0]
        return GherkinParser.parse_feature(content, feature_id)
    
    @staticmethod
    def extract_scenario_by_name(feature: GherkinFeature, scenario_name: str) -> Optional[GherkinScenario]:
        """Extract a specific scenario by name"""
        for scenario in feature.scenarios:
            if scenario.name.lower() == scenario_name.lower():
                return scenario
        return None
    
    @staticmethod
    def extract_scenarios_by_tags(feature: GherkinFeature, tags: List[str]) -> List[GherkinScenario]:
        """Extract scenarios that have any of the specified tags"""
        matching_scenarios = []
        for scenario in feature.scenarios:
            if any(tag in scenario.tags for tag in tags):
                matching_scenarios.append(scenario)
        return matching_scenarios
    
    @staticmethod
    def validate_feature(feature: GherkinFeature) -> List[str]:
        """
        Validate a feature for common issues
        Returns list of validation errors (empty if valid)
        """
        errors = []
        
        if not feature.name:
            errors.append("Feature must have a name")
        
        if not feature.scenarios:
            errors.append("Feature must have at least one scenario")
        
        for idx, scenario in enumerate(feature.scenarios):
            if not scenario.name:
                errors.append(f"Scenario {idx + 1} must have a name")
            
            if not scenario.steps:
                errors.append(f"Scenario '{scenario.name}' must have at least one step")
            
            # Check for proper Given-When-Then flow
            has_given = any(s.keyword == StepKeyword.GIVEN for s in scenario.steps)
            has_when = any(s.keyword == StepKeyword.WHEN for s in scenario.steps)
            has_then = any(s.keyword == StepKeyword.THEN for s in scenario.steps)
            
            if not has_given:
                errors.append(f"Scenario '{scenario.name}' should have at least one Given step")
            if not has_when:
                errors.append(f"Scenario '{scenario.name}' should have at least one When step")
            if not has_then:
                errors.append(f"Scenario '{scenario.name}' should have at least one Then step")
        
        return errors


# Utility function for quick parsing
def parse_gherkin(content: str) -> GherkinFeature:
    """Quick utility to parse Gherkin content"""
    return GherkinParser.parse_feature(content)
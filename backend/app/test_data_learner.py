"""
Test Data Learner
Learns new field types and patterns from test execution.
Stores learned mappings persistently for future use.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


class TestDataLearner:
    """
    Learns and remembers field type classifications.
    When encountering unknown fields, it uses heuristics to classify them
    and stores the mappings for future use.
    """

    # Knowledge base file location
    KNOWLEDGE_FILE = "data/test_data_knowledge.json"

    # Heuristic patterns for classifying unknown fields
    # These are broader patterns used when exact match fails
    CLASSIFICATION_HINTS = {
        # Name-related fields
        'name': {
            'hints': ['name', 'nm', 'nombre', 'nom'],
            'data_type': 'name',
            'generator': 'generate_full_name'
        },
        'first_name': {
            'hints': ['first', 'given', 'fname', 'forename', 'prenom'],
            'data_type': 'first_name',
            'generator': 'generate_first_name'
        },
        'last_name': {
            'hints': ['last', 'sur', 'family', 'lname', 'apellido'],
            'data_type': 'last_name',
            'generator': 'generate_last_name'
        },

        # Contact fields
        'email': {
            'hints': ['email', 'mail', 'correo', 'e-mail'],
            'data_type': 'email',
            'generator': 'generate_email'
        },
        'phone': {
            'hints': ['phone', 'tel', 'mobile', 'cell', 'fax', 'telefono'],
            'data_type': 'phone',
            'generator': 'generate_phone'
        },

        # Authentication
        'username': {
            'hints': ['user', 'login', 'account', 'usuario'],
            'data_type': 'username',
            'generator': 'generate_username'
        },
        'password': {
            'hints': ['pass', 'pwd', 'secret', 'pin', 'clave'],
            'data_type': 'password',
            'generator': 'generate_password'
        },

        # Address fields
        'street': {
            'hints': ['street', 'address', 'addr', 'line1', 'direccion', 'calle'],
            'data_type': 'street',
            'generator': 'generate_street_address'
        },
        'city': {
            'hints': ['city', 'town', 'ciudad', 'ville'],
            'data_type': 'city',
            'generator': 'generate_city'
        },
        'state': {
            'hints': ['state', 'province', 'region', 'estado'],
            'data_type': 'state',
            'generator': 'generate_state'
        },
        'zip': {
            'hints': ['zip', 'postal', 'postcode', 'codigo'],
            'data_type': 'zip',
            'generator': 'generate_zip_code'
        },
        'country': {
            'hints': ['country', 'nation', 'pais'],
            'data_type': 'country',
            'generator': 'generate_country'
        },

        # Business fields
        'company': {
            'hints': ['company', 'org', 'business', 'employer', 'empresa'],
            'data_type': 'company',
            'generator': 'generate_company'
        },
        'job': {
            'hints': ['job', 'title', 'position', 'role', 'occupation', 'puesto'],
            'data_type': 'job',
            'generator': 'generate_job_title'
        },

        # Date/Time fields
        'date': {
            'hints': ['date', 'day', 'fecha', 'dt'],
            'data_type': 'date',
            'generator': 'generate_date'
        },
        'dob': {
            'hints': ['birth', 'dob', 'birthday', 'nacimiento'],
            'data_type': 'dob',
            'generator': 'generate_date_of_birth'
        },
        'time': {
            'hints': ['time', 'hour', 'hora'],
            'data_type': 'time',
            'generator': 'generate_time'
        },

        # Numeric fields
        'amount': {
            'hints': ['amount', 'price', 'cost', 'total', 'sum', 'value', 'monto'],
            'data_type': 'amount',
            'generator': 'generate_amount'
        },
        'quantity': {
            'hints': ['qty', 'quantity', 'count', 'number', 'num', 'cantidad'],
            'data_type': 'quantity',
            'generator': 'generate_quantity'
        },
        'age': {
            'hints': ['age', 'edad'],
            'data_type': 'age',
            'generator': 'generate_age'
        },

        # Text fields
        'description': {
            'hints': ['desc', 'description', 'detail', 'about', 'bio', 'summary'],
            'data_type': 'description',
            'generator': 'generate_description'
        },
        'comment': {
            'hints': ['comment', 'note', 'message', 'msg', 'feedback', 'remark'],
            'data_type': 'comment',
            'generator': 'generate_comment'
        },
        'url': {
            'hints': ['url', 'link', 'website', 'site', 'href', 'web'],
            'data_type': 'url',
            'generator': 'generate_url'
        },
    }

    def __init__(self, knowledge_dir: str = None):
        """Initialize the learner with optional custom knowledge directory."""
        if knowledge_dir:
            self.knowledge_file = os.path.join(knowledge_dir, "test_data_knowledge.json")
        else:
            # Default to app/data directory
            app_dir = os.path.dirname(os.path.abspath(__file__))
            self.knowledge_file = os.path.join(app_dir, self.KNOWLEDGE_FILE)

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.knowledge_file), exist_ok=True)

        # Load existing knowledge
        self.learned_mappings: Dict[str, Dict] = {}
        self.unknown_fields: List[Dict] = []
        self._load_knowledge()

    def _load_knowledge(self):
        """Load learned mappings from file."""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learned_mappings = data.get('learned_mappings', {})
                    self.unknown_fields = data.get('unknown_fields', [])
                    print(f"[TestDataLearner] Loaded {len(self.learned_mappings)} learned field mappings")
            except Exception as e:
                print(f"[TestDataLearner] Error loading knowledge: {e}")

    def _save_knowledge(self):
        """Save learned mappings to file."""
        try:
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'learned_mappings': self.learned_mappings,
                'unknown_fields': self.unknown_fields[-100:]  # Keep last 100 unknown
            }
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[TestDataLearner] Error saving knowledge: {e}")

    def classify_field(self, field_name: str) -> Tuple[str, str, float]:
        """
        Classify a field based on its name.
        Returns: (data_type, generator_name, confidence)
        """
        field_lower = field_name.lower().strip().replace(' ', '_').replace('-', '_')

        # Check learned mappings first (highest confidence)
        if field_lower in self.learned_mappings:
            mapping = self.learned_mappings[field_lower]
            return mapping['data_type'], mapping['generator'], 1.0

        # Try heuristic classification
        best_match = None
        best_score = 0.0

        for category, info in self.CLASSIFICATION_HINTS.items():
            score = self._calculate_match_score(field_lower, info['hints'])
            if score > best_score:
                best_score = score
                best_match = info

        if best_match and best_score >= 0.5:
            # Good enough match - learn it for next time
            self._learn_mapping(field_lower, best_match['data_type'],
                              best_match['generator'], best_score, 'heuristic')
            return best_match['data_type'], best_match['generator'], best_score

        # Unknown field - log it and return generic text
        self._log_unknown_field(field_name)
        return 'text', 'generate_generic_text', 0.0

    def _calculate_match_score(self, field_name: str, hints: List[str]) -> float:
        """Calculate how well a field name matches a set of hints."""
        max_score = 0.0

        for hint in hints:
            # Exact match
            if field_name == hint:
                return 1.0

            # Contains as whole word
            if re.search(rf'\b{re.escape(hint)}\b', field_name):
                max_score = max(max_score, 0.9)

            # Starts or ends with hint
            if field_name.startswith(hint) or field_name.endswith(hint):
                max_score = max(max_score, 0.8)

            # Contains hint
            if hint in field_name:
                max_score = max(max_score, 0.7)

            # Hint contains field (field is abbreviation)
            if field_name in hint and len(field_name) >= 3:
                max_score = max(max_score, 0.6)

        return max_score

    def _learn_mapping(self, field_name: str, data_type: str, generator: str,
                       confidence: float, source: str):
        """Store a learned mapping."""
        self.learned_mappings[field_name] = {
            'data_type': data_type,
            'generator': generator,
            'confidence': confidence,
            'source': source,
            'learned_at': datetime.now().isoformat(),
            'usage_count': 1
        }
        self._save_knowledge()

    def _log_unknown_field(self, field_name: str):
        """Log an unknown field for later review."""
        entry = {
            'field_name': field_name,
            'encountered_at': datetime.now().isoformat(),
            'status': 'unknown'
        }
        self.unknown_fields.append(entry)
        self._save_knowledge()
        print(f"[TestDataLearner] Unknown field encountered: '{field_name}'")

    def teach(self, field_name: str, data_type: str, generator: str = None):
        """
        Manually teach the learner about a field type.
        This is useful for custom field types specific to your application.
        """
        field_lower = field_name.lower().strip().replace(' ', '_').replace('-', '_')

        # Auto-determine generator if not provided
        if not generator:
            generator = f"generate_{data_type}"

        self._learn_mapping(field_lower, data_type, generator, 1.0, 'manual')
        print(f"[TestDataLearner] Learned: '{field_name}' -> {data_type}")

    def get_unknown_fields(self) -> List[str]:
        """Get list of fields that couldn't be classified."""
        return [f['field_name'] for f in self.unknown_fields if f['status'] == 'unknown']

    def get_statistics(self) -> Dict:
        """Get learning statistics."""
        return {
            'total_learned': len(self.learned_mappings),
            'unknown_count': len([f for f in self.unknown_fields if f['status'] == 'unknown']),
            'sources': {
                'manual': len([m for m in self.learned_mappings.values() if m.get('source') == 'manual']),
                'heuristic': len([m for m in self.learned_mappings.values() if m.get('source') == 'heuristic']),
            }
        }


# Global instance
_learner: Optional[TestDataLearner] = None

def get_learner() -> TestDataLearner:
    """Get or create the global learner instance."""
    global _learner
    if _learner is None:
        _learner = TestDataLearner()
    return _learner


# Convenience functions
def classify_field(field_name: str) -> Tuple[str, str, float]:
    """Classify a field and get its data type."""
    return get_learner().classify_field(field_name)

def teach_field(field_name: str, data_type: str, generator: str = None):
    """Teach the learner about a new field type."""
    get_learner().teach(field_name, data_type, generator)


if __name__ == "__main__":
    # Demo
    print("=== Test Data Learner Demo ===\n")

    learner = TestDataLearner()

    # Test classification of various fields
    test_fields = [
        "First Name",
        "apellido",  # Spanish for last name
        "correo_electronico",  # Spanish for email
        "user_mobile",
        "billing_address_line_1",
        "fecha_nacimiento",  # Spanish for date of birth
        "custom_xyz_field",  # Unknown field
        "employee_id",
        "numero_telefono",  # Spanish for phone number
    ]

    print("Field Classifications:")
    print("-" * 60)

    for field in test_fields:
        data_type, generator, confidence = learner.classify_field(field)
        print(f"{field:30} -> {data_type:15} (confidence: {confidence:.2f})")

    print("\n" + "-" * 60)
    print(f"\nStatistics: {learner.get_statistics()}")
    print(f"Unknown fields: {learner.get_unknown_fields()}")

    # Demo manual teaching
    print("\n--- Teaching custom field ---")
    learner.teach("employee_badge_number", "employee_id")

    # Re-classify
    data_type, generator, confidence = learner.classify_field("employee_badge_number")
    print(f"After teaching: employee_badge_number -> {data_type} (confidence: {confidence:.2f})")

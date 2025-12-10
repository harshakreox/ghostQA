#!/usr/bin/env python3
"""
SauceDemo Test Cases Importer
Automatically imports test cases into GhostQA framework
"""

import requests
import json
import sys

# Configuration
API_BASE_URL = "http://localhost:8000/api"
TEST_CASES_FILE = "saucedemo_test_cases.json"


def import_test_cases():
    """Import SauceDemo test cases into GhostQA"""
    
    print("🚀 SauceDemo Test Cases Importer")
    print("=" * 50)
    
    # Load test cases from JSON
    try:
        with open(TEST_CASES_FILE, 'r') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data['test_cases'])} test cases from file")
    except FileNotFoundError:
        print(f"❌ Error: {TEST_CASES_FILE} not found!")
        print("   Make sure the file is in the same directory as this script.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {TEST_CASES_FILE}")
        sys.exit(1)
    
    # Create project
    print("\n📁 Creating project...")
    try:
        project_data = {
            'name': data['project']['name'],
            'description': data['project']['description'],
            'base_url': data['project']['base_url']
        }
        
        response = requests.post(f"{API_BASE_URL}/projects", json=project_data)
        response.raise_for_status()
        project = response.json()
        project_id = project['id']
        
        print(f"✓ Project created: {project['name']}")
        print(f"  Project ID: {project_id}")
        print(f"  Base URL: {project['base_url']}")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to GhostQA backend!")
        print("   Make sure the backend is running on http://localhost:8000")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating project: {e}")
        sys.exit(1)
    
    # Import test cases
    print(f"\n📝 Importing {len(data['test_cases'])} test cases...")
    print("-" * 50)
    
    imported_count = 0
    failed_count = 0
    
    for idx, test_case in enumerate(data['test_cases'], 1):
        try:
            response = requests.post(
                f"{API_BASE_URL}/projects/{project_id}/test-cases",
                json=test_case
            )
            response.raise_for_status()
            
            print(f"✓ [{idx}/{len(data['test_cases'])}] {test_case['name']}")
            print(f"    {len(test_case['actions'])} actions imported")
            imported_count += 1
            
        except requests.exceptions.RequestException as e:
            print(f"✗ [{idx}/{len(data['test_cases'])}] {test_case['name']} - FAILED")
            print(f"    Error: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Import Summary:")
    print(f"  ✓ Successfully imported: {imported_count}")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count}")
    print(f"  📁 Project ID: {project_id}")
    
    if imported_count == len(data['test_cases']):
        print("\n🎉 All test cases imported successfully!")
        print(f"\n🌐 View your project at:")
        print(f"   http://localhost:3000/projects/{project_id}")
    else:
        print("\n⚠️ Some test cases failed to import.")
        print("   Check the errors above and try again.")
    
    print("\n🚀 Next steps:")
    print("  1. Open GhostQA UI (http://localhost:3000)")
    print("  2. Go to Projects → SauceDemo E2E Tests")
    print("  3. Click 'Run Tests' to execute the test suite")
    print("  4. View results in the Reports section")


if __name__ == "__main__":
    try:
        import_test_cases()
    except KeyboardInterrupt:
        print("\n\n⚠️ Import cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

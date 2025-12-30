# Backend Application Structure

## Overview

This backend serves as the test automation and AI-powered QA platform.

## Directory Structure

```
app/
├── main.py                     # FastAPI application entry point
├── start_server.py             # Server startup script
│
├── agent/                      # Autonomous Test Agent (Core Engine)
│   ├── core/                   # Core agent components
│   │   ├── agent.py            # Main AutonomousTestAgent class
│   │   ├── action_executor.py  # Executes browser actions
│   │   ├── selector_service.py # 5-tier selector resolution
│   │   ├── element_intelligence.py  # Semantic element analysis
│   │   ├── visual_intelligence.py   # Visual/AI-powered analysis
│   │   ├── recovery_handler.py      # Error recovery strategies
│   │   └── spa_handler.py           # SPA framework detection
│   │
│   ├── context/                # Project Context & Navigation
│   │   ├── project_context.py       # Project-specific knowledge
│   │   └── navigation_intelligence.py  # Smart navigation (like a manual tester)
│   │
│   ├── knowledge/              # Knowledge Base System
│   │   ├── knowledge_index.py  # O(1) selector lookup
│   │   ├── learning_engine.py  # Learns from test execution
│   │   ├── pattern_store.py    # Pattern matching storage
│   │   └── framework_selectors.py  # Framework-specific selectors
│   │
│   ├── explorer/               # Application Exploration
│   │   ├── app_explorer.py     # Autonomous app exploration
│   │   ├── element_extractor.py  # DOM element extraction
│   │   └── page_analyzer.py    # Page structure analysis
│   │
│   ├── recorder/               # Action Recording
│   │   └── action_recorder.py  # Records user actions
│   │
│   ├── training/               # Training Data Collection
│   │   ├── data_collector.py   # Collects training data
│   │   └── import_export.py    # Import/export functionality
│   │
│   ├── unified_executor.py     # Unified test execution engine
│   └── project_autonomous_agent.py  # Project-level agent wrapper
│
├── *_api.py                    # API Endpoints
│   ├── agent_api.py            # Agent/test execution endpoints
│   ├── ai_api.py               # AI service endpoints
│   ├── auth_api.py             # Authentication endpoints
│   ├── folder_api.py           # Folder management endpoints
│   └── release_api.py          # Release management endpoints
│
├── *_models.py / models*.py    # Data Models
│   ├── models.py               # Core test models
│   ├── models_gherkin.py       # Gherkin-specific models
│   ├── models_folder.py        # Folder models
│   ├── auth_models.py          # Authentication models
│   └── release_models.py       # Release models
│
├── *_storage.py                # Storage/Persistence
│   ├── storage.py              # Main test storage
│   ├── gherkin_storage.py      # Gherkin file storage
│   ├── folder_storage.py       # Folder storage
│   └── auth_storage.py         # User/auth storage
│
├── gherkin_*.py                # Gherkin Processing
│   ├── gherkin_parser.py       # Parse .feature files
│   ├── gherkin_executor.py     # Execute Gherkin tests
│   └── step_definitions.py     # Generic step definitions
│
├── ai_*.py                     # AI Services
│   ├── ai_gherkin_generator.py # Generate Gherkin from requirements
│   └── ai_test_generator.py    # Generate tests from exploration
│
├── test_data_*.py              # Test Data Management
│   ├── test_data_generator.py  # Generate test data
│   ├── test_data_learner.py    # Learn test data patterns
│   └── test_data_resolver.py   # Resolve test data placeholders
│
├── Utilities
│   ├── html_reporter.py        # Generate HTML reports
│   ├── dom_manager.py          # DOM management utilities
│   ├── framework_library.py    # Framework detection
│   ├── data_dictionary_parser.py  # Data dictionary parsing
│   ├── test_engine.py          # Traditional test engine
│   └── windows_test_runner.py  # Windows-specific runner
│
└── _unused/                    # Deprecated/unused files
    ├── ai_api_ollama.py        # Old Ollama integration
    ├── ai_test_generator_ollama.py
    └── dom_extractor.py        # Old DOM extractor
```

## Key Components

### 1. Autonomous Test Agent (`agent/`)

The heart of the system - an AI-powered test agent that:
- Learns from every test execution
- Resolves selectors using a 5-tier pipeline (KB -> Framework -> Heuristics -> AI -> Fallback)
- Handles SPA frameworks automatically
- Recovers from failures
- Navigates applications like a manual tester

### 2. Navigation Intelligence (`agent/context/`)

**NEW**: Enables the agent to navigate applications intelligently:
- `project_context.py` - Stores project-specific knowledge (pages, navigation paths)
- `navigation_intelligence.py` - Scans DOM, predicts destinations, executes navigation

### 3. Knowledge Base (`agent/knowledge/`)

Self-learning knowledge base that improves over time:
- `knowledge_index.py` - O(1) lookup for known selectors + scenario caching
- `learning_engine.py` - Records successful element interactions
- `pattern_store.py` - Stores patterns for element matching

### 4. API Layer (`*_api.py`)

REST API endpoints for:
- Test execution (agent_api.py)
- AI services (ai_api.py)
- Authentication (auth_api.py)
- Folder/project management (folder_api.py)
- Release management (release_api.py)

## Data Flow

```
User Request → API → Unified Executor → Autonomous Agent
                                            │
                   ┌────────────────────────┼────────────────────────┐
                   │                        │                        │
           Navigation Intel        Selector Service           Action Executor
                   │                        │                        │
           Project Context         Knowledge Base              Browser
                   │                        │                        │
           Learned Paths           Learned Selectors          Test Results
```

## Configuration

- Agent config: `AgentConfig` in `agent/core/agent.py`
- Knowledge storage: `data/agent_knowledge/`
- Project context: `data/project_context/`

# GhostQA - Autonomous Test Automation Framework

A self-learning, AI-powered test automation framework that executes tests like an experienced human tester.

The system learns from every execution to reduce AI dependency over time, achieving true autonomy.

---

## Overview

GhostQA is an intelligent test automation framework that combines traditional test execution with AI-powered autonomous capabilities. Unlike conventional frameworks that require precise selectors, GhostQA understands what you want to test and figures out how to do it.

### The Problem We Solve

Traditional test automation is:
- Brittle - Tests break when selectors change
- Expensive - Requires constant maintenance
- Slow - Developers spend more time fixing tests than writing features

### Our Solution: Semantic Element Intelligence (SEI)

GhostQA introduces SEI - a system that:
- Understands elements by their PURPOSE, not just attributes
- Learns from every execution to improve over time
- Recovers automatically from failures
- Works offline when AI services are unavailable

---

## Key Features

### Autonomous Test Execution
- Self-Learning Agent - Learns from every interaction
- 5-Tier Selector Resolution - Multiple fallback strategies
- Intelligent Recovery - Handles failures gracefully
- AI Dependency Reduction - Becomes smarter over time

### Semantic Element Intelligence (SEI)
- Element DNA - Multi-dimensional fingerprinting
- Intent Resolution - Natural language to element mapping
- Predictive Confidence - Knows which selectors will break
- Page Context Awareness - Understands page types

### Modern Test Management
- Visual Test Editor - No coding required
- Gherkin/BDD Support - Natural language test cases
- Real-time Execution - Live WebSocket logs
- Comprehensive Reports - Detailed HTML reports with screenshots

### Multi-Framework Support
- Material UI (MUI) v5
- Ant Design v5
- Bootstrap v5
- Chakra UI v2
- Tailwind CSS / Headless UI

---

## Design Patterns and Innovations

### 1. Semantic Element Intelligence (SEI)

Location: backend/app/agent/core/element_intelligence.py

SEI understands elements by their PURPOSE, not just their DOM attributes.

Element DNA captures:
- Identity genes: semantic_type, element_tag, element_type
- Attribute genes: test_id, element_id, aria_label
- Behavioral genes: is_clickable, is_editable, triggers_navigation
- Stability genes: has_dynamic_id, has_framework_classes

Semantic Types (30+ types):
USERNAME_INPUT, PASSWORD_INPUT, LOGIN_BUTTON, SEARCH_INPUT, ADD_TO_CART, CHECKOUT_BUTTON, etc.

Intent Resolution maps natural language to semantic types:
- "enter username" -> USERNAME_INPUT (confidence: 0.9)
- "click login" -> LOGIN_BUTTON (confidence: 0.9)

Predictive Confidence scores selector stability:
- data-testid: 0.98 (very stable)
- id: 0.85 (usually stable)
- class: 0.50 (often unstable)
- xpath position: 0.30 (very unstable)

---

### 2. Five-Tier Decision Pipeline

Location: backend/app/agent/core/selector_service.py

Resolution order:
1. Knowledge Base (0.05ms) - O(1) learned selectors
2. Framework Rules (0.1ms) - Pre-seeded patterns
3. Heuristics + SEI (1-5ms) - Smart analysis
4. AI Decision (500-2000ms) - LLM-powered
5. Fallback (0.5ms) - Generic patterns

Key Insight: AI is a learning accelerator, not a permanent crutch.

---

### 3. Knowledge Index with Bloom Filter

Location: backend/app/agent/knowledge/knowledge_index.py

O(1) lookup using:
- Hash-based indexing for instant lookups
- Bloom filter for quick "not found" checks
- Trie structure for fuzzy matching
- LRU cache for hot elements

Result: 2000x faster than AI-first approaches after learning.

---

### 4. Self-Learning Engine

Location: backend/app/agent/knowledge/learning_engine.py

- Selector Learning with confidence scores
- Pattern Mining from action sequences
- Confidence Decay for stale knowledge
- Cross-Domain Transfer

---

### 5. Intelligent Recovery Handler

Location: backend/app/agent/core/recovery_handler.py

Handles failures automatically:
- Element not found -> Wait + retry with alternatives
- Element not visible -> Scroll into view
- Element intercepted -> Dismiss blocking modal
- Stale element -> Re-query the DOM

---

### 6. Framework Pre-seeding

Location: backend/app/agent/knowledge/framework_selectors.py

Built-in patterns for MUI, Ant Design, Bootstrap, Chakra UI.

---

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+

### Backend Setup

cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
echo "ANTHROPIC_API_KEY=your-key" > .env
cd app && python -m uvicorn main:app --reload --port 8000

### Frontend Setup

cd frontend
npm install
npm run dev

URLs:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Usage

### Semantic Test Writing

OLD WAY (Fragile):
{"action": "click", "selector": "#btn-xyz-123"}

GHOSTQA WAY (Semantic):
{"action": "click", "target": "login button"}

### Gherkin Tests (No Step Definitions Needed!)

Feature: User Authentication
  Scenario: Successful login
    Given I am on the login page
    When I enter "user@example.com" in the email field
    And I click the login button
    Then I should see the dashboard

---

## Project Structure

ghostQA/
+-- backend/
|   +-- app/
|   |   +-- main.py                    # FastAPI entry point
|   |   +-- agent_api.py               # Agent endpoints
|   |   +-- agent/                     # AUTONOMOUS AGENT
|   |       +-- core/
|   |       |   +-- selector_service.py # 5-tier resolution
|   |       |   +-- element_intelligence.py # SEI System
|   |       |   +-- action_executor.py
|   |       |   +-- recovery_handler.py
|   |       +-- knowledge/
|   |       |   +-- knowledge_index.py # O(1) lookup
|   |       |   +-- learning_engine.py
|   |       |   +-- framework_selectors.py
|   |       +-- explorer/
|   |       +-- recorder/
|   +-- data/                          # Knowledge storage
+-- frontend/
|   +-- src/
|   |   +-- pages/
|   |   +-- components/
|   |   +-- hooks/

---

## API Reference

POST /api/agent/run - Execute tests
POST /api/agent/stop - Stop execution
GET /api/agent/metrics/ai-dependency - Get AI metrics
GET /api/projects - List projects
GET /api/reports - List reports
WS /ws/logs - Real-time logs

---

## Performance

### AI Dependency Reduction
- Week 1: 45% (learning)
- Week 4: <5% (autonomous)

### Resolution Speed
- Knowledge Base: 0.05ms
- Heuristics + SEI: 1-5ms
- AI Decision: 500-2000ms

---

## Tech Stack

Backend: FastAPI, Playwright, Pydantic, WebSockets
Frontend: React 18, Vite, Material-UI, Axios
AI: Claude (Anthropic), Ollama (offline)

---

## License

MIT License

---

GhostQA - Tests that think like humans, learn like machines.

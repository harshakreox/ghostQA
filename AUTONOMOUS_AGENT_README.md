# Autonomous Test Agent System

A self-learning, AI-powered test execution framework that executes tests like an experienced human tester. The system learns from every execution to reduce AI dependency over time, achieving true autonomy.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [5-Tier Decision Pipeline](#5-tier-decision-pipeline)
5. [Knowledge Storage](#knowledge-storage)
6. [Training Data Sources](#training-data-sources)
7. [Performance & Efficiency](#performance--efficiency)
8. [Directory Structure](#directory-structure)
9. [Usage Examples](#usage-examples)
10. [API Reference](#api-reference)

---

## Overview

### What This System Does

The Autonomous Test Agent mimics an experienced human tester by:

- **Executing tests autonomously** without manual intervention
- **Learning from every interaction** to improve future executions
- **Reducing AI dependency** over time through learned patterns
- **Recovering from failures** using intelligent strategies
- **Working offline** when AI services are unavailable

### Key Design Principles

1. **AI is a Learning Accelerator, Not a Permanent Crutch**
   - AI helps discover selectors and patterns initially
   - Every successful AI decision is cached for future offline use
   - Over time, the system becomes less dependent on AI

2. **Graceful Degradation**
   - System continues working even when AI is unavailable
   - Falls back through multiple tiers of decision-making
   - Maintains test execution capability at all times

3. **Efficiency First**
   - O(1) lookup performance using hash indexes
   - Bloom filters for quick "not found" checks
   - LRU caching for hot elements
   - No database required - JSON-based storage

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS TEST AGENT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SELECTOR   │  │    ACTION    │  │   RECOVERY   │          │
│  │   SERVICE    │  │   EXECUTOR   │  │   HANDLER    │          │
│  │              │  │              │  │              │          │
│  │ 5-Tier       │  │ Playwright   │  │ Smart        │          │
│  │ Resolution   │  │ Actions      │  │ Recovery     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └────────────┬────┴────────────────┘                   │
│                      │                                          │
│         ┌────────────▼────────────┐                            │
│         │    KNOWLEDGE SYSTEM      │                            │
│         ├─────────────────────────┤                            │
│         │ ┌─────────┐ ┌─────────┐ │                            │
│         │ │Knowledge│ │ Pattern │ │                            │
│         │ │  Index  │ │  Store  │ │                            │
│         │ └────┬────┘ └────┬────┘ │                            │
│         │      │           │      │                            │
│         │ ┌────▼───────────▼────┐ │                            │
│         │ │   Learning Engine   │ │                            │
│         │ └─────────────────────┘ │                            │
│         └─────────────────────────┘                            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    TRAINING SOURCES                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Pre-seed  │  │  Explorer  │  │  Recorder  │                │
│  │ Framework  │  │ Auto-crawl │  │  Human     │                │
│  │ Selectors  │  │ Discovery  │  │ Demos      │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Knowledge Index (`knowledge_index.py`)

The heart of the knowledge system - provides O(1) lookup for learned selectors.

**Features:**
- Hash-based indexing for instant lookups
- Bloom filter for quick "not found" checks
- Trie structure for fuzzy intent matching
- LRU cache for frequently accessed elements
- Confidence scoring and decay

**Key Classes:**
- `KnowledgeIndex` - Main index class
- `ElementKnowledge` - Complete knowledge about an element
- `SelectorInfo` - Information about a single selector
- `BloomFilter` - Probabilistic "not in set" check
- `Trie` - Prefix-based fuzzy matching
- `LRUCache` - Thread-safe LRU cache

### 2. Framework Selectors (`framework_selectors.py`)

Pre-seeded knowledge for common UI frameworks.

**Supported Frameworks:**
- **Material UI (MUI) v5** - 20+ component patterns
- **Ant Design v5** - 30+ component patterns
- **Bootstrap v5** - 20+ component patterns
- **Chakra UI v2** - 20+ component patterns
- **Tailwind CSS** - Headless UI patterns

**Universal Patterns:**
- Common buttons, inputs, forms
- Authentication elements (login, logout)
- Navigation patterns
- Dialog/modal patterns
- Loading indicators

### 3. Pattern Store (`pattern_store.py`)

Stores reusable action sequences (patterns).

**Built-in Patterns:**
- Login flows (email/password, username/password)
- Form submission
- Search functionality
- Modal dismissal
- Cookie banner handling
- Pagination navigation

**Features:**
- Pattern matching by page content
- Intent-based pattern lookup
- Variable substitution
- Success/failure indicators

### 4. Learning Engine (`learning_engine.py`)

Processes test execution results to continuously improve knowledge.

**Learning Sources:**
- Selector success/failure results
- Recovery action effectiveness
- Action sequence patterns
- Cross-domain knowledge transfer

**Features:**
- Batch processing for efficiency
- Confidence decay for stale knowledge
- Pattern mining from action sequences
- Automatic cleanup of low-quality learnings

### 5. Application Explorer (`app_explorer.py`)

Automatically crawls and maps web applications.

**Features:**
- Multiple exploration strategies (breadth-first, depth-first, priority)
- Framework detection
- Element extraction with selector generation
- Sitemap building
- Change detection via content hashing

### 6. Action Recorder (`action_recorder.py`)

Records human interactions for training.

**Captured Information:**
- Action type and timing
- Element snapshots
- Multiple selector strategies
- Page context

**Outputs:**
- Playwright test script generation
- Test step format for execution
- Training data for knowledge base

### 7. Selector Service (`selector_service.py`)

Implements the 5-tier decision pipeline.

**Resolution Order:**
1. Knowledge Base (cached learnings)
2. Framework Rules (pre-seeded patterns)
3. Heuristic Engine (smart guessing)
4. AI Decision (LLM-powered)
5. Graceful Degradation (fallbacks)

### 8. Action Executor (`action_executor.py`)

Executes actions on web pages using Playwright.

**Supported Actions:**
- Click, double-click, right-click
- Type, fill, clear
- Select options
- Check/uncheck
- Hover, scroll
- Navigate, refresh
- Wait for element/time
- Assertions

### 9. Recovery Handler (`recovery_handler.py`)

Handles error recovery during test execution.

**Failure Types:**
- Element not found
- Element not visible
- Element intercepted (modal blocking)
- Stale element
- Timeout
- Cookie banners

**Recovery Actions:**
- Wait and retry
- Scroll into view
- Dismiss modal/dialog
- Wait for loading
- Refresh page
- JavaScript click fallback

### 10. Autonomous Test Agent (`agent.py`)

The main orchestrator that ties everything together.

**Features:**
- Test case execution
- Step-by-step processing
- Automatic recovery
- Metrics tracking
- Screenshot capture

---

## 5-Tier Decision Pipeline

When the agent needs to find an element, it uses a 5-tier decision pipeline:

### Tier 1: Knowledge Base (100% Offline)
```
Lookup Time: ~0.05ms
Source: Previously learned selectors
Confidence: High (validated by past success)
```

The system first checks if it has seen this element before. Uses hash indexing for O(1) lookup.

### Tier 2: Framework Rules (100% Offline)
```
Lookup Time: ~0.1ms
Source: Pre-seeded framework patterns
Confidence: Medium-High
```

If not in knowledge base, checks framework-specific patterns (MUI buttons, Bootstrap forms, etc.).

### Tier 3: Heuristic Engine (100% Offline)
```
Lookup Time: ~1-5ms
Source: Smart pattern matching on current page
Confidence: Medium
```

Analyzes the current page to find elements matching the intent using keyword matching, attribute analysis, and DOM structure.

### Tier 4: AI Decision (Requires AI)
```
Lookup Time: ~500-2000ms
Source: LLM-powered decision
Confidence: Variable
```

Only used when offline methods fail. The AI analyzes the page and suggests selectors. **Critical: Successful AI decisions are cached for future offline use.**

### Tier 5: Graceful Degradation (100% Offline)
```
Lookup Time: ~0.5ms
Source: Generic fallback strategies
Confidence: Low
```

Last resort - uses generic selector patterns based on intent keywords.

---

## Knowledge Storage

All knowledge is stored as JSON files (no database required).

### Directory Structure

```
data/agent_knowledge/
├── selectors/
│   ├── example_com.json        # Per-domain selectors
│   └── another_site.json
├── patterns/
│   ├── builtin_patterns.json   # Built-in patterns
│   └── learned_patterns.json   # Discovered patterns
├── recovery/
│   └── example_com_recovery.json
├── global/
│   ├── login_patterns.json     # Cross-domain patterns
│   └── search_patterns.json
├── metrics/
│   └── selector_evolution.json
├── explorations/
│   └── example_com_20240115_120000.json
└── recordings/
    └── rec_20240115_120000_abc123.json
```

### Selector Storage Format

```json
{
  "domain": "example.com",
  "pages": {
    "/login": {
      "elements": {
        "email_input": {
          "element_key": "email_input",
          "selectors": [
            {
              "value": "[data-testid=\"email\"]",
              "selector_type": "css",
              "confidence": 0.95,
              "successes": 42,
              "failures": 0,
              "last_used": "2024-01-15T12:00:00Z"
            },
            {
              "value": "#email",
              "selector_type": "css",
              "confidence": 0.85,
              "successes": 38,
              "failures": 4,
              "last_used": "2024-01-14T10:00:00Z"
            }
          ],
          "first_seen": "2024-01-01T00:00:00Z",
          "last_verified": "2024-01-15T12:00:00Z"
        }
      }
    }
  }
}
```

---

## Training Data Sources

### 1. Pre-seeded Framework Knowledge
Built-in patterns for MUI, Ant Design, Bootstrap, Chakra UI, and Tailwind. No training required - works immediately.

### 2. Self-Learning (Automatic)
Every successful selector usage is recorded. The system learns from real test executions.

### 3. Application Explorer
```python
explorer = ApplicationExplorer(knowledge_index=ki)
result = await explorer.explore("https://example.com", ExplorationConfig(
    max_pages=50,
    max_depth=3,
    strategy=ExplorationStrategy.PRIORITY
))
# Automatically discovers elements and builds knowledge
```

### 4. Recording Mode
```python
recorder = ActionRecorder(knowledge_index=ki)
recorder.start_session("Login Test", "https://example.com/login")
# Human performs actions, recorder captures everything
recorder.record_click(element_data)
recorder.record_type(element_data, "test@example.com")
session = recorder.end_session()
# Knowledge is automatically extracted and stored
```

### 5. Import/Export
```python
# Export learnings for sharing
learning_engine.export_learnings("backup.json", domain="example.com")

# Import learnings from another system
learning_engine.import_learnings("shared_knowledge.json", merge=True)
```

---

## Performance & Efficiency

### Lookup Benchmarks

| Method | Time | Use Case |
|--------|------|----------|
| LRU Cache Hit | 0.01ms | Repeated element access |
| Bloom Filter Check | 0.02ms | Quick "not found" |
| Knowledge Index Lookup | 0.05ms | Known elements |
| Framework Pattern Match | 0.1ms | Common UI patterns |
| Heuristic Analysis | 1-5ms | Page scanning |
| AI Decision | 500-2000ms | Novel elements |

### Comparison

```
Traditional Approach (AI for every element):
- 10 elements × 1000ms = 10,000ms per test

Our Approach (after learning):
- 8 elements from cache (0.05ms) = 0.4ms
- 2 elements from heuristics (2ms) = 4ms
- Total: ~5ms per test

Improvement: 2000x faster
```

### Memory Efficiency

- Lazy loading: Domain data loaded on demand
- LRU cache: Only hot elements in memory
- Bloom filter: Compact probabilistic structure
- Background saving: Non-blocking persistence

---

## Directory Structure

```
backend/app/agent/
├── __init__.py                 # Main module exports
├── core/
│   ├── __init__.py
│   ├── agent.py               # Main autonomous agent
│   ├── selector_service.py    # 5-tier selector resolution
│   ├── action_executor.py     # Playwright action execution
│   └── recovery_handler.py    # Error recovery strategies
├── knowledge/
│   ├── __init__.py
│   ├── knowledge_index.py     # O(1) knowledge lookup
│   ├── framework_selectors.py # Pre-seeded UI patterns
│   ├── pattern_store.py       # Action patterns
│   └── learning_engine.py     # Learning pipeline
├── explorer/
│   ├── __init__.py
│   ├── app_explorer.py        # Auto-crawl applications
│   ├── page_analyzer.py       # Page analysis & detection
│   └── element_extractor.py   # Element extraction
└── recorder/
    ├── __init__.py
    └── action_recorder.py     # Record human demos
```

---

## Usage Examples

### Basic Test Execution

```python
from playwright.async_api import async_playwright
from app.agent import AutonomousTestAgent, AgentConfig

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Initialize agent
        agent = AutonomousTestAgent(
            page=page,
            config=AgentConfig(
                enable_ai_fallback=True,
                enable_recovery=True,
                capture_screenshots=True
            )
        )

        # Define test case
        test_case = {
            "name": "Login Test",
            "steps": [
                {"action": "navigate", "value": "https://example.com/login"},
                {"action": "type", "target": "email input", "value": "test@example.com"},
                {"action": "type", "target": "password input", "value": "password123"},
                {"action": "click", "target": "login button"},
                {"action": "assert", "target": "dashboard heading", "expected": "Welcome"}
            ]
        }

        # Execute test
        result = await agent.execute_test(test_case)

        print(f"Test: {result.test_name}")
        print(f"Status: {result.status}")
        print(f"Steps: {result.passed_steps}/{result.total_steps} passed")
        print(f"AI calls: {result.ai_calls_made}")
        print(f"KB hits: {result.knowledge_base_hits}")

        await browser.close()
```

### Application Exploration

```python
from app.agent.explorer import ApplicationExplorer, ExplorationConfig

async def explore_app():
    explorer = ApplicationExplorer(
        knowledge_index=knowledge_index,
        learning_engine=learning_engine
    )

    # Set browser callbacks
    explorer.set_browser_callbacks(
        navigate=lambda url: page.goto(url),
        get_html=lambda: page.content(),
        get_dom=lambda: page.evaluate("...")
    )

    # Explore
    result = await explorer.explore(
        "https://example.com",
        ExplorationConfig(
            max_pages=100,
            max_depth=5,
            strategy=ExplorationStrategy.PRIORITY,
            capture_screenshots=True
        )
    )

    print(f"Explored {result.total_pages} pages")
    print(f"Found {result.total_elements} elements")
    print(f"Detected frameworks: {result.detected_frameworks}")
```

### Recording Human Actions

```python
from app.agent.recorder import ActionRecorder

def record_demo():
    recorder = ActionRecorder(
        knowledge_index=knowledge_index,
        learning_engine=learning_engine
    )

    # Start recording
    session_id = recorder.start_session(
        name="Login Flow",
        start_url="https://example.com/login",
        tags=["login", "authentication"]
    )

    # Record actions (called from browser integration)
    recorder.record_click(element_data={
        "tagName": "input",
        "attributes": {"type": "email", "name": "email"}
    })

    recorder.record_type(element_data={...}, value="test@example.com")

    # End recording
    session = recorder.end_session()

    # Generate Playwright script
    script = recorder.generate_playwright_script(session)
    print(script)
```

### Checking AI Dependency

```python
# Get current statistics
stats = agent.get_stats()

print(f"Total actions: {stats['total_actions']}")
print(f"Knowledge base hits: {stats['knowledge_base_hits']}")
print(f"AI calls: {stats['ai_calls']}")
print(f"AI dependency: {stats['ai_dependency_percent']:.1f}%")

# Goal: Get AI dependency below 5%
# This happens naturally as the system learns
```

---

## API Reference

### AutonomousTestAgent

```python
class AutonomousTestAgent:
    def __init__(
        self,
        page=None,                          # Playwright page
        data_dir: str = "data/agent_knowledge",
        config: AgentConfig = None
    )

    async def execute_test(
        self,
        test_case: Dict[str, Any],          # Test definition
        base_url: Optional[str] = None      # Starting URL
    ) -> TestResult

    def set_ai_callback(callback: Callable) # Set AI fallback
    def get_stats() -> Dict[str, Any]       # Get metrics
    def pause() / resume() / stop()         # Control execution
```

### KnowledgeIndex

```python
class KnowledgeIndex:
    def __init__(data_dir: str)

    def lookup(
        domain: str,
        page: str,
        element_key: str
    ) -> Optional[ElementKnowledge]

    def find_by_intent(
        intent: str,
        domain: Optional[str] = None,
        page: Optional[str] = None
    ) -> List[SelectorMatch]

    def add_learning(
        domain: str,
        page: str,
        element_key: str,
        selector: str,
        selector_type: str,
        success: bool,
        ai_assisted: bool = False,
        context: Dict = None
    )
```

### SelectorService

```python
class SelectorService:
    def resolve(
        intent: str,            # What to find
        domain: str,            # Current domain
        page: str,              # Current page
        page_html: str = None,  # Page HTML
        dom_elements: List = None,
        context: Dict = None
    ) -> SelectorResult
```

### ApplicationExplorer

```python
class ApplicationExplorer:
    async def explore(
        start_url: str,
        config: ExplorationConfig = None
    ) -> ExplorationResult

    async def quick_scan(url: str) -> Dict
```

### ActionRecorder

```python
class ActionRecorder:
    def start_session(
        name: str,
        start_url: str,
        description: str = "",
        tags: List[str] = None
    ) -> str  # Returns session ID

    def record_click(element_data: Dict, **kwargs)
    def record_type(element_data: Dict, value: str, **kwargs)
    def record_select(element_data: Dict, value: str, **kwargs)

    def end_session() -> RecordingSession

    def generate_playwright_script(session: RecordingSession) -> str
```

---

## Best Practices

### 1. Start with Exploration
Before running tests, explore the application to build initial knowledge:
```python
await explorer.explore(base_url)
```

### 2. Use Descriptive Intents
Instead of hardcoding selectors, use descriptive targets:
```python
# Good
{"action": "click", "target": "submit login button"}

# Bad
{"action": "click", "target": "#btn-123"}
```

### 3. Monitor AI Dependency
Track how often AI is used and aim to reduce it:
```python
stats = agent.get_stats()
if stats['ai_dependency_percent'] > 10:
    # Consider more exploration or recording
    await explorer.explore(...)
```

### 4. Regular Knowledge Backup
Export knowledge periodically:
```python
learning_engine.export_learnings("backup_2024.json")
```

### 5. Share Cross-Project Knowledge
For similar applications, import existing knowledge:
```python
learning_engine.import_learnings("ecommerce_patterns.json")
```

---

## Troubleshooting

### High AI Dependency
- Run application explorer on all pages
- Record common user flows
- Check if framework selectors are being detected

### Slow Lookups
- Check LRU cache size
- Verify Bloom filter is initialized
- Look for memory issues

### Recovery Failures
- Add custom recovery selectors for your app
- Check for unique modal/dialog patterns
- Verify network stability

---

## Future Enhancements

- [ ] Visual element recognition using screenshots
- [ ] Natural language test case input
- [ ] Distributed knowledge sharing
- [ ] Real-time learning during execution
- [ ] Integration with CI/CD pipelines
- [ ] Custom AI model fine-tuning

---

## License

This autonomous test agent system is part of the GhostQA project.

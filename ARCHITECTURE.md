# GhostQA - System Architecture

## Complete Technical Architecture Diagram

```
+=====================================================================================+
|                              GHOSTQA ARCHITECTURE                                    |
|                    Autonomous Self-Learning Test Automation Framework                |
+=====================================================================================+

+-----------------------------------------------------------------------------------+
|                                  FRONTEND LAYER                                     |
|                              React 18 + Material-UI 5                               |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +------------------+  +------------------+  +------------------+  +--------------+ |
|  |    Dashboard     |  |     Projects     |  |  AI Generator    |  |   Releases   | |
|  |------------------|  |------------------|  |------------------|  |--------------| |
|  | - Stats Cards    |  | - Project List   |  | - BRD Upload     |  | - Release    | |
|  | - Pass Rate      |  | - CRUD Actions   |  | - Gherkin Gen    |  |   Management | |
|  | - Recent Reports |  | - Framework Cfg  |  | - Traditional    |  | - Envs (Dev/ | |
|  | - Charts         |  | - Credentials    |  | - Export (JSON,  |  |   QA/Prod)   | |
|  +------------------+  +------------------+  |   CSV, Feature)  |  | - Iterations | |
|                                              +------------------+  +--------------+ |
|                                                                                     |
|  +------------------+  +------------------+  +------------------+  +--------------+ |
|  |   Test Cases     |  |   Test Runner    |  |     Reports      |  |   Layout     | |
|  |------------------|  |------------------|  |------------------|  |--------------| |
|  | - Action Editor  |  | - Real-time Logs |  | - HTML Reports   |  | - Sidebar    | |
|  | - Selector Types |  | - WebSocket Feed |  | - Screenshots    |  | - Top Nav    | |
|  | - Drag & Drop    |  | - Stop/Pause     |  | - Pass/Fail      |  | - Routing    | |
|  +------------------+  | - Headless Mode  |  | - Step Details   |  +--------------+ |
|                        +------------------+  +------------------+                   |
|                                                                                     |
|  +--------------------------------------------------------------------------------+ |
|  |                         SERVICES & HOOKS                                       | |
|  |  api.js (Axios)  |  useApiData  |  useNotification  |  useContextMenu         | |
|  +--------------------------------------------------------------------------------+ |
|                                        |                                            |
+----------------------------------------|--------------------------------------------+
                                         | HTTP/REST + WebSocket
                                         v
+-----------------------------------------------------------------------------------+
|                                   API LAYER                                         |
|                              FastAPI + Pydantic                                     |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +----------------------------------+  +---------------------------------------+    |
|  |         main.py (1567 LOC)       |  |          agent_api.py                 |    |
|  |----------------------------------|  |---------------------------------------|    |
|  | POST /api/projects               |  | POST /api/agent/run                   |    |
|  | GET  /api/projects               |  |   - Unified test execution            |    |
|  | PUT  /api/projects/{id}          |  |   - Traditional + Gherkin             |    |
|  | DELETE /api/projects/{id}        |  |   - Real-time progress                |    |
|  |                                  |  |                                       |    |
|  | POST /api/projects/{id}/test-cases| | POST /api/agent/stop                  |    |
|  | GET  /api/projects/{id}/test-cases| |   - Graceful execution stop           |    |
|  |                                  |  |                                       |    |
|  | POST /api/run-tests              |  | POST /api/agent/training/explore      |    |
|  | GET  /api/reports                |  |   - Application exploration           |    |
|  | DELETE /api/reports/{id}         |  |                                       |    |
|  |                                  |  | POST /api/agent/training/import       |    |
|  | POST /api/gherkin/generate-*     |  |   - Historical report import          |    |
|  | POST /api/gherkin/execute        |  |                                       |    |
|  | POST /api/gherkin/run-autonomous |  | POST /api/agent/knowledge/export      |    |
|  |                                  |  | POST /api/agent/knowledge/import      |    |
|  | POST /api/traditional/generate-* |  |                                       |    |
|  |                                  |  | GET  /api/agent/metrics/ai-dependency |    |
|  | WS   /ws/logs                    |  | WS   /api/agent/ws/logs               |    |
|  +----------------------------------+  +---------------------------------------+    |
|                                                                                     |
|  +----------------------------------+  +---------------------------------------+    |
|  |          ai_api.py               |  |         release_api.py                |    |
|  |----------------------------------|  |---------------------------------------|    |
|  | POST /api/ai/generate-from-text  |  | POST /api/releases                    |    |
|  | POST /api/ai/generate-from-file  |  | GET  /api/releases                    |    |
|  | GET  /api/ai/check-api-key       |  | PUT  /api/releases/{id}               |    |
|  | GET  /api/ai/ollama/models       |  | POST /api/releases/{id}/environments  |    |
|  +----------------------------------+  | POST /api/releases/{id}/projects      |    |
|                                        | POST /api/releases/{id}/iterations    |    |
|                                        | GET  /api/releases/{id}/metrics       |    |
|                                        +---------------------------------------+    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+=====================================================================================+
|                              CORE ENGINE LAYER                                       |
+=====================================================================================+

+-----------------------------------------------------------------------------------+
|                           AUTONOMOUS AGENT SYSTEM                                   |
|                          agent/ directory (23 files)                                |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +-----------------------------------------------------------------------------+   |
|  |                      UNIFIED TEST EXECUTOR                                   |   |
|  |                     unified_executor.py (350+ LOC)                           |   |
|  |-----------------------------------------------------------------------------|   |
|  |  - Converts Traditional tests to UnifiedTestCase                            |   |
|  |  - Converts Gherkin scenarios to UnifiedTestCase                            |   |
|  |  - Execution modes: AUTONOMOUS | GUIDED | STRICT                            |   |
|  |  - Generates UnifiedExecutionReport with learning stats                     |   |
|  +-----------------------------------------------------------------------------+   |
|                                        |                                            |
|                                        v                                            |
|  +-----------------------------------------------------------------------------+   |
|  |                       AUTONOMOUS TEST AGENT                                  |   |
|  |                        core/agent.py (600+ LOC)                              |   |
|  |-----------------------------------------------------------------------------|   |
|  |  States: IDLE -> RUNNING -> RECOVERING -> COMPLETED/FAILED                  |   |
|  |                                                                              |   |
|  |  Orchestrates:                                                               |   |
|  |    1. Test step execution                                                    |   |
|  |    2. Error recovery                                                         |   |
|  |    3. Screenshot capture                                                     |   |
|  |    4. Result tracking                                                        |   |
|  |    5. Learning updates                                                       |   |
|  +-----------------------------------------------------------------------------+   |
|                                        |                                            |
|           +----------------------------+----------------------------+               |
|           |                            |                            |               |
|           v                            v                            v               |
|  +------------------+      +-------------------+      +-------------------+         |
|  | SELECTOR SERVICE |      | ACTION EXECUTOR   |      | RECOVERY HANDLER  |         |
|  | selector_service |      | action_executor   |      | recovery_handler  |         |
|  |------------------|      |-------------------|      |-------------------|         |
|  |                  |      |                   |      |                   |         |
|  | 5-TIER PIPELINE: |      | Actions:          |      | Recovery Methods: |         |
|  |                  |      |  - click          |      |  - Fuzzy match    |         |
|  | 1. Knowledge Base|      |  - type           |      |  - Coord click    |         |
|  |    (0.05ms)      |      |  - navigate       |      |  - DOM refresh    |         |
|  |    O(1) lookup   |      |  - wait           |      |  - Alt selectors  |         |
|  |                  |      |  - assert_text    |      |  - Scroll reveal  |         |
|  | 2. Framework     |      |  - assert_visible |      |  - Modal dismiss  |         |
|  |    Rules (0.1ms) |      |  - select         |      |                   |         |
|  |                  |      |  - hover          |      | Handles:          |         |
|  | 3. Heuristics    |      |  - check/uncheck  |      |  - Stale refs     |         |
|  |    + SEI (1-5ms) |      |                   |      |  - Not found      |         |
|  |                  |      | Retry logic       |      |  - Not visible    |         |
|  | 4. AI Decision   |      | Timeout handling  |      |  - Intercepted    |         |
|  |    (500-2000ms)  |      | Result capture    |      |  - Layout change  |         |
|  |                  |      +-------------------+      +-------------------+         |
|  | 5. Fallback      |                                                              |
|  |    (0.5ms)       |                                                              |
|  +------------------+                                                              |
|           |                                                                         |
|           v                                                                         |
|  +------------------+      +-------------------+      +-------------------+         |
|  | ELEMENT          |      | SPA HANDLER       |      | DOM MANAGER       |         |
|  | INTELLIGENCE     |      | spa_handler.py    |      | dom_manager.py    |         |
|  | element_intel.py |      |-------------------|      |-------------------|         |
|  |------------------|      |                   |      |                   |         |
|  |                  |      | Detects:          |      | - DOM caching     |         |
|  | Semantic Types:  |      |  - React          |      | - Route detection |         |
|  | - USERNAME_INPUT |      |  - Vue            |      | - Mutation watch  |         |
|  | - PASSWORD_INPUT |      |  - Angular        |      | - Stable hashing  |         |
|  | - LOGIN_BUTTON   |      |                   |      | - Self-healing    |         |
|  | - SEARCH_INPUT   |      | Handles:          |      |   element locate  |         |
|  | - ADD_TO_CART    |      |  - Dynamic content|      |                   |         |
|  | - CHECKOUT_BTN   |      |  - Route changes  |      |                   |         |
|  | - 30+ more...    |      |  - Network idle   |      |                   |         |
|  |                  |      |  - State changes  |      |                   |         |
|  | Element DNA:     |      +-------------------+      +-------------------+         |
|  | - Identity genes |                                                              |
|  | - Attr genes     |                                                              |
|  | - Behavior genes |                                                              |
|  | - Stability genes|                                                              |
|  |                  |                                                              |
|  | Intent Resolver: |                                                              |
|  | "login button"   |                                                              |
|  |  -> LOGIN_BUTTON |                                                              |
|  |  (conf: 0.9)     |                                                              |
|  +------------------+                                                              |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                           KNOWLEDGE SYSTEM                                          |
|                         agent/knowledge/ (4 files)                                  |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +--------------------------------------+  +------------------------------------+   |
|  |         KNOWLEDGE INDEX              |  |        LEARNING ENGINE             |   |
|  |        knowledge_index.py            |  |       learning_engine.py           |   |
|  |--------------------------------------|  |------------------------------------|   |
|  |                                      |  |                                    |   |
|  | Data Structures:                     |  | Learning Events:                   |   |
|  |                                      |  |  - selector_success                |   |
|  | +------------------------------+     |  |  - selector_failure                |   |
|  | |      HASH INDEX              |     |  |  - recovery_success                |   |
|  | |  element_key -> selectors[]  |     |  |  - pattern_discovery               |   |
|  | |  O(1) lookup                 |     |  |  - element_mapping                 |   |
|  | +------------------------------+     |  |                                    |   |
|  |                                      |  | Confidence Evolution:              |   |
|  | +------------------------------+     |  |  success: conf += 0.05             |   |
|  | |      BLOOM FILTER            |     |  |  failure: conf -= 0.10             |   |
|  | |  Quick "not found" check     |     |  |  decay: conf *= 0.995/day          |   |
|  | |  False positive: ~1%         |     |  |                                    |   |
|  | +------------------------------+     |  | Pattern Mining:                    |   |
|  |                                      |  |  - Action sequence detection       |   |
|  | +------------------------------+     |  |  - Cross-app learning              |   |
|  | |      TRIE STRUCTURE          |     |  |  - Framework pattern matching      |   |
|  | |  Fuzzy prefix matching       |     |  |                                    |   |
|  | |  "log" -> login, logout...   |     |  +------------------------------------+   |
|  | +------------------------------+     |                                          |
|  |                                      |  +------------------------------------+   |
|  | +------------------------------+     |  |        PATTERN STORE               |   |
|  | |      LRU CACHE               |     |  |        pattern_store.py            |   |
|  | |  Hot elements (1000 max)     |     |  |------------------------------------|   |
|  | |  Instant access              |     |  |                                    |   |
|  | +------------------------------+     |  | Patterns:                          |   |
|  |                                      |  |  - Common action sequences         |   |
|  | Thread-safe operations               |  |  - Element interaction chains      |   |
|  | Persistence to disk                  |  |  - Framework-specific patterns     |   |
|  +--------------------------------------+  |  - Login flow patterns             |   |
|                                            |  - Form submission patterns        |   |
|  +--------------------------------------+  |  - Navigation patterns             |   |
|  |      FRAMEWORK SELECTORS             |  |                                    |   |
|  |      framework_selectors.py          |  | Confidence scoring                 |   |
|  |--------------------------------------|  | Auto-application                   |   |
|  |                                      |  +------------------------------------+   |
|  | Pre-seeded patterns for:             |                                          |
|  |  - Material UI v5                    |                                          |
|  |  - Ant Design v5                     |                                          |
|  |  - Bootstrap v5                      |                                          |
|  |  - Chakra UI v2                      |                                          |
|  |  - Tailwind CSS                      |                                          |
|  |                                      |                                          |
|  | 100+ keyword synonyms:               |                                          |
|  |  "submit" -> "send", "confirm"...    |                                          |
|  |  "login" -> "sign in", "log in"...   |                                          |
|  +--------------------------------------+                                          |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                           EXPLORER SYSTEM                                           |
|                         agent/explorer/ (3 files)                                   |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +-------------------------+  +------------------------+  +---------------------+  |
|  |     APP EXPLORER        |  |   ELEMENT EXTRACTOR    |  |   PAGE ANALYZER     |  |
|  |    app_explorer.py      |  |  element_extractor.py  |  |  page_analyzer.py   |  |
|  |-------------------------|  |------------------------|  |---------------------|  |
|  |                         |  |                        |  |                     |  |
|  | Strategies:             |  | Extracts:              |  | Detects page type:  |  |
|  |  - breadth_first        |  |  - Buttons             |  |  - login            |  |
|  |  - depth_first          |  |  - Inputs              |  |  - dashboard        |  |
|  |  - priority_based       |  |  - Selects             |  |  - form             |  |
|  |  - random               |  |  - Links               |  |  - list             |  |
|  |                         |  |  - Forms               |  |  - detail           |  |
|  | Outputs:                |  |  - Tables              |  |                     |  |
|  |  - Page map             |  |  - Modals              |  | Detects framework:  |  |
|  |  - Element catalog      |  |                        |  |  - React            |  |
|  |  - Screenshots          |  | Attributes captured:   |  |  - Vue              |  |
|  |  - Framework detection  |  |  - id, class, name     |  |  - Angular          |  |
|  |                         |  |  - data-testid         |  |  - jQuery           |  |
|  |                         |  |  - aria-label          |  |                     |  |
|  |                         |  |  - placeholder         |  | Content analysis    |  |
|  |                         |  |  - text content        |  | Form detection      |  |
|  +-------------------------+  +------------------------+  +---------------------+  |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                           TRAINING SYSTEM                                           |
|                         agent/training/ (2 files)                                   |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +------------------------------------------+  +--------------------------------+  |
|  |          DATA COLLECTOR                   |  |      IMPORT/EXPORT             |  |
|  |         data_collector.py                 |  |      import_export.py          |  |
|  |------------------------------------------|  |--------------------------------|  |
|  |                                          |  |                                |  |
|  | Collection sources:                      |  | Export types:                  |  |
|  |  - Application exploration               |  |  - Full knowledge base         |  |
|  |  - Historical test reports               |  |  - Domain-specific             |  |
|  |  - Manual recording sessions             |  |  - Patterns only               |  |
|  |                                          |  |                                |  |
|  | Collects:                                |  | Import with merge:             |  |
|  |  - Element selectors                     |  |  - Combines knowledge bases    |  |
|  |  - Interaction patterns                  |  |  - Confidence aggregation      |  |
|  |  - Success/failure metrics               |  |  - Cross-project learning      |  |
|  |                                          |  |                                |  |
|  | Batch processing                         |  | Format: JSON                   |  |
|  | Statistics & recommendations             |  |                                |  |
|  +------------------------------------------+  +--------------------------------+  |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                         TEST EXECUTION ENGINES                                      |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +-------------------------+  +---------------------------+  +------------------+  |
|  |     TEST ENGINE         |  | AUTONOMOUS GHERKIN EXEC   |  | GHERKIN EXECUTOR |  |
|  |    test_engine.py       |  | autonomous_gherkin_exec.py|  | gherkin_exec.py  |  |
|  |-------------------------|  |---------------------------|  |------------------|  |
|  |                         |  |                           |  |                  |  |
|  | Traditional tests       |  | AI-powered Gherkin        |  | Step-definition  |  |
|  | Playwright automation   |  | NO step definitions!      |  | based execution  |  |
|  | Self-healing via DOM    |  | AI interprets steps       |  |                  |  |
|  | Screenshot capture      |  | Fuzzy step matching       |  | Tag filtering    |  |
|  | Windows-safe execution  |  | DOM extraction            |  | Result tracking  |  |
|  +-------------------------+  +---------------------------+  +------------------+  |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                            AI GENERATION                                            |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +------------------------------------------+  +--------------------------------+  |
|  |       AI GHERKIN GENERATOR               |  |    AI TEST GENERATOR           |  |
|  |      ai_gherkin_generator.py             |  |   ai_test_generator.py         |  |
|  |------------------------------------------|  |--------------------------------|  |
|  |                                          |  |                                |  |
|  | Generates:                               |  | Generates:                     |  |
|  |  - Gherkin Features                      |  |  - Action-based test cases     |  |
|  |  - Traditional Test Suites               |  |  - UI interaction sequences    |  |
|  |                                          |  |                                |  |
|  | Modes:                                   |  | Features:                      |  |
|  |  - Focused (10-15 scenarios)             |  |  - Framework awareness         |  |
|  |  - End-to-End (15-25 scenarios)          |  |  - UI config integration       |  |
|  |                                          |  |                                |  |
|  | Framework-aware generation               |  |                                |  |
|  +------------------------------------------+  +--------------------------------+  |
|                                         |                                          |
|                                         v                                          |
|  +----------------------------------------------------------------------+         |
|  |                     LLM AUTO-DETECTION                                |         |
|  |----------------------------------------------------------------------|         |
|  |  Priority Order:                                                      |         |
|  |   1. Custom LLM_API_URL (env var)                                    |         |
|  |   2. Ollama (localhost:11434)                                        |         |
|  |   3. Anthropic Claude (ANTHROPIC_API_KEY)                            |         |
|  |   4. OpenAI (OPENAI_API_KEY)                                         |         |
|  +----------------------------------------------------------------------+         |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                              STORAGE LAYER                                          |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|  |       storage.py        |  |    gherkin_storage.py   |  |  release_models.py  | |
|  |-------------------------|  |-------------------------|  |---------------------| |
|  | Projects & Reports      |  | Features & Traditional  |  | Release tracking    | |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|                                                                                     |
|  File Structure:                                                                    |
|  +------------------------------------------------------------------------+        |
|  | data/                                                                   |        |
|  |   +-- projects/              # Project definitions                      |        |
|  |   |     +-- {uuid}.json      # Individual project files                 |        |
|  |   |                                                                     |        |
|  |   +-- reports/               # Test execution reports                   |        |
|  |   |     +-- report_{ts}.json # Timestamped reports                      |        |
|  |   |                                                                     |        |
|  |   +-- features/              # Gherkin features                         |        |
|  |   |     +-- feature_{id}.json                                          |        |
|  |   |                                                                     |        |
|  |   +-- traditional/           # Traditional test suites                  |        |
|  |   |     +-- suite_{id}.json                                            |        |
|  |   |                                                                     |        |
|  |   +-- results/               # Execution results                        |        |
|  |   |     +-- {uuid}.json                                                |        |
|  |   |                                                                     |        |
|  |   +-- agent_knowledge/       # Learning database                        |        |
|  |   |     +-- selectors/       # Learned element selectors               |        |
|  |   |     +-- patterns/        # Action patterns                          |        |
|  |   |     +-- explorations/    # Exploration results                      |        |
|  |   |     +-- training/        # Training batches                         |        |
|  |   |     +-- recovery/        # Recovery strategies                      |        |
|  |   |     +-- screenshots/     # Captured screenshots                     |        |
|  |   |     +-- metrics/         # Learning metrics                         |        |
|  |   |                                                                     |        |
|  |   +-- releases.json          # Release tracking                         |        |
|  +------------------------------------------------------------------------+        |
|                                                                                     |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                           BROWSER AUTOMATION                                        |
+-----------------------------------------------------------------------------------+
|                                                                                     |
|  +----------------------------------------------------------------------+         |
|  |                          PLAYWRIGHT                                   |         |
|  |----------------------------------------------------------------------|         |
|  |  - Chromium browser automation                                        |         |
|  |  - Headless and UI modes                                             |         |
|  |  - Screenshot capture                                                 |         |
|  |  - Network interception                                               |         |
|  |  - Multiple browser contexts                                          |         |
|  |  - Windows-safe async handling                                        |         |
|  +----------------------------------------------------------------------+         |
|                                                                                     |
+-----------------------------------------------------------------------------------+
```

---

## Component Interaction Flows

### 1. Test Generation Flow

```
+---------------+     +------------------+     +-------------+     +---------------+
|   User        |     |   Frontend       |     |   FastAPI   |     |   LLM         |
|   (BRD Doc)   |---->|   AIGenerator    |---->|   ai_api    |---->|   (Claude/    |
|               |     |   Page           |     |   router    |     |    Ollama)    |
+---------------+     +------------------+     +-------------+     +---------------+
                                                      |
                                                      v
                                               +-------------+
                                               | AIGherkin   |
                                               | Generator   |
                                               +-------------+
                                                      |
                      +-------------------------------+-------------------------------+
                      |                                                               |
                      v                                                               v
               +-------------+                                                 +-------------+
               | Gherkin     |                                                 | Traditional |
               | Feature     |                                                 | TestSuite   |
               +-------------+                                                 +-------------+
                      |                                                               |
                      v                                                               v
               +-------------+                                                 +-------------+
               | gherkin_    |                                                 | gherkin_    |
               | storage.py  |                                                 | storage.py  |
               +-------------+                                                 +-------------+
                      |                                                               |
                      v                                                               v
               +-------------+                                                 +-------------+
               | data/       |                                                 | data/       |
               | features/   |                                                 | traditional/|
               +-------------+                                                 +-------------+
```

### 2. Autonomous Test Execution Flow

```
+---------------+     +------------------+     +------------------+     +------------------+
|   Frontend    |     |   agent_api.py   |     |  Unified         |     |  Autonomous      |
|   RunTests    |---->|   /api/agent/run |---->|  Executor        |---->|  TestAgent       |
+---------------+     +------------------+     +------------------+     +------------------+
                                                                               |
                      +--------------------------------------------------------+
                      |
                      v
         +------------------------+
         |   For Each Test Step   |
         +------------------------+
                      |
     +----------------+----------------+----------------+
     |                |                |                |
     v                v                v                v
+----------+    +----------+    +----------+    +----------+
| Selector |    | Action   |    | Recovery |    | Learning |
| Service  |    | Executor |    | Handler  |    | Engine   |
+----------+    +----------+    +----------+    +----------+
     |                |                |                |
     v                v                v                v
+----------+    +----------+    +----------+    +----------+
| 5-Tier   |    | Playwright|   | Self-    |    | Knowledge|
| Pipeline |    | Actions  |    | Healing  |    | Update   |
+----------+    +----------+    +----------+    +----------+
     |
     +---> Knowledge Base (O(1) lookup)
     +---> Framework Rules (pre-seeded)
     +---> Heuristics + SEI (smart analysis)
     +---> AI Decision (LLM fallback)
     +---> Fallback (generic patterns)
```

### 3. Self-Learning Flow

```
+------------------+     +------------------+     +------------------+
|  Test Execution  |     |  Learning        |     |  Knowledge       |
|  Results         |---->|  Engine          |---->|  Index           |
+------------------+     +------------------+     +------------------+
                                |                        |
                                |                        v
                                |                 +------------------+
                                |                 |  Hash Index      |
                                |                 |  Bloom Filter    |
                                |                 |  Trie Structure  |
                                |                 |  LRU Cache       |
                                |                 +------------------+
                                |
                                v
                         +------------------+
                         |  Pattern Store   |
                         +------------------+
                                |
                                v
                         +------------------+
                         |  Next Execution  |
                         |  Uses Learned    |
                         |  Selectors       |
                         +------------------+
                                |
                                v
                         +------------------+
                         |  AI Dependency   |
                         |  Decreases       |
                         |  Over Time       |
                         +------------------+

Week 1: 45% AI dependency (learning)
Week 4: <5% AI dependency (autonomous)
```

### 4. 5-Tier Selector Resolution

```
                    +-------------------+
                    |   Intent/Target   |
                    |   "login button"  |
                    +-------------------+
                            |
                            v
+-----------------------------------------------------------------------+
|                        TIER 1: KNOWLEDGE BASE                          |
|                           (0.05ms - O(1))                              |
|-----------------------------------------------------------------------|
|   Hash lookup: intent_key -> learned_selectors[]                      |
|   If found with confidence > 0.7: RETURN                              |
+-----------------------------------------------------------------------+
                            |
                            | Miss
                            v
+-----------------------------------------------------------------------+
|                      TIER 2: FRAMEWORK RULES                           |
|                           (0.1ms - O(1))                               |
|-----------------------------------------------------------------------|
|   Pre-seeded patterns for MUI, Bootstrap, Ant Design, etc.           |
|   If framework detected and pattern matches: RETURN                   |
+-----------------------------------------------------------------------+
                            |
                            | Miss
                            v
+-----------------------------------------------------------------------+
|                    TIER 3: HEURISTICS + SEI                            |
|                          (1-5ms - O(n))                                |
|-----------------------------------------------------------------------|
|   Semantic Element Intelligence analyzes DOM                          |
|   Element DNA matching, Intent resolution                             |
|   Predictive confidence scoring                                       |
|   If high confidence match: RETURN                                    |
+-----------------------------------------------------------------------+
                            |
                            | Miss
                            v
+-----------------------------------------------------------------------+
|                      TIER 4: AI DECISION                               |
|                       (500-2000ms - LLM)                               |
|-----------------------------------------------------------------------|
|   Send DOM context to LLM                                             |
|   AI analyzes and returns best selector                               |
|   Learn from result for future                                        |
|   If AI provides answer: RETURN                                       |
+-----------------------------------------------------------------------+
                            |
                            | Miss
                            v
+-----------------------------------------------------------------------+
|                        TIER 5: FALLBACK                                |
|                           (0.5ms)                                      |
|-----------------------------------------------------------------------|
|   Generic patterns: text matching, aria-labels                        |
|   Last resort strategies                                              |
|   Log for future learning                                             |
+-----------------------------------------------------------------------+
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | React | 18.2.0 |
| | Material-UI | 5.15.0 |
| | Vite | 5.0.8 |
| | Axios | 1.6.2 |
| | React Router | 6.20.0 |
| | Recharts | 2.10.3 |
| **Backend** | FastAPI | 0.109.0 |
| | Python | 3.8+ |
| | Pydantic | 2.6.0 |
| | Playwright | 1.41.0 |
| **AI/LLM** | Anthropic Claude | claude-sonnet-4-20250514 |
| | Ollama | Any local model |
| | OpenAI | GPT-4/3.5 |
| **Storage** | File-based JSON | - |

---

## Feature Summary

### Test Generation
- AI-powered Gherkin/BDD generation from BRDs
- AI-powered Traditional test case generation
- Framework-aware (React, Vue, Angular, MUI, Bootstrap)
- File upload (PDF, DOCX, TXT)
- Focused vs End-to-End modes

### Test Execution
- Traditional action-based tests
- Gherkin BDD scenarios
- Autonomous AI execution (no step definitions)
- Real-time WebSocket logs
- Stop/pause capability
- Headless and UI modes

### Self-Learning System
- 5-tier selector resolution
- Knowledge base with O(1) lookup
- Pattern discovery and reuse
- Cross-app learning
- AI dependency reduction tracking

### Self-Healing
- Stale reference recovery
- Layout change adaptation
- Fuzzy element matching
- Coordinate-based fallback
- DOM refresh strategies

### Release Management
- Multi-environment (Dev, QA, Staging, Prod)
- Test iterations
- Deployment readiness metrics
- Pass rate aggregation

### Reporting
- HTML reports with charts
- Screenshot galleries
- Step-by-step details
- Execution logs

---

## File Count Summary

| Directory | Files | Lines of Code |
|-----------|-------|---------------|
| backend/app/ | 25 | ~15,000 |
| backend/app/agent/ | 18 | ~8,000 |
| frontend/src/pages/ | 15 | ~5,000 |
| frontend/src/components/ | 8 | ~1,500 |
| **Total** | **66+** | **~30,000** |

---

*GhostQA - Tests that think like humans, learn like machines.*

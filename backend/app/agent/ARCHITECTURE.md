# GhostQA Agent Architecture

## The "Body" Metaphor

The GhostQA agent is designed as an integrated system where different modules work together like parts of a human body:

```
                    +------------------+
                    |      BRAIN       |
                    | (Decision Making)|
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
+--------v--------+ +--------v--------+ +--------v--------+
|    KNOWLEDGE    | |     MEMORY      | |    AI GATEWAY   |
| (Long-term DB)  | | (Specialized)   | | (Token Budget)  |
+-----------------+ +-----------------+ +-----------------+
         |                   |                   |
         +-------------------+-------------------+
                             |
                    +--------v--------+
                    |      CORE       |
                    | (Execution/Body)|
                    +-----------------+
```

## Module Responsibilities

### 1. KNOWLEDGE (`knowledge/`) - Long-term Memory

The persistent storage for learned patterns and selectors:

- **KnowledgeIndex**: Stores selector mappings (intent -> CSS selector)
- **LearningEngine**: Learns from action outcomes, reinforces successful patterns
- **PatternStore**: Stores action patterns and sequences

**Shared by**: Core AND Brain (single source of truth)

### 2. BRAIN (`brain/`) - Decision Making

The neural core that makes intelligent decisions:

- **QABrain**: Main orchestrator, coordinates all cognitive functions
- **DecisionEngine**: Pattern matching without AI, heuristic decisions
- **PageMemory**: Remembers page types, layouts, load times
- **ErrorMemory**: Stores error patterns and recovery strategies
- **WorkflowMemory**: Tracks test flows for prediction
- **AIGateway**: Token budget management, AI call orchestration
- **LearningLoop**: Continuous learning from every action

### 3. CORE (`core/`) - Execution (Muscles)

The execution layer that performs actions:

- **AutonomousTestAgent**: Main orchestrator for test execution
- **SelectorService**: Resolves selectors (5-tier cascade)
- **ActionExecutor**: Executes browser actions
- **RecoveryHandler**: Handles failures and recovery
- **SPAHandler**: Handles single-page applications
- **PreActionChecker**: Human-like pre-action validation
- **HumanLikeTester**: Token-efficient element validation

## How They Work Together

### Selector Resolution Flow

```
1. CORE receives action "click submit button"
       |
2. CORE.SelectorService asks KNOWLEDGE.KnowledgeIndex
       |
3. If not found, asks BRAIN.DecisionEngine (heuristics)
       |
4. If not found, BRAIN.AIGateway (with token budget check)
       |
5. Result stored in KNOWLEDGE for next time
```

### Learning Flow

```
1. CORE executes action
       |
2. Success/Failure reported to BRAIN.LearningLoop
       |
3. LearningLoop updates:
   - KNOWLEDGE.KnowledgeIndex (selector worked/failed)
   - BRAIN.ErrorMemory (if error)
   - BRAIN.WorkflowMemory (action sequence)
```

### Decision Flow

```
1. BRAIN.DecisionEngine receives request
       |
2. Checks KNOWLEDGE.KnowledgeIndex (learned patterns)
       |
3. Applies heuristics (common patterns)
       |
4. Returns decision with confidence score
       |
5. If confidence < threshold, AI fallback via AIGateway
```

## Token Efficiency

The architecture minimizes AI token usage:

1. **Tier 1**: Knowledge Index (FREE) - O(1) lookup
2. **Tier 2**: Heuristics (FREE) - Pattern matching
3. **Tier 3**: Framework rules (FREE) - React, Angular patterns
4. **Tier 4**: AI Fallback (TOKENS) - Only when needed
5. **Tier 5**: AI + Retry (TOKENS) - Last resort

Token budget is enforced by AIGateway:
- Daily limit: 50,000 tokens
- Per-test limit: 2,000 tokens
- Priority system for critical vs optional AI calls

## File Structure

```
backend/app/agent/
|-- core/                  # Execution layer
|   |-- agent.py          # Main orchestrator
|   |-- selector_service.py
|   |-- action_executor.py
|   |-- recovery_handler.py
|   |-- spa_handler.py
|   |-- human_like_tester.py  # Pre-action checks
|
|-- brain/                 # Decision making
|   |-- qa_brain.py       # Main brain orchestrator
|   |-- decision_engine.py
|   |-- memory.py         # Page, Error, Workflow memory
|   |-- learning_loop.py
|   |-- ai_gateway.py
|
|-- knowledge/             # Persistent storage
|   |-- knowledge_index.py
|   |-- learning_engine.py
|   |-- pattern_store.py
|   |-- framework_selectors.py
```

## Integration Points

### Agent Initialization

```python
# In AutonomousTestAgent.__init__:

# 1. Create shared knowledge systems
self.knowledge_index = KnowledgeIndex(data_dir)
self.pattern_store = PatternStore(data_dir)
self.learning_engine = LearningEngine(
    self.knowledge_index,
    self.pattern_store,
    data_dir
)

# 2. Create brain connected to knowledge
self.brain = QABrain(
    config=BrainConfig(...),
    knowledge_index=self.knowledge_index,      # SHARED
    learning_engine=self.learning_engine,      # SHARED
    pattern_store=self.pattern_store           # SHARED
)
```

### Action Execution

```python
# In agent._execute_action():

# 1. Pre-action check (human-like, no AI)
check_result = await self.pre_action_checker.check_before_action(
    page=self.page,
    target_selector=selector,
    action_type=action
)

# 2. If blocked, handle (overlays, loading, errors)
if check_result.readiness != ActionReadiness.READY:
    await self._handle_pre_action_blocker(check_result)

# 3. Execute action
result = await self.action_executor.execute(action, selector, value)

# 4. Learn from outcome
if result.success:
    self.brain.learn_action_success(action, target, selector, execution_time)
else:
    self.brain.learn_action_failure(action, target, selector, error)
```

## Key Design Principles

1. **Single Source of Truth**: Knowledge systems are shared, not duplicated
2. **Token Efficiency**: AI is the last resort, not the first choice
3. **Continuous Learning**: Every action improves the system
4. **Graceful Degradation**: Works without AI, just slower
5. **Human-like Behavior**: Pre-checks mimic what testers do instinctively

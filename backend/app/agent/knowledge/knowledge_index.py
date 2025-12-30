"""
Knowledge Index - High-Performance In-Memory Index

Provides O(1) lookups for element selectors using:
- Hash-based indexes for direct lookups
- Bloom filter for quick "not found" checks
- LRU cache for hot elements
- Trie for fuzzy intent matching
"""

import json
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import lru_cache


@dataclass
class SelectorInfo:
    """Information about a single selector"""
    value: str
    selector_type: str  # test_id, aria, class, text, xpath, etc.
    confidence: float = 0.5
    successes: int = 0
    failures: int = 0
    last_used: Optional[str] = None
    learned_from: str = "unknown"  # ai, recording, exploration, manual


@dataclass
class ElementKnowledge:
    """Complete knowledge about an element"""
    selectors: List[SelectorInfo] = field(default_factory=list)
    best_selector: Optional[str] = None
    element_type: str = "unknown"  # button, input, select, link, etc.
    context: Dict[str, Any] = field(default_factory=dict)  # label, placeholder, etc.
    last_success: Optional[str] = None


@dataclass
class SelectorMatch:
    """A matched selector with metadata"""
    selector: str
    confidence: float
    domain: str
    page: str
    element_key: str
    tier: str  # knowledge_base, framework, heuristic, ai
    selector_type: str = "css"  # css, xpath, text, placeholder, etc.


class LRUCache:
    """Simple LRU cache implementation"""

    def __init__(self, maxsize: int = 1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def put(self, key: str, value: Any):
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.maxsize:
                    self.cache.popitem(last=False)
            self.cache[key] = value

    def invalidate(self, key: str):
        """Remove a key from the cache"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        """Clear all entries from the cache"""
        with self._lock:
            self.cache.clear()


@dataclass
class ScenarioKnowledge:
    """Pre-cached knowledge for a specific scenario"""
    scenario_id: str
    scenario_name: str
    domain: str
    selectors: Dict[str, ElementKnowledge] = field(default_factory=dict)  # element_key -> knowledge
    last_run: str = ""
    success_rate: float = 0.0
    run_count: int = 0

    def get_selector(self, element_key: str) -> Optional[ElementKnowledge]:
        """Get selector for an element key"""
        # Try exact match
        if element_key in self.selectors:
            return self.selectors[element_key]
        # Try variations
        variations = [
            element_key,
            f"{element_key}_field",
            f"form_field_{element_key}",
            element_key.replace(" ", "_"),
        ]
        for var in variations:
            if var in self.selectors:
                return self.selectors[var]
        return None


class BloomFilter:
    """
    Simple Bloom filter for quick "definitely not in set" checks
    Reduces unnecessary lookups for unknown elements
    """

    def __init__(self, capacity: int = 100000, error_rate: float = 0.01):
        import math
        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal size and hash count
        self.size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.size / capacity * math.log(2))

        self.bit_array = [False] * self.size
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> List[int]:
        """Generate multiple hash values for an item"""
        hashes = []
        for i in range(self.hash_count):
            h = hashlib.md5(f"{item}:{i}".encode()).hexdigest()
            hashes.append(int(h, 16) % self.size)
        return hashes

    def add(self, item: str):
        """Add an item to the filter"""
        with self._lock:
            for h in self._hashes(item):
                self.bit_array[h] = True

    def might_contain(self, item: str) -> bool:
        """Check if item might be in the set (false positives possible)"""
        return all(self.bit_array[h] for h in self._hashes(item))


class Trie:
    """
    Trie for fast prefix and fuzzy matching of intents
    Enables finding similar intents like "login button" matching "login_button"
    """

    def __init__(self):
        self.root = {}
        self._end = "_END_"
        self._lock = threading.Lock()

    def insert(self, word: str):
        """Insert a word into the trie"""
        with self._lock:
            # Normalize: lowercase, replace separators with spaces
            normalized = self._normalize(word)
            node = self.root
            for char in normalized:
                if char not in node:
                    node[char] = {}
                node = node[char]
            node[self._end] = word  # Store original

    def _normalize(self, text: str) -> str:
        """Normalize text for matching"""
        return text.lower().replace("_", " ").replace("-", " ").strip()

    def find_exact(self, word: str) -> Optional[str]:
        """Find exact match"""
        normalized = self._normalize(word)
        node = self.root
        for char in normalized:
            if char not in node:
                return None
            node = node[char]
        return node.get(self._end)

    def find_prefix(self, prefix: str, limit: int = 10) -> List[str]:
        """Find all words with given prefix"""
        normalized = self._normalize(prefix)
        node = self.root

        for char in normalized:
            if char not in node:
                return []
            node = node[char]

        # Collect all words under this node
        results = []
        self._collect(node, results, limit)
        return results

    def _collect(self, node: dict, results: List[str], limit: int):
        """Collect all words under a node"""
        if len(results) >= limit:
            return

        if self._end in node:
            results.append(node[self._end])

        for char, child in node.items():
            if char != self._end:
                self._collect(child, results, limit)

    def find_similar(self, query: str, limit: int = 5) -> List[str]:
        """Find similar words using prefix matching"""
        normalized = self._normalize(query)

        # Try progressively shorter prefixes
        for i in range(len(normalized), 0, -1):
            prefix = normalized[:i]
            matches = self.find_prefix(prefix, limit)
            if matches:
                return matches

        return []


class KnowledgeIndex:
    """
    High-performance in-memory index for element knowledge

    Features:
    - O(1) lookups for known elements
    - Bloom filter for quick "not found" checks
    - LRU cache for hot elements
    - Trie for fuzzy intent matching
    - Thread-safe operations
    - Automatic persistence
    """

    def __init__(self, knowledge_dir: str = "data/agent_knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # === PRIMARY INDEXES ===
        # Domain → Page → Element → Knowledge
        self.by_location: Dict[str, Dict[str, Dict[str, ElementKnowledge]]] = {}

        # Intent hash → List of matches
        self.by_intent_hash: Dict[int, List[SelectorMatch]] = {}

        # Selector string → Metadata
        self.by_selector: Dict[str, Dict[str, Any]] = {}

        # === FAST LOOKUP STRUCTURES ===
        self.bloom_filter = BloomFilter(capacity=100000)
        self.intent_trie = Trie()
        self.hot_cache = LRUCache(maxsize=1000)

        # === STATISTICS ===
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "bloom_filter_saves": 0,
            "total_lookups": 0,
            "total_elements": 0,
            "total_domains": 0
        }

        # === PERSISTENCE ===
        self._pending_saves: List[tuple] = []
        self._save_lock = threading.Lock()
        self._loaded_domains: Set[str] = set()

        # Start background saver
        self._start_background_saver()

        # Load existing knowledge base
        self.load_all()

    def _start_background_saver(self):
        """Start background thread for periodic persistence"""
        def save_loop():
            while True:
                time.sleep(30)  # Save every 30 seconds
                self._persist_pending()

        thread = threading.Thread(target=save_loop, daemon=True)
        thread.start()

    def load_all(self):
        """Load entire knowledge base into memory"""
        start = time.time()

        selectors_dir = self.knowledge_dir / "selectors"
        if not selectors_dir.exists():
            print("[KB] No existing knowledge base found, starting fresh")
            return

        for domain_dir in selectors_dir.iterdir():
            if domain_dir.is_dir():
                self._load_domain(domain_dir.name)

        elapsed = time.time() - start
        print(f"[KB] Knowledge index loaded in {elapsed:.3f}s")
        print(f"   Domains: {self.stats['total_domains']}")
        print(f"   Elements: {self.stats['total_elements']}")

        # Also load exploration results
        self._import_explorations()

    def _import_explorations(self):
        """Import exploration results into the knowledge base"""
        explorations_dir = self.knowledge_dir / "explorations"
        if not explorations_dir.exists():
            return

        imported_count = 0
        for exp_file in explorations_dir.glob("*.json"):
            try:
                data = json.loads(exp_file.read_text(encoding='utf-8'))
                domain = data.get("domain", "")
                if not domain:
                    continue

                for page in data.get("pages", []):
                    page_path = page.get("url", "/")
                    # Extract just the path from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(page_path)
                    page_path = parsed.path or "/"

                    for element in page.get("elements", []):
                        elem_key = element.get("key", "")
                        if not elem_key:
                            continue

                        for selector_info in element.get("selectors", []):
                            selector = selector_info.get("selector", "")
                            sel_type = selector_info.get("type", "css")
                            confidence = selector_info.get("confidence", 0.7)

                            if selector and confidence >= 0.5:
                                # Add to KB if not already present with higher confidence
                                existing = self.lookup(domain, page_path, elem_key)
                                should_add = True
                                if existing and existing.selectors:
                                    # Check if we already have this selector
                                    for s in existing.selectors:
                                        if s.value == selector:
                                            should_add = False
                                            break
                                        # Don't overwrite if existing has higher confidence
                                        if s.confidence > confidence:
                                            should_add = False

                                if should_add:
                                    self.add_learning(
                                        domain=domain,
                                        page=page_path,
                                        element_key=elem_key,
                                        selector=selector,
                                        selector_type=sel_type,
                                        success=True,  # Exploration finds working selectors
                                        element_type=element.get("type", "unknown"),
                                        context={"source": "exploration"}
                                    )
                                    imported_count += 1
            except Exception as e:
                print(f"[KB] Error importing {exp_file.name}: {e}")

        if imported_count > 0:
            print(f"[KB] Imported {imported_count} selectors from explorations")

    def _load_domain(self, domain: str):
        """Load knowledge for a specific domain"""
        if domain in self._loaded_domains:
            return

        cache_file = self.knowledge_dir / "selectors" / domain / "element_cache.json"

        if not cache_file.exists():
            return

        try:
            data = json.loads(cache_file.read_text(encoding='utf-8'))

            if domain not in self.by_location:
                self.by_location[domain] = {}

            for page_path, page_data in data.get("pages", {}).items():
                if page_path not in self.by_location[domain]:
                    self.by_location[domain][page_path] = {}

                for elem_key, elem_data in page_data.get("elements", {}).items():
                    # Build ElementKnowledge
                    selectors = [
                        SelectorInfo(
                            value=s.get("value", ""),
                            selector_type=s.get("type", "unknown"),
                            confidence=s.get("confidence", 0.5),
                            successes=s.get("successes", 0),
                            failures=s.get("failures", 0),
                            last_used=s.get("last_used"),
                            learned_from=s.get("learned_from", "unknown")
                        )
                        for s in elem_data.get("selectors", [])
                    ]

                    knowledge = ElementKnowledge(
                        selectors=selectors,
                        best_selector=elem_data.get("best_selector"),
                        element_type=elem_data.get("element_type", "unknown"),
                        context=elem_data.get("context", {}),
                        last_success=elem_data.get("last_success")
                    )

                    self.by_location[domain][page_path][elem_key] = knowledge

                    # Update indexes
                    cache_key = f"{domain}:{page_path}:{elem_key}"
                    self.bloom_filter.add(cache_key)
                    self.intent_trie.insert(elem_key)

                    # Index by intent hash
                    intent_hash = self._hash_intent(elem_key)
                    if intent_hash not in self.by_intent_hash:
                        self.by_intent_hash[intent_hash] = []

                    if knowledge.best_selector:
                        self.by_intent_hash[intent_hash].append(
                            SelectorMatch(
                                selector=knowledge.best_selector,
                                selector_type=selectors[0].selector_type if selectors else "css",
                                confidence=selectors[0].confidence if selectors else 0.5,
                                domain=domain,
                                page=page_path,
                                element_key=elem_key,
                                tier="knowledge_base"
                            )
                        )

                    # Index by selector
                    for sel in selectors:
                        self.by_selector[sel.value] = {
                            "domain": domain,
                            "page": page_path,
                            "element": elem_key,
                            "confidence": sel.confidence
                        }

                    self.stats["total_elements"] += 1

            self._loaded_domains.add(domain)
            self.stats["total_domains"] = len(self._loaded_domains)

        except Exception as e:
            print(f"[WARN] Error loading domain {domain}: {e}")

    @lru_cache(maxsize=10000)
    def _hash_intent(self, intent: str) -> int:
        """Fast hash for intent strings"""
        normalized = " ".join(intent.lower().split())
        return hash(normalized)

    def lookup(
        self,
        domain: str,
        page: str,
        element_key: str
    ) -> Optional[ElementKnowledge]:
        """
        O(1) lookup for known element

        Returns ElementKnowledge if found, None otherwise
        """
        self.stats["total_lookups"] += 1
        cache_key = f"{domain}:{page}:{element_key}"

        # Step 1: Check hot cache (fastest)
        cached = self.hot_cache.get(cache_key)
        if cached is not None:
            self.stats["cache_hits"] += 1
            return cached

        # Step 2: Bloom filter check (quick rejection)
        if not self.bloom_filter.might_contain(cache_key):
            self.stats["bloom_filter_saves"] += 1
            return None

        # Step 3: Load domain if not loaded
        if domain not in self._loaded_domains:
            self._load_domain(domain)

        # Step 4: Direct lookup
        self.stats["cache_misses"] += 1

        result = self.by_location.get(domain, {}).get(page, {}).get(element_key)

        if result:
            self.hot_cache.put(cache_key, result)

        return result

    def find_by_intent(
        self,
        intent: str,
        domain: Optional[str] = None,
        page: Optional[str] = None,
        limit: int = 5
    ) -> List[SelectorMatch]:
        """
        Find selectors matching an intent like "click login button"

        Uses hash lookup first, falls back to trie for fuzzy matching
        """
        results = []

        # Try exact hash match first (O(1))
        intent_hash = self._hash_intent(intent)
        if intent_hash in self.by_intent_hash:
            matches = self.by_intent_hash[intent_hash]

            # Filter by domain/page if provided
            for match in matches:
                if domain and match.domain != domain:
                    continue
                if page and match.page != page:
                    continue
                results.append(match)
                if len(results) >= limit:
                    break

        # If no exact match, try fuzzy matching with trie
        if not results:
            similar_intents = self.intent_trie.find_similar(intent, limit=10)

            for similar in similar_intents:
                similar_hash = self._hash_intent(similar)
                if similar_hash in self.by_intent_hash:
                    for match in self.by_intent_hash[similar_hash]:
                        if domain and match.domain != domain:
                            continue
                        if page and match.page != page:
                            continue

                        # Reduce confidence for fuzzy matches
                        fuzzy_match = SelectorMatch(
                            selector=match.selector,
                            selector_type=match.selector_type,
                            confidence=match.confidence * 0.8,
                            domain=match.domain,
                            page=match.page,
                            element_key=match.element_key,
                            tier="knowledge_base_fuzzy"
                        )
                        results.append(fuzzy_match)

                        if len(results) >= limit:
                            break

        return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]

    def add_learning(
        self,
        domain: str,
        page: str,
        element_key: str,
        selector: str,
        selector_type: str = "ai_learned",
        success: bool = True,
        element_type: str = "unknown",
        context: Optional[Dict] = None,
        ai_assisted: bool = False
    ):
        """
        Add new learning to the knowledge base

        This is called whenever a selector successfully (or unsuccessfully) finds an element.

        Args:
            ai_assisted: Whether AI was used to discover this selector
        """
        # Ensure domain structure exists
        if domain not in self.by_location:
            self.by_location[domain] = {}
        if page not in self.by_location[domain]:
            self.by_location[domain][page] = {}

        # Get or create element knowledge
        if element_key not in self.by_location[domain][page]:
            self.by_location[domain][page][element_key] = ElementKnowledge(
                selectors=[],
                element_type=element_type,
                context=context or {}
            )

        knowledge = self.by_location[domain][page][element_key]

        # Find or create selector info
        existing_selector = None
        for sel in knowledge.selectors:
            if sel.value == selector:
                existing_selector = sel
                break

        if existing_selector:
            # Update existing
            if success:
                existing_selector.successes += 1
            else:
                existing_selector.failures += 1

            total = existing_selector.successes + existing_selector.failures
            existing_selector.confidence = existing_selector.successes / total if total > 0 else 0.5
            existing_selector.last_used = datetime.now().isoformat()
        else:
            # Add new selector
            knowledge.selectors.append(SelectorInfo(
                value=selector,
                selector_type=selector_type,
                confidence=0.8 if success else 0.2,
                successes=1 if success else 0,
                failures=0 if success else 1,
                last_used=datetime.now().isoformat(),
                learned_from="execution"
            ))

        # Update best selector
        if knowledge.selectors:
            knowledge.selectors.sort(key=lambda x: x.confidence, reverse=True)
            knowledge.best_selector = knowledge.selectors[0].value

            if success:
                knowledge.last_success = datetime.now().isoformat()

        # Update indexes
        cache_key = f"{domain}:{page}:{element_key}"
        self.bloom_filter.add(cache_key)
        self.intent_trie.insert(element_key)
        self.hot_cache.invalidate(cache_key)

        # Update intent hash index
        intent_hash = self._hash_intent(element_key)
        if intent_hash not in self.by_intent_hash:
            self.by_intent_hash[intent_hash] = []

        # Update or add match
        existing_match = None
        for match in self.by_intent_hash[intent_hash]:
            if match.domain == domain and match.page == page and match.element_key == element_key:
                existing_match = match
                break

        if existing_match:
            existing_match.selector = knowledge.best_selector
            existing_match.confidence = knowledge.selectors[0].confidence if knowledge.selectors else 0.5
        else:
            self.by_intent_hash[intent_hash].append(
                SelectorMatch(
                    selector=knowledge.best_selector,
                    selector_type=knowledge.selectors[0].selector_type if knowledge.selectors else "css",
                    confidence=knowledge.selectors[0].confidence if knowledge.selectors else 0.5,
                    domain=domain,
                    page=page,
                    element_key=element_key,
                    tier="knowledge_base"
                )
            )

        # Queue for persistence
        with self._save_lock:
            self._pending_saves.append((domain, page, element_key))

        # Update stats
        if cache_key not in [f"{d}:{p}:{e}" for d, pages in self.by_location.items() for p, elems in pages.items() for e in elems]:
            self.stats["total_elements"] += 1

        print(f"[KB] Learned: '{element_key}' -> '{selector}' (confidence: {knowledge.selectors[0].confidence:.2f})")

    def _persist_pending(self):
        """Persist pending changes to JSON files"""
        with self._save_lock:
            if not self._pending_saves:
                return

            # Group by domain
            by_domain: Dict[str, Set[tuple]] = {}
            for domain, page, element in self._pending_saves:
                if domain not in by_domain:
                    by_domain[domain] = set()
                by_domain[domain].add((page, element))

            self._pending_saves.clear()

        # Save each domain
        for domain, elements in by_domain.items():
            self._save_domain(domain)

    def _save_domain(self, domain: str):
        """Save all knowledge for a domain to JSON"""
        domain_dir = self.knowledge_dir / "selectors" / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        cache_file = domain_dir / "element_cache.json"

        # Build JSON structure
        data = {
            "version": "1.0",
            "domain": domain,
            "last_updated": datetime.now().isoformat(),
            "pages": {}
        }

        if domain in self.by_location:
            for page_path, elements in self.by_location[domain].items():
                data["pages"][page_path] = {"elements": {}}

                for elem_key, knowledge in elements.items():
                    data["pages"][page_path]["elements"][elem_key] = {
                        "selectors": [
                            {
                                "value": s.value,
                                "type": s.selector_type,
                                "confidence": s.confidence,
                                "successes": s.successes,
                                "failures": s.failures,
                                "last_used": s.last_used,
                                "learned_from": s.learned_from
                            }
                            for s in knowledge.selectors
                        ],
                        "best_selector": knowledge.best_selector,
                        "element_type": knowledge.element_type,
                        "context": knowledge.context,
                        "last_success": knowledge.last_success
                    }

        # Write atomically
        temp_file = cache_file.with_suffix('.tmp')
        temp_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        temp_file.replace(cache_file)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self.stats["total_lookups"]
        if total > 0:
            cache_rate = self.stats["cache_hits"] / total * 100
            bloom_rate = self.stats["bloom_filter_saves"] / total * 100
        else:
            cache_rate = 0
            bloom_rate = 0

        return {
            **self.stats,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "bloom_filter_save_rate": f"{bloom_rate:.1f}%"
        }

    def force_save(self):
        """Force immediate persistence of all pending changes"""
        # Save all loaded domains
        for domain in self._loaded_domains:
            self._save_domain(domain)
        print("[KB] Knowledge base saved to disk")

    # ==================== Scenario-Level Caching ====================

    def get_scenario_cache(self, scenario_id: str, scenario_name: str, domain: str) -> Optional[ScenarioKnowledge]:
        """
        Load cached knowledge for a specific scenario.
        Returns all known selectors for this scenario in one O(1) lookup.
        """
        cache_file = self.knowledge_dir / "scenario_cache" / f"{self._safe_filename(scenario_id)}.json"

        if not cache_file.exists():
            print(f"[KB-SCENARIO] No cache found for scenario: {scenario_name}", flush=True)
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Convert to ScenarioKnowledge
            selectors = {}
            for key, sel_data in data.get("selectors", {}).items():
                selector_infos = [
                    SelectorInfo(
                        value=s.get("value", ""),
                        selector_type=s.get("selector_type", "css"),
                        confidence=s.get("confidence", 0.5),
                        successes=s.get("successes", 0),
                        failures=s.get("failures", 0),
                        last_used=s.get("last_used"),
                        learned_from=s.get("learned_from", "scenario_cache")
                    )
                    for s in sel_data.get("selectors", [])
                ]
                selectors[key] = ElementKnowledge(
                    selectors=selector_infos,
                    best_selector=sel_data.get("best_selector"),
                    element_type=sel_data.get("element_type", "unknown")
                )

            scenario_kb = ScenarioKnowledge(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                domain=domain,
                selectors=selectors,
                last_run=data.get("last_run", ""),
                success_rate=data.get("success_rate", 0.0),
                run_count=data.get("run_count", 0)
            )

            print(f"[KB-SCENARIO] Loaded cache for '{scenario_name}': {len(selectors)} selectors", flush=True)
            return scenario_kb

        except Exception as e:
            print(f"[KB-SCENARIO] Error loading scenario cache: {e}", flush=True)
            return None

    def save_scenario_cache(
        self,
        scenario_id: str,
        scenario_name: str,
        domain: str,
        used_selectors: Dict[str, Dict[str, Any]],
        success: bool
    ):
        """
        Save learned selectors for a scenario to cache.
        Next time this scenario runs, we'll load these directly.
        """
        cache_dir = self.knowledge_dir / "scenario_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{self._safe_filename(scenario_id)}.json"

        # Load existing or create new
        existing = {}
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    existing = json.load(f)
            except:
                existing = {}

        # Merge new selectors with existing
        existing_selectors = existing.get("selectors", {})
        for key, sel_info in used_selectors.items():
            if key not in existing_selectors:
                existing_selectors[key] = {
                    "selectors": [],
                    "best_selector": sel_info.get("selector"),
                    "element_type": sel_info.get("element_type", "unknown")
                }

            # Add or update selector
            selector_value = sel_info.get("selector")
            found = False
            for s in existing_selectors[key].get("selectors", []):
                if s.get("value") == selector_value:
                    s["successes"] = s.get("successes", 0) + (1 if success else 0)
                    s["failures"] = s.get("failures", 0) + (0 if success else 1)
                    s["last_used"] = datetime.now().isoformat()
                    # Recalculate confidence
                    total = s["successes"] + s["failures"]
                    s["confidence"] = s["successes"] / total if total > 0 else 0.5
                    found = True
                    break

            if not found:
                existing_selectors[key]["selectors"].append({
                    "value": selector_value,
                    "selector_type": sel_info.get("selector_type", "css"),
                    "confidence": 0.8 if success else 0.2,
                    "successes": 1 if success else 0,
                    "failures": 0 if success else 1,
                    "last_used": datetime.now().isoformat(),
                    "learned_from": "scenario_execution"
                })

            # Update best selector
            if existing_selectors[key]["selectors"]:
                best = max(existing_selectors[key]["selectors"], key=lambda x: x.get("confidence", 0))
                existing_selectors[key]["best_selector"] = best.get("value")

        # Update metadata
        run_count = existing.get("run_count", 0) + 1
        old_success_rate = existing.get("success_rate", 0.0)
        new_success_rate = ((old_success_rate * (run_count - 1)) + (1.0 if success else 0.0)) / run_count

        cache_data = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "domain": domain,
            "selectors": existing_selectors,
            "last_run": datetime.now().isoformat(),
            "success_rate": new_success_rate,
            "run_count": run_count
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        print(f"[KB-SCENARIO] Saved cache for '{scenario_name}': {len(existing_selectors)} selectors, run #{run_count}", flush=True)

    def _safe_filename(self, name: str) -> str:
        """Convert a name to a safe filename"""
        import re
        safe = re.sub(r'[^\w\-]', '_', name)
        return safe[:100]  # Limit length

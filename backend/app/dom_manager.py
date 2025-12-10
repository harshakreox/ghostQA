"""
dom_manager.py
--------------
Enhanced DOM Manager with robust error handling, diagnostics, and SPA support.

Key Features:
- Intelligent DOM caching and refresh
- SPA route-change detection via history API hooks
- MutationObserver-based structural change detection
- Stable DOM hashing (ignores ephemeral changes)
- Comprehensive diagnostics and logging
- Thread-safe operations
- Auto-initialization and validation

Improvements over original:
- Better initialization with validation
- Enhanced error handling with fallbacks
- Detailed diagnostic logging
- Automatic SPA watcher setup
- DOM validation after refresh
- Retry logic with backoff
"""

import hashlib
import json
import os
import re
import time
import threading
from urllib.parse import urlsplit, urlunsplit
from typing import Optional, Dict, Any, Callable


# ============================================================
# Utility Functions
# ============================================================

def load_dom_library(path="dom_library.json"):
    """Load existing DOM JSON (returns {} if missing)."""
    try:
        if not os.path.exists(path):
            print(f"[INFO]  DOM library not found at {path}, will create on first refresh.")
            return {}
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Validate the loaded data has expected structure
        if not isinstance(data, dict):
            print(f"[WARN] DOM library has invalid format, starting fresh.")
            return {}
            
        print(f"[OK] Loaded existing DOM library from {path}")
        return data
        
    except FileNotFoundError:
        print(f"[INFO]  DOM library not found at {path}, starting fresh.")
        return {}
    except json.JSONDecodeError as e:
        print(f"[WARN] DOM library is corrupted ({e}), starting fresh.")
        return {}
    except Exception as e:
        print(f"[WARN] Failed to load DOM library: {e}")
        return {}


def write_safe_read(path, timeout=5.0):
    """Attempt to read a JSON file safely, retrying briefly for async writes."""
    deadline = time.time() + timeout
    attempts = 0
    while time.time() < deadline:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            attempts += 1
            if attempts > 5:
                return None
            time.sleep(0.2)
        except Exception:
            time.sleep(0.1)
    return None


def stable_dom_hash(html: str) -> str:
    """
    Compute a stable hash of the DOM that ignores ephemeral attributes
    like input values, React data IDs, timestamps, etc.
    """
    try:
        # Strip user-entered or transient data
        html = re.sub(r'value="[^"]*"', '', html)
        html = re.sub(r'data-[a-zA-Z0-9_-]+="[^"]*"', '', html)
        html = re.sub(r'id="react-[-\w]+"', '', html)
        html = re.sub(r'aria-[a-zA-Z-]+="[^"]*"', '', html)
        html = re.sub(r'\s+', ' ', html)
        return hashlib.md5(html.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def validate_dom_structure(dom_data: Dict[str, Any]) -> bool:
    """
    Validate that DOM data has the expected structure and is not empty.
    Returns True if valid, False otherwise.
    """
    if not dom_data or not isinstance(dom_data, dict):
        return False
    
    # Check for at least one expected key with data
    expected_keys = ["forms", "buttons_and_links", "images", "visible_elements", "visible_text_sample"]
    has_data = False
    
    for key in expected_keys:
        if key in dom_data:
            value = dom_data[key]
            if isinstance(value, list) and len(value) > 0:
                has_data = True
                break
            elif isinstance(value, dict) and len(value) > 0:
                has_data = True
                break
    
    return has_data


def refresh_dom(page, dom_path="dom_library.json", max_retries=2):
    """
    Perform an actual DOM inspection refresh via runtime inspector.
    Returns updated DOM data (not the full library) or None on failure.
    """
    print(" Refreshing DOM library from current page...")
    
    for attempt in range(max_retries):
        try:
            # Import here to avoid circular dependency
            from dom_inspect import inspect_page_runtime
            
            api_key = os.getenv("ANTHROPIC_API_KEY", None)
            
            # Call the DOM inspector
            inspect_page_runtime(
                page,
                goals="Runtime inspection from dom_manager",
                api_key=api_key,
                library_path=dom_path,
            )
            
            # Wait a bit for the file to be written
            time.sleep(0.5)
            
            # Try to read the updated library
            updated_library = write_safe_read(dom_path, timeout=5.0)
            
            if not updated_library:
                print(f"[WARN] DOM refresh attempt {attempt + 1}: Could not read library file.")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                    time.sleep(1)
                continue
            
            # Extract the actual DOM data from the library
            # Library format: {"url#hash": {DOM_DATA}}
            # We need to get the DOM_DATA for the current URL
            from urllib.parse import urlsplit, urlunsplit
            
            current_url = page.url
            # Normalize current URL (keep fragment for SPA routing)
            try:
                p = urlsplit(current_url)
                current_url_normalized = urlunsplit((p.scheme, p.netloc, p.path, "", p.fragment))
            except:
                current_url_normalized = current_url
            
            print(f" Searching for DOM data matching: {current_url_normalized}")
            
            # Find the entry for current URL using EXACT match
            dom_data = None
            best_match_key = None
            
            for key, value in updated_library.items():
                # Extract URL from key (remove the content hash at the end)
                # Key format: "https://site.com/#page#12345678"
                # We want:     "https://site.com/#page"
                if '#' in key:
                    key_url = key.rsplit('#', 1)[0]  # Remove last hash (content ID)
                else:
                    key_url = key
                
                # Normalize key URL
                try:
                    p = urlsplit(key_url)
                    key_url_normalized = urlunsplit((p.scheme, p.netloc, p.path, "", p.fragment))
                except:
                    key_url_normalized = key_url
                
                print(f"    Comparing: {key_url_normalized}")
                
                # Exact match
                if current_url_normalized == key_url_normalized:
                    dom_data = value
                    best_match_key = key
                    print(f"   [OK] EXACT MATCH: {key}")
                    break
            
            # If not found, just get the last entry (most recent)
            if not dom_data and updated_library:
                last_key = list(updated_library.keys())[-1]
                dom_data = updated_library[last_key]
                print(f"   [WARN] No exact match, using most recent: {last_key}")
            
            # Now validate the actual DOM data (not the library wrapper)
            if dom_data and validate_dom_structure(dom_data):
                print("[OK] DOM library successfully refreshed and validated.")
                return dom_data  # Return the DOM data, not the full library
            else:
                print(f"[WARN] DOM refresh attempt {attempt + 1} produced invalid/empty data.")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                    time.sleep(1)
                    
        except Exception as e:
            print(f"[WARN] DOM refresh attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("   Retrying...")
                time.sleep(1)
    
    print("[ERR] All DOM refresh attempts failed.")
    return None


# ============================================================
# DOM Manager Class
# ============================================================

class DOMManager:
    """
    Manages cached DOM library with intelligent SPA/MPA refresh behavior.
    
    Features:
    - Automatic initialization and validation
    - SPA/MPA detection and handling
    - Intelligent refresh with debouncing
    - Comprehensive diagnostics
    - Thread-safe operations
    """

    def __init__(
        self, 
        page=None, 
        dom_path="dom_library.json", 
        debounce_interval=1.0,
        auto_init=True
    ):
        """
        Initialize DOM Manager.
        
        Args:
            page: Playwright page object
            dom_path: Path to DOM library JSON file
            debounce_interval: Minimum seconds between refreshes
            auto_init: Automatically initialize SPA watchers
        """
        self.dom_path = dom_path
        self.page = page
        
        # Load the full library
        self.dom_library = load_dom_library(dom_path)
        
        # Extract the most recent DOM data from library
        self.dom_data = self._extract_latest_dom_data(self.dom_library)
        
        # Tracking state
        self.last_dom_hash = None
        self.last_url = None
        self.last_url_normalized = None
        self._last_refresh_ts = 0.0
        self._refresh_in_progress = False
        self._initialized = False

        # Threading synchronization
        self._refresh_lock = threading.Lock()
        self._refresh_event = threading.Event()
        self._refresh_event.set()

        # Configuration
        self.debounce_interval = debounce_interval
        
        # Statistics for debugging
        self.stats = {
            "refreshes": 0,
            "successful_refreshes": 0,
            "failed_refreshes": 0,
            "cached_hits": 0
        }
        
        # Auto-initialize if page is provided
        if auto_init and page:
            self.initialize()
    
    def _extract_latest_dom_data(self, library: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract the most recent DOM data from the library.
        Library format: {"url#hash": {DOM_DATA}, ...}
        Returns: {DOM_DATA} or {}
        """
        if not library:
            return {}
        
        # If page is available, try to find matching URL using EXACT normalized comparison
        if self.page:
            try:
                # Keep fragment for SPA routing (#login, #dashboard, etc.)
                current_url = self._normalize_url(self.page.url, keep_fragment=True)
                
                print(f" Looking for DOM data for: {current_url}")
                
                # Try exact match first (normalized URL WITH fragment)
                for key, value in library.items():
                    # Extract just the URL part from "url#hash" key
                    # Library key format: "https://example.com/#page#12345678"
                    #                      ^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^
                    #                      URL part (keep)         hash ID (remove)
                    if '#' in key:
                        # Split from the right to separate hash ID
                        parts = key.rsplit('#', 1)
                        if len(parts) == 2:
                            key_url = parts[0]  # This includes SPA fragment like #login
                        else:
                            key_url = key
                    else:
                        key_url = key
                    
                    key_url_normalized = self._normalize_url(key_url, keep_fragment=True)
                    
                    print(f"    Comparing with: {key_url_normalized}")
                    
                    # Exact match on normalized URLs (including fragment!)
                    if current_url == key_url_normalized:
                        print(f"   [OK] MATCH FOUND: {key}")
                        return value
                
                print(f"   [WARN] No exact match found")
                    
            except Exception as e:
                print(f"   [WARN] Error matching URL: {e}")
        
        # Fallback: return the most recently added entry
        if library:
            # Get entries sorted by extraction time if available
            entries_with_time = []
            for key, value in library.items():
                extraction_time = value.get('fetch_meta', {}).get('extraction_time', '')
                entries_with_time.append((extraction_time, key, value))
            
            if entries_with_time:
                # Sort by time descending (most recent first)
                entries_with_time.sort(reverse=True)
                fallback_key = entries_with_time[0][1]
                print(f"    Using most recent entry: {fallback_key}")
                return entries_with_time[0][2]  # Return the DOM data
        
        return {}

    # --------------------------------------------------------
    # Initialization
    # --------------------------------------------------------

    def initialize(self):
        """
        Initialize the DOM manager with SPA watchers and initial state.
        Should be called once per page after page object is set.
        """
        if self._initialized:
            print("[INFO]  DOM Manager already initialized.")
            return
        
        if not self.page:
            print("[WARN] Cannot initialize: no page object set.")
            return
        
        print(" Initializing DOM Manager...")
        
        # Set up SPA watchers
        self.initialize_spa_watchers()
        
        # Capture initial state if page is loaded
        try:
            if self.page.url and self.page.url != "about:blank":
                self.last_url = self.page.url
                self.last_url_normalized = self._normalize_url(self.page.url)
                try:
                    html = self.page.content()
                    self.last_dom_hash = stable_dom_hash(html)
                except Exception:
                    pass
        except Exception as e:
            print(f"[WARN] Could not capture initial page state: {e}")
        
        self._initialized = True
        print("[OK] DOM Manager initialized.")

    def initialize_spa_watchers(self):
        """Inject mutation observer and history API hooks for SPA detection."""
        if not self.page:
            print("[WARN] Cannot inject SPA watchers: no page object.")
            return

        js_setup = """
        (function() {
            if (window.__domManagerInitialized) {
                console.log('DOM Manager watchers already initialized');
                return;
            }
            
            console.log('Initializing DOM Manager watchers...');
            window.__domManagerInitialized = true;
            window.__domChanged = false;
            window.__routeChanged = false;

            // MutationObserver for DOM changes
            try {
                const observer = new MutationObserver(mutations => {
                    let significant = 0;
                    for (const m of mutations) {
                        if (m.addedNodes.length > 3 || m.removedNodes.length > 3) {
                            significant++;
                        }
                        if (significant > 3) break;
                    }
                    if (significant > 3) {
                        window.__domChanged = true;
                        console.log('Significant DOM change detected');
                    }
                });
                
                if (document.body) {
                    observer.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                    console.log('MutationObserver attached');
                } else {
                    console.warn('document.body not ready for observer');
                }
            } catch (e) {
                console.error('Failed to set up MutationObserver:', e);
            }

            // Hook into history API for SPA route changes
            try {
                const pushState = history.pushState;
                const replaceState = history.replaceState;

                function routeChanged() {
                    window.__routeChanged = true;
                    window.__domChanged = true;
                    console.log('Route change detected');
                }

                history.pushState = function() {
                    pushState.apply(this, arguments);
                    routeChanged();
                };
                
                history.replaceState = function() {
                    replaceState.apply(this, arguments);
                    routeChanged();
                };
                
                window.addEventListener('popstate', routeChanged);
                console.log('History API hooks installed');
            } catch (e) {
                console.error('Failed to hook history API:', e);
            }
            
            console.log('DOM Manager watchers initialized successfully');
        })();
        """
        try:
            self.page.evaluate(js_setup)
            print("[OK] SPA watchers injected successfully.")
        except Exception as e:
            print(f"[WARN] Failed to inject SPA watchers: {e}")

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    def _normalize_url(self, url: str, keep_fragment: bool = True) -> str:
        """
        Normalize URL for comparison.
        
        Args:
            url: URL to normalize
            keep_fragment: If True, keeps the fragment (#hash) for SPA routing
        
        Returns:
            Normalized URL
        """
        try:
            p = urlsplit(url)
            if keep_fragment:
                # Keep fragment for SPA routing (e.g., #login, #dashboard)
                return urlunsplit((p.scheme, p.netloc, p.path, "", p.fragment))
            else:
                # Remove query and fragment
                return urlunsplit((p.scheme, p.netloc, p.path, "", ""))
        except Exception:
            return url

    def _check_dom_changed(self) -> bool:
        """Determine if the DOM has meaningfully changed."""
        if not self.page:
            return False

        try:
            current_url = self.page.url
            normalized = self._normalize_url(current_url)

            # Check SPA-triggered flags
            try:
                spa_flag = self.page.evaluate("window.__domChanged || false")
                route_flag = self.page.evaluate("window.__routeChanged || false")
            except Exception:
                spa_flag = False
                route_flag = False

            # Compute stable DOM hash
            try:
                html = self.page.content()
                current_hash = stable_dom_hash(html)
            except Exception as e:
                print(f"[WARN] Could not compute DOM hash: {e}")
                current_hash = None

            # Reset SPA flags after read
            try:
                self.page.evaluate("window.__domChanged = false; window.__routeChanged = false;")
            except Exception:
                pass

            # Evaluate change significance
            url_changed = normalized != self.last_url_normalized
            hash_changed = current_hash and current_hash != self.last_dom_hash

            changed = route_flag or url_changed or hash_changed or spa_flag
            
            if changed:
                change_reasons = []
                if route_flag:
                    change_reasons.append("route change")
                if url_changed:
                    change_reasons.append("URL change")
                if hash_changed:
                    change_reasons.append("DOM hash change")
                if spa_flag:
                    change_reasons.append("SPA mutation")
                print(f" DOM change detected: {', '.join(change_reasons)}")
            
            return changed

        except Exception as e:
            print(f"[WARN] Error checking DOM change: {e}")
            return False

    # --------------------------------------------------------
    # Refresh Management
    # --------------------------------------------------------

    def maybe_refresh_dom(self, force=False, reason=""):
        """
        Refresh the DOM library if a meaningful change is detected.
        
        Args:
            force: Force refresh regardless of change detection
            reason: Optional reason for refresh (for logging)
        """
        if not self.page:
            print("[ERR] No page set; cannot refresh DOM.")
            return False

        # Debounce guard (unless forced)
        time_since_last = time.time() - self._last_refresh_ts
        if not force and time_since_last < self.debounce_interval:
            print(f"⏭  Skipping refresh (debounce: {time_since_last:.1f}s < {self.debounce_interval}s)")
            return False

        # Check if already refreshing
        if self._refresh_in_progress:
            print("⏳ Refresh already in progress; waiting...")
            self._refresh_event.wait(timeout=15.0)
            return bool(self.dom_data and validate_dom_structure(self.dom_data))

        # Acquire lock for thread safety
        with self._refresh_lock:
            if self._refresh_in_progress:
                return False
            
            self._refresh_in_progress = True
            self._refresh_event.clear()

        try:
            # Check if refresh is needed
            dom_changed = force or self._check_dom_changed()
            
            if not dom_changed:
                print("[OK] DOM unchanged — using cached library.")
                self.stats["cached_hits"] += 1
                return True

            # Perform refresh
            self.stats["refreshes"] += 1
            if reason:
                print(f" Refreshing DOM: {reason}")
            
            # This now returns DOM data, not the full library
            new_dom = refresh_dom(self.page, self.dom_path)

            if new_dom and validate_dom_structure(new_dom):
                # Update cached DOM data
                try:
                    html = self.page.content()
                    self.dom_data = new_dom  # This is now just the DOM data
                    
                    # Also reload the library to keep it in sync
                    self.dom_library = load_dom_library(self.dom_path)
                    
                    # Update tracking
                    self.last_dom_hash = stable_dom_hash(html)
                    self.last_url = self.page.url
                    self.last_url_normalized = self._normalize_url(self.page.url)
                    self._last_refresh_ts = time.time()
                    self.stats["successful_refreshes"] += 1
                    
                    # Log DOM summary
                    self._log_dom_summary()
                    
                    print("[OK] DOM library updated and cached.")
                    return True
                except Exception as e:
                    print(f"[WARN] Error updating DOM state: {e}")
                    self.stats["failed_refreshes"] += 1
                    return False
            else:
                print("[WARN] DOM refresh produced no valid data — using cached version.")
                self.stats["failed_refreshes"] += 1
                return False

        except Exception as e:
            print(f"[ERR] Error during DOM refresh: {e}")
            self.stats["failed_refreshes"] += 1
            return False
        finally:
            self._refresh_in_progress = False
            self._refresh_event.set()

    # --------------------------------------------------------
    # Accessors & Utilities
    # --------------------------------------------------------

    def get_dom(self) -> Optional[Dict[str, Any]]:
        """Return cached DOM data (not the full library)."""
        return self.dom_data
    
    def get_library(self) -> Dict[str, Any]:
        """Return the full DOM library with all URLs."""
        return self.dom_library

    def is_dom_valid(self) -> bool:
        """Check if current DOM data is valid and populated."""
        return validate_dom_structure(self.dom_data)

    def find_or_refresh(
        self, 
        selector_fn: Callable, 
        *args, 
        wait_timeout=10.0, 
        force_refresh=False,
        **kwargs
    ):
        """
        Attempt to resolve using cached DOM, refreshing only if necessary.

        Logic:
        1. Try cached DOM immediately (unless force_refresh)
        2. If not found, wait for any in-progress refresh
        3. If still not found, trigger a refresh
        4. Try one final time after refresh
        
        Args:
            selector_fn: Function that takes DOM data and returns a selector
            *args: Arguments to pass to selector_fn
            wait_timeout: Max time to wait for refresh
            force_refresh: Force a refresh even if element found in cache
            **kwargs: Keyword arguments to pass to selector_fn
        """
        try:
            # Try cached DOM first (unless forced)
            if not force_refresh:
                result = selector_fn(self.dom_data, *args, **kwargs)
                if result:
                    self.stats["cached_hits"] += 1
                    return result

            # Wait for any in-progress refresh
            if self._refresh_in_progress:
                print("⏳ Waiting for ongoing refresh...")
                self._refresh_event.wait(timeout=wait_timeout)
                result = selector_fn(self.dom_data, *args, **kwargs)
                if result:
                    return result

            # Trigger refresh if DOM might have changed
            print(" Element not found in cache, attempting refresh...")
            refresh_success = self.maybe_refresh_dom(force=False, reason="element not found")
            
            if refresh_success or force_refresh:
                # Try again with refreshed DOM
                result = selector_fn(self.dom_data, *args, **kwargs)
                if result:
                    return result
            
            return None

        except Exception as e:
            print(f"[WARN] Error in find_or_refresh: {e}")
            return None

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    def _log_dom_summary(self):
        """Log a summary of what's in the current DOM library."""
        if not self.dom_data:
            print(" DOM Summary: Empty")
            return
        
        summary = []
        if "forms" in self.dom_data:
            total_inputs = sum(len(f.get("inputs", [])) for f in self.dom_data["forms"])
            summary.append(f"{len(self.dom_data['forms'])} forms ({total_inputs} inputs)")
        
        if "buttons_and_links" in self.dom_data:
            summary.append(f"{len(self.dom_data['buttons_and_links'])} buttons/links")
        
        if "images" in self.dom_data:
            img_count = len(self.dom_data["images"].get("sample", []))
            if img_count:
                summary.append(f"{img_count} images")
        
        if "visible_elements" in self.dom_data:
            summary.append(f"{len(self.dom_data['visible_elements'])} visible elements")
        
        print(f" DOM Summary: {', '.join(summary) if summary else 'No data'}")

    def diagnose(self):
        """Print comprehensive diagnostic information about DOM state."""
        print("\n" + "="*60)
        print(" DOM MANAGER DIAGNOSTICS")
        print("="*60)
        
        print(f"\n Configuration:")
        print(f"   DOM Library Path: {self.dom_path}")
        print(f"   Debounce Interval: {self.debounce_interval}s")
        print(f"   Initialized: {self._initialized}")
        
        print(f"\n Statistics:")
        print(f"   Total Refreshes: {self.stats['refreshes']}")
        print(f"   Successful: {self.stats['successful_refreshes']}")
        print(f"   Failed: {self.stats['failed_refreshes']}")
        print(f"   Cache Hits: {self.stats['cached_hits']}")
        
        print(f"\n Page State:")
        if self.page:
            try:
                print(f"   Current URL: {self.page.url}")
                print(f"   Normalized URL: {self._normalize_url(self.page.url)}")
            except Exception:
                print(f"   Current URL: <error reading>")
        else:
            print(f"   No page object set")
        
        print(f"\n DOM Library State:")
        if not self.dom_data:
            print(f"   [ERR] DOM library is empty or not loaded")
        else:
            print(f"   [OK] DOM library loaded")
            print(f"   Valid Structure: {validate_dom_structure(self.dom_data)}")
            
            if "forms" in self.dom_data:
                total_inputs = sum(len(f.get("inputs", [])) for f in self.dom_data["forms"])
                print(f"   - Forms: {len(self.dom_data['forms'])} (Inputs: {total_inputs})")
            
            if "buttons_and_links" in self.dom_data:
                print(f"   - Buttons/Links: {len(self.dom_data['buttons_and_links'])}")
            
            if "images" in self.dom_data:
                img_count = len(self.dom_data["images"].get("sample", []))
                print(f"   - Images: {img_count}")
            
            if "visible_elements" in self.dom_data:
                print(f"   - Visible Elements: {len(self.dom_data['visible_elements'])}")
            
            if "visible_text_sample" in self.dom_data:
                print(f"   - Visible Text Samples: {len(self.dom_data['visible_text_sample'])}")
        
        print("\n" + "="*60 + "\n")

    def get_stats(self) -> Dict[str, int]:
        """Return statistics about DOM manager operations."""
        return self.stats.copy()
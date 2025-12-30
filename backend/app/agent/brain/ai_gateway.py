"""
AI Gateway for QA Brain
========================

Controls and optimizes AI usage with token budgeting.
Acts as a gatekeeper that:
- Limits AI calls to stay within budget
- Caches AI responses for reuse
- Batches similar requests
- Tracks token usage

The goal is MINIMAL AI usage - only when the brain
truly cannot decide on its own.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class RequestPriority(Enum):
    """Priority levels for AI requests"""
    CRITICAL = 1  # Must have AI response
    HIGH = 2      # Prefer AI but can fallback
    NORMAL = 3    # Nice to have
    LOW = 4       # Only if budget allows


@dataclass
class AIRequest:
    """A request for AI assistance"""
    request_type: str  # element_find, action_interpret, error_analyze
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.NORMAL
    max_tokens: int = 500
    include_screenshot: bool = False
    screenshot_data: Optional[str] = None  # base64


@dataclass
class AIResponse:
    """Response from AI"""
    success: bool
    content: str
    tokens_used: int
    cached: bool = False
    latency_ms: int = 0
    error: Optional[str] = None


@dataclass
class TokenBudget:
    """Token budget management"""
    daily_limit: int = 50000
    hourly_limit: int = 5000
    per_test_limit: int = 2000
    used_today: int = 0
    used_this_hour: int = 0
    used_this_test: int = 0
    last_reset_day: str = ""
    last_reset_hour: int = -1


class AIGateway:
    """
    Gatekeeper for AI API calls.

    Responsibilities:
    - Enforce token budgets
    - Cache AI responses
    - Batch similar requests
    - Track usage metrics
    - Fallback handling
    """

    def __init__(
        self,
        data_dir: str = "data/agent_knowledge",
        provider: AIProvider = AIProvider.ANTHROPIC
    ):
        self.data_dir = Path(data_dir)
        self.provider = provider
        self.cache_dir = self.data_dir / "ai_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Token budget
        self.budget = TokenBudget()
        self._load_budget()

        # Response cache (in-memory LRU)
        self.cache: Dict[str, AIResponse] = {}
        self.cache_max_size = 1000

        # Request batching
        self.pending_requests: List[AIRequest] = []
        self.batch_delay_ms = 100

        # Statistics
        self.total_requests = 0
        self.cache_hits = 0
        self.budget_blocks = 0
        self.api_calls = 0
        self.total_tokens = 0

        # Callbacks
        self._on_budget_warning: Optional[Callable[[int, int], None]] = None

    def _load_budget(self):
        """Load budget state from disk"""
        budget_file = self.data_dir / "ai_budget.json"
        if budget_file.exists():
            try:
                with open(budget_file, 'r') as f:
                    data = json.load(f)
                    self.budget.used_today = data.get("used_today", 0)
                    self.budget.used_this_hour = data.get("used_this_hour", 0)
                    self.budget.last_reset_day = data.get("last_reset_day", "")
                    self.budget.last_reset_hour = data.get("last_reset_hour", -1)
            except:
                pass

        # Check if we need to reset
        self._check_budget_reset()

    def _save_budget(self):
        """Save budget state to disk"""
        budget_file = self.data_dir / "ai_budget.json"
        try:
            with open(budget_file, 'w') as f:
                json.dump({
                    "used_today": self.budget.used_today,
                    "used_this_hour": self.budget.used_this_hour,
                    "last_reset_day": self.budget.last_reset_day,
                    "last_reset_hour": self.budget.last_reset_hour
                }, f)
        except:
            pass

    def _check_budget_reset(self):
        """Check and reset budgets if needed"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.hour

        # Daily reset
        if self.budget.last_reset_day != today:
            self.budget.used_today = 0
            self.budget.last_reset_day = today

        # Hourly reset
        if self.budget.last_reset_hour != hour:
            self.budget.used_this_hour = 0
            self.budget.last_reset_hour = hour

    def start_test(self):
        """Start a new test - reset per-test budget"""
        self.budget.used_this_test = 0

    def can_make_request(self, request: AIRequest) -> bool:
        """Check if we have budget for this request"""
        self._check_budget_reset()

        # Critical requests always allowed
        if request.priority == RequestPriority.CRITICAL:
            return True

        # Check daily limit
        if self.budget.used_today >= self.budget.daily_limit:
            logger.warning("[AI-GATE] Daily token limit reached")
            return False

        # Check hourly limit
        if self.budget.used_this_hour >= self.budget.hourly_limit:
            logger.warning("[AI-GATE] Hourly token limit reached")
            return False

        # Check per-test limit for non-high priority
        if request.priority.value >= RequestPriority.NORMAL.value:
            if self.budget.used_this_test >= self.budget.per_test_limit:
                logger.warning("[AI-GATE] Per-test token limit reached")
                return False

        return True

    def get_cache_key(self, request: AIRequest) -> str:
        """Generate cache key for a request"""
        data = f"{request.request_type}|{request.prompt}|{json.dumps(request.context, sort_keys=True)}"
        return hashlib.md5(data.encode()).hexdigest()

    def check_cache(self, request: AIRequest) -> Optional[AIResponse]:
        """Check if response is cached"""
        key = self.get_cache_key(request)

        # In-memory cache
        if key in self.cache:
            self.cache_hits += 1
            response = self.cache[key]
            response.cached = True
            return response

        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    response = AIResponse(
                        success=True,
                        content=data["content"],
                        tokens_used=0,  # Cached, no new tokens
                        cached=True
                    )
                    self.cache[key] = response
                    self.cache_hits += 1
                    return response
            except:
                pass

        return None

    def cache_response(self, request: AIRequest, response: AIResponse):
        """Cache a response"""
        if not response.success:
            return

        key = self.get_cache_key(request)

        # In-memory cache
        self.cache[key] = response

        # Enforce cache size limit
        if len(self.cache) > self.cache_max_size:
            # Remove oldest entries
            keys = list(self.cache.keys())
            for old_key in keys[:len(keys)//4]:
                del self.cache[old_key]

        # Disk cache (for persistence)
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    "content": response.content,
                    "request_type": request.request_type,
                    "cached_at": time.time()
                }, f)
        except:
            pass

    async def request(self, request: AIRequest) -> AIResponse:
        """
        Make an AI request with caching and budget checking.

        This is the main entry point for AI calls.
        """
        self.total_requests += 1
        start_time = time.time()

        # 1. Check cache first
        cached = self.check_cache(request)
        if cached:
            logger.debug(f"[AI-GATE] Cache hit for {request.request_type}")
            return cached

        # 2. Check budget
        if not self.can_make_request(request):
            self.budget_blocks += 1
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error="Budget limit reached"
            )

        # 3. Make API call
        try:
            response = await self._call_ai(request)

            # 4. Update budget
            self.budget.used_today += response.tokens_used
            self.budget.used_this_hour += response.tokens_used
            self.budget.used_this_test += response.tokens_used
            self.total_tokens += response.tokens_used
            self.api_calls += 1

            # Check for warnings
            if self._on_budget_warning:
                if self.budget.used_today > self.budget.daily_limit * 0.8:
                    self._on_budget_warning(self.budget.used_today, self.budget.daily_limit)

            # 5. Cache response
            self.cache_response(request, response)

            # Save budget state
            self._save_budget()

            response.latency_ms = int((time.time() - start_time) * 1000)
            return response

        except Exception as e:
            logger.error(f"[AI-GATE] API call failed: {e}")
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error=str(e)
            )

    async def _call_ai(self, request: AIRequest) -> AIResponse:
        """Make actual API call to AI provider"""
        if self.provider == AIProvider.ANTHROPIC:
            return await self._call_anthropic(request)
        elif self.provider == AIProvider.OPENAI:
            return await self._call_openai(request)
        elif self.provider == AIProvider.OLLAMA:
            return await self._call_ollama(request)
        else:
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error=f"Unknown provider: {self.provider}"
            )

    async def _call_anthropic(self, request: AIRequest) -> AIResponse:
        """Call Anthropic Claude API"""
        try:
            import httpx

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return AIResponse(
                    success=False,
                    content="",
                    tokens_used=0,
                    error="ANTHROPIC_API_KEY not set"
                )

            messages_content = []

            # Add screenshot if provided
            if request.include_screenshot and request.screenshot_data:
                messages_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": request.screenshot_data
                    }
                })

            messages_content.append({
                "type": "text",
                "text": request.prompt
            })

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": request.max_tokens,
                        "messages": [
                            {
                                "role": "user",
                                "content": messages_content
                            }
                        ]
                    }
                )

                if response.status_code != 200:
                    return AIResponse(
                        success=False,
                        content="",
                        tokens_used=0,
                        error=f"API error: {response.status_code}"
                    )

                data = response.json()
                content = data["content"][0]["text"]
                tokens = data.get("usage", {}).get("input_tokens", 0) + \
                        data.get("usage", {}).get("output_tokens", 0)

                return AIResponse(
                    success=True,
                    content=content,
                    tokens_used=tokens
                )

        except Exception as e:
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error=str(e)
            )

    async def _call_openai(self, request: AIRequest) -> AIResponse:
        """Call OpenAI API"""
        try:
            import httpx

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return AIResponse(
                    success=False,
                    content="",
                    tokens_used=0,
                    error="OPENAI_API_KEY not set"
                )

            messages = [{"role": "user", "content": request.prompt}]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": request.max_tokens
                    }
                )

                if response.status_code != 200:
                    return AIResponse(
                        success=False,
                        content="",
                        tokens_used=0,
                        error=f"API error: {response.status_code}"
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)

                return AIResponse(
                    success=True,
                    content=content,
                    tokens_used=tokens
                )

        except Exception as e:
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error=str(e)
            )

    async def _call_ollama(self, request: AIRequest) -> AIResponse:
        """Call Ollama local API"""
        try:
            import httpx

            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llama3.2:3b",
                        "prompt": request.prompt,
                        "stream": False
                    }
                )

                if response.status_code != 200:
                    return AIResponse(
                        success=False,
                        content="",
                        tokens_used=0,
                        error=f"Ollama error: {response.status_code}"
                    )

                data = response.json()
                content = data.get("response", "")

                # Ollama doesn't report exact tokens, estimate
                tokens = len(request.prompt.split()) + len(content.split())

                return AIResponse(
                    success=True,
                    content=content,
                    tokens_used=tokens
                )

        except Exception as e:
            return AIResponse(
                success=False,
                content="",
                tokens_used=0,
                error=str(e)
            )

    # =========================================================================
    # SPECIALIZED REQUEST METHODS
    # =========================================================================

    async def find_element(
        self,
        intent: str,
        page_context: str,
        screenshot_data: str = None
    ) -> AIResponse:
        """Request AI help to find an element"""
        prompt = f"""Find the best CSS selector for this element:

Intent: {intent}
Page Context: {page_context}

Return ONLY a valid CSS selector, nothing else.
Example: button[type="submit"]"""

        return await self.request(AIRequest(
            request_type="element_find",
            prompt=prompt,
            context={"intent": intent, "page": page_context},
            priority=RequestPriority.HIGH,
            max_tokens=100,
            include_screenshot=screenshot_data is not None,
            screenshot_data=screenshot_data
        ))

    async def interpret_step(self, step_text: str, page_context: str) -> AIResponse:
        """Request AI help to interpret a test step"""
        prompt = f"""Interpret this test step and return the action:

Step: {step_text}
Page Context: {page_context}

Return JSON with:
{{"action": "click|type|navigate|etc", "target": "element description", "value": "if applicable"}}"""

        return await self.request(AIRequest(
            request_type="step_interpret",
            prompt=prompt,
            context={"step": step_text},
            priority=RequestPriority.NORMAL,
            max_tokens=200
        ))

    async def analyze_error(self, error_message: str, page_context: str) -> AIResponse:
        """Request AI help to analyze an error"""
        prompt = f"""Analyze this error and suggest recovery:

Error: {error_message}
Page Context: {page_context}

Return JSON with:
{{"error_type": "type", "cause": "likely cause", "recovery": "suggested action"}}"""

        return await self.request(AIRequest(
            request_type="error_analyze",
            prompt=prompt,
            context={"error": error_message},
            priority=RequestPriority.NORMAL,
            max_tokens=300
        ))

    # =========================================================================
    # MANAGEMENT
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (self.cache_hits / max(1, self.total_requests)) * 100,
            "api_calls": self.api_calls,
            "budget_blocks": self.budget_blocks,
            "total_tokens": self.total_tokens,
            "budget": {
                "daily_used": self.budget.used_today,
                "daily_limit": self.budget.daily_limit,
                "daily_remaining": self.budget.daily_limit - self.budget.used_today,
                "hourly_used": self.budget.used_this_hour,
                "hourly_limit": self.budget.hourly_limit,
                "test_used": self.budget.used_this_test,
                "test_limit": self.budget.per_test_limit
            }
        }

    def set_budget(
        self,
        daily_limit: int = None,
        hourly_limit: int = None,
        per_test_limit: int = None
    ):
        """Update budget limits"""
        if daily_limit is not None:
            self.budget.daily_limit = daily_limit
        if hourly_limit is not None:
            self.budget.hourly_limit = hourly_limit
        if per_test_limit is not None:
            self.budget.per_test_limit = per_test_limit

    def set_budget_warning_callback(self, callback: Callable[[int, int], None]):
        """Set callback for budget warnings"""
        self._on_budget_warning = callback

    def clear_cache(self):
        """Clear all cached responses"""
        self.cache.clear()
        # Clear disk cache
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except:
                pass
        logger.info("[AI-GATE] Cache cleared")

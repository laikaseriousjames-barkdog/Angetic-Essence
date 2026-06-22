"""Phase 1: Token Budget Gatekeeper.

Monitors token and API usage per rolling hour.
Forcefully terminates the loop if thresholds are exceeded.
"""

import os
import time
import threading
from collections import deque
from typing import List, Tuple


class BudgetExceededError(Exception):
    pass


class TokenBudgetGatekeeper:
    def __init__(
        self,
        max_tokens_per_hour: int = 100000,
        max_api_calls_per_hour: int = 500,
        hard_token_limit: int = 500000,
    ):
        self.max_tokens_per_hour = max_tokens_per_hour
        self.max_api_calls_per_hour = max_api_calls_per_hour
        self.hard_token_limit = hard_token_limit
        self._token_log: deque[Tuple[float, int]] = deque()
        self._api_log: deque[float] = deque()
        self._total_tokens = 0
        self._lock = threading.Lock()
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)

    def start(self):
        self._monitor_thread.start()

    def stop(self):
        self._running = False

    def record_tokens(self, count: int):
        now = time.time()
        with self._lock:
            self._token_log.append((now, count))
            self._total_tokens += count

    def record_api_call(self):
        now = time.time()
        with self._lock:
            self._api_log.append(now)

    def _prune(self):
        cutoff = time.time() - 3600
        with self._lock:
            while self._token_log and self._token_log[0][0] < cutoff:
                _, tokens = self._token_log.popleft()
                self._total_tokens -= tokens
            while self._api_log and self._api_log[0] < cutoff:
                self._api_log.popleft()

    def _check(self):
        self._prune()
        with self._lock:
            recent_tokens = sum(t for _, t in self._token_log)
            recent_calls = len(self._api_log)
        if recent_tokens > self.max_tokens_per_hour:
            raise BudgetExceededError(
                f"Token budget exceeded: {recent_tokens}/{self.max_tokens_per_hour}"
            )
        if recent_calls > self.max_api_calls_per_hour:
            raise BudgetExceededError(
                f"API call budget exceeded: {recent_calls}/{self.max_api_calls_per_hour}"
            )
        if self._total_tokens > self.hard_token_limit:
            raise BudgetExceededError(
                f"Hard token limit exceeded: {self._total_tokens}/{self.hard_token_limit}"
            )

    def _monitor_loop(self):
        while self._running:
            try:
                self._check()
            except BudgetExceededError as e:
                print(f"[BUDGET_GATEKEEPER] {e}")
                print("[BUDGET_GATEKEEPER] Forcefully terminating execution.")
                os._exit(137)
            time.sleep(60)

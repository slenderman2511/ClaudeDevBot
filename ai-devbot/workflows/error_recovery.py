"""
Error Recovery Module

Provides automatic retry, fallback strategies, and task resumption for failed workflows.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for failed tasks."""
    RETRY = "retry"           # Retry the same operation
    FALLBACK = "fallback"     # Use alternative approach
    SKIP = "skip"            # Skip the failed task
    ABORT = "abort"          # Abort the entire workflow


class FailureReason(Enum):
    """Reasons for task failure."""
    TIMEOUT = "timeout"
    AGENT_ERROR = "agent_error"
    TOOL_ERROR = "tool_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    enabled: bool = True
    fallback_agents: Dict[str, str] = field(default_factory=dict)
    max_fallbacks: int = 2


@dataclass
class RecoveryRecord:
    """Record of recovery action taken."""
    task_id: str
    attempt: int
    strategy: RecoveryStrategy
    success: bool
    error: str
    timestamp: datetime
    duration: float


class ErrorRecovery:
    """
    Error recovery system for workflows.

    Features:
    - Configurable retry with exponential backoff
    - Fallback agents for failed tasks
    - Automatic task resumption
    - Failure tracking and analysis
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        fallback_config: Optional[FallbackConfig] = None
    ):
        """
        Initialize error recovery.

        Args:
            retry_config: Retry configuration
            fallback_config: Fallback configuration
        """
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()

        self._recovery_history: deque = deque(maxlen=100)
        self._workflow_state: Dict[str, Dict] = {}

        logger.info("ErrorRecovery initialized")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.retry_config.exponential_backoff:
            delay = self.retry_config.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.retry_config.base_delay

        # Cap at max delay
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter
        if self.retry_config.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay

    def classify_failure(self, error: str) -> FailureReason:
        """Classify the reason for failure."""
        error_lower = error.lower()

        if "timeout" in error_lower:
            return FailureReason.TIMEOUT
        elif "validation" in error_lower:
            return FailureReason.VALIDATION_ERROR
        elif "agent" in error_lower or "execute" in error_lower:
            return FailureReason.AGENT_ERROR
        elif "tool" in error_lower or "command" in error_lower:
            return FailureReason.TOOL_ERROR
        else:
            return FailureReason.UNKNOWN

    def determine_strategy(
        self,
        error: str,
        attempt: int,
        context: Dict[str, Any]
    ) -> RecoveryStrategy:
        """Determine the best recovery strategy."""
        # Check if max retries exceeded
        if attempt >= self.retry_config.max_attempts:
            # Check if fallback is available
            if self.fallback_config.enabled:
                agent_name = context.get('agent_name', '')
                if agent_name in self.fallback_config.fallback_agents:
                    return RecoveryStrategy.FALLBACK
            return RecoveryStrategy.ABORT

        # Classify failure
        reason = self.classify_failure(error)

        # Determine strategy based on reason
        if reason == FailureReason.TIMEOUT:
            # Timeouts are worth retrying
            return RecoveryStrategy.RETRY
        elif reason == FailureReason.VALIDATION_ERROR:
            # Validation errors likely won't be fixed by retry
            return RecoveryStrategy.SKIP
        elif reason == FailureReason.AGENT_ERROR:
            # Try fallback if available
            if self.fallback_config.enabled:
                agent_name = context.get('agent_name', '')
                if agent_name in self.fallback_config.fallback_agents:
                    return RecoveryStrategy.FALLBACK
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.RETRY

    async def execute_with_recovery(
        self,
        task_id: str,
        execute_func: Callable,
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute a function with error recovery.

        Args:
            task_id: Task identifier
            execute_func: Async function to execute
            context: Execution context

        Returns:
            Result of successful execution
        """
        last_error = None
        attempt = 0

        while attempt < self.retry_config.max_attempts:
            attempt += 1

            try:
                # Execute the function
                result = await execute_func()

                # Record successful recovery if this was a retry
                if attempt > 1:
                    self._record_recovery(
                        task_id=task_id,
                        attempt=attempt,
                        strategy=RecoveryStrategy.RETRY,
                        success=True,
                        error=str(last_error) if last_error else None
                    )

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt} failed for task {task_id}: {e}")

                # Determine recovery strategy
                strategy = self.determine_strategy(
                    error=str(e),
                    attempt=attempt,
                    context=context
                )

                # Record the failure
                self._record_recovery(
                    task_id=task_id,
                    attempt=attempt,
                    strategy=strategy,
                    success=False,
                    error=str(e)
                )

                # Handle strategy
                if strategy == RecoveryStrategy.ABORT:
                    logger.error(f"Aborting task {task_id} after {attempt} attempts")
                    break

                elif strategy == RecoveryStrategy.SKIP:
                    logger.warning(f"Skipping task {task_id}")
                    return None

                elif strategy == RecoveryStrategy.FALLBACK:
                    # Get fallback agent
                    agent_name = context.get('agent_name', '')
                    fallback_agent = self.fallback_config.fallback_agents.get(agent_name)
                    if fallback_agent:
                        logger.info(f"Falling back to {fallback_agent} for task {task_id}")
                        context['agent_name'] = fallback_agent

                elif strategy == RecoveryStrategy.RETRY:
                    # Wait before retry
                    if attempt < self.retry_config.max_attempts:
                        delay = self.calculate_delay(attempt)
                        logger.info(f"Retrying task {task_id} in {delay:.2f}s")
                        await asyncio.sleep(delay)

        # All recovery attempts failed
        raise Exception(f"Task {task_id} failed after {attempt} attempts: {last_error}")

    def _record_recovery(
        self,
        task_id: str,
        attempt: int,
        strategy: RecoveryStrategy,
        success: bool,
        error: Optional[str]
    ):
        """Record recovery action."""
        record = RecoveryRecord(
            task_id=task_id,
            attempt=attempt,
            strategy=strategy,
            success=success,
            error=error or "",
            timestamp=datetime.now(),
            duration=0.0
        )
        self._recovery_history.append(record)

    def save_workflow_state(self, workflow_id: str, state: Dict[str, Any]):
        """Save workflow state for resumption."""
        self._workflow_state[workflow_id] = {
            'state': state,
            'timestamp': datetime.now()
        }
        logger.info(f"Saved state for workflow {workflow_id}")

    def load_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load saved workflow state."""
        data = self._workflow_state.get(workflow_id)
        if data:
            logger.info(f"Loaded state for workflow {workflow_id}")
            return data['state']
        return None

    def clear_workflow_state(self, workflow_id: str):
        """Clear workflow state."""
        if workflow_id in self._workflow_state:
            del self._workflow_state[workflow_id]

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total = len(self._recovery_history)
        if total == 0:
            return {'total': 0, 'success_rate': 0}

        successful = sum(1 for r in self._recovery_history if r.success)

        by_strategy = {}
        for record in self._recovery_history:
            strategy = record.strategy.value
            if strategy not in by_strategy:
                by_strategy[strategy] = {'total': 0, 'success': 0}
            by_strategy[strategy]['total'] += 1
            if record.success:
                by_strategy[strategy]['success'] += 1

        return {
            'total': total,
            'successful': successful,
            'success_rate': round(successful / total * 100, 1),
            'by_strategy': by_strategy
        }


# Global error recovery instance
_error_recovery: Optional[ErrorRecovery] = None


def get_error_recovery(
    retry_config: Optional[RetryConfig] = None,
    fallback_config: Optional[FallbackConfig] = None
) -> ErrorRecovery:
    """Get or create the global error recovery instance."""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = ErrorRecovery(retry_config, fallback_config)
    return _error_recovery

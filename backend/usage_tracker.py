"""
Usage Tracker - Track API calls and enforce limits.

Provides:
- Session-based API call tracking
- Warning levels (green < 50, yellow 50-79, red 80+)
- Per-field retry limits (max 2 retries per document)
- Persistent storage in session state
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from enum import Enum


class UsageLevel(Enum):
    """API usage warning levels."""
    GREEN = "green"      # < 50 calls - all good
    YELLOW = "yellow"    # 50-79 calls - warning
    RED = "red"          # 80+ calls - critical
    BLOCKED = "blocked"  # Exceeded limit


@dataclass
class FieldRetryInfo:
    """Track retries for a specific document field."""
    field_id: str
    document_type: str
    side: str
    attempts: int = 0
    max_attempts: int = 2
    last_attempt: Optional[datetime] = None
    
    @property
    def can_retry(self) -> bool:
        """Check if more retries are allowed."""
        return self.attempts < self.max_attempts
    
    @property
    def remaining_attempts(self) -> int:
        """Get remaining retry attempts."""
        return max(0, self.max_attempts - self.attempts)


@dataclass
class UsageStats:
    """Current usage statistics."""
    total_calls: int = 0
    session_start: datetime = field(default_factory=datetime.now)
    last_call: Optional[datetime] = None
    field_retries: Dict[str, FieldRetryInfo] = field(default_factory=dict)
    
    # Limits
    WARNING_THRESHOLD: int = 50
    CRITICAL_THRESHOLD: int = 80
    DAILY_LIMIT: int = 100
    
    @property
    def usage_level(self) -> UsageLevel:
        """Get current usage warning level."""
        if self.total_calls >= self.DAILY_LIMIT:
            return UsageLevel.BLOCKED
        elif self.total_calls >= self.CRITICAL_THRESHOLD:
            return UsageLevel.RED
        elif self.total_calls >= self.WARNING_THRESHOLD:
            return UsageLevel.YELLOW
        else:
            return UsageLevel.GREEN
    
    @property
    def remaining_calls(self) -> int:
        """Get remaining API calls for session."""
        return max(0, self.DAILY_LIMIT - self.total_calls)
    
    @property
    def usage_percentage(self) -> float:
        """Get usage as percentage of daily limit."""
        return (self.total_calls / self.DAILY_LIMIT) * 100


class UsageTracker:
    """
    Track API usage and enforce limits.
    
    Usage levels:
    - GREEN: < 50 calls - normal operation
    - YELLOW: 50-79 calls - show warning banner
    - RED: 80+ calls - show critical warning
    - BLOCKED: 100+ calls - prevent further API calls
    """
    
    def __init__(self):
        """Initialize usage tracker."""
        self._stats = UsageStats()
    
    @property
    def stats(self) -> UsageStats:
        """Get current stats."""
        return self._stats
    
    @property
    def total_calls(self) -> int:
        """Get total API calls."""
        return self._stats.total_calls
    
    @property
    def usage_level(self) -> UsageLevel:
        """Get current usage level."""
        return self._stats.usage_level
    
    @property
    def can_make_call(self) -> bool:
        """Check if API calls are allowed."""
        return self._stats.usage_level != UsageLevel.BLOCKED
    
    def record_call(self) -> Tuple[bool, str]:
        """
        Record an API call.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.can_make_call:
            return False, "API limit reached. Please try again tomorrow."
        
        self._stats.total_calls += 1
        self._stats.last_call = datetime.now()
        
        level = self._stats.usage_level
        if level == UsageLevel.RED:
            return True, f"Warning: {self._stats.remaining_calls} API calls remaining today"
        elif level == UsageLevel.YELLOW:
            return True, f"Note: {self._stats.remaining_calls} API calls remaining"
        else:
            return True, ""
    
    def get_field_key(self, document_type: str, side: str) -> str:
        """Generate unique key for document field."""
        return f"{document_type}_{side}"
    
    def can_retry_field(self, document_type: str, side: str) -> Tuple[bool, int]:
        """
        Check if a document field can be retried.
        
        Returns:
            Tuple of (can_retry, remaining_attempts)
        """
        key = self.get_field_key(document_type, side)
        retry_info = self._stats.field_retries.get(key)
        
        if retry_info is None:
            # First attempt
            return True, 2
        
        return retry_info.can_retry, retry_info.remaining_attempts
    
    def record_field_attempt(self, document_type: str, side: str) -> Tuple[bool, str]:
        """
        Record an attempt for a document field.
        
        Returns:
            Tuple of (success, message)
        """
        key = self.get_field_key(document_type, side)
        retry_info = self._stats.field_retries.get(key)
        
        if retry_info is None:
            retry_info = FieldRetryInfo(
                field_id=key,
                document_type=document_type,
                side=side,
                attempts=0
            )
            self._stats.field_retries[key] = retry_info
        
        if not retry_info.can_retry:
            return False, f"Maximum retries ({retry_info.max_attempts}) reached for this document. Please contact support."
        
        retry_info.attempts += 1
        retry_info.last_attempt = datetime.now()
        
        remaining = retry_info.remaining_attempts
        if remaining == 0:
            return True, "This was your last attempt for this document."
        elif remaining == 1:
            return True, f"1 retry remaining for this document."
        else:
            return True, ""
    
    def reset_field(self, document_type: str, side: str) -> None:
        """Reset retry count for a specific field (admin use)."""
        key = self.get_field_key(document_type, side)
        if key in self._stats.field_retries:
            del self._stats.field_retries[key]
    
    def reset_all(self) -> None:
        """Reset all usage stats (admin use)."""
        self._stats = UsageStats()
    
    def get_status_message(self) -> Tuple[str, str, str]:
        """
        Get status message for display.
        
        Returns:
            Tuple of (level_name, message, color_code)
        """
        level = self._stats.usage_level
        remaining = self._stats.remaining_calls
        total = self._stats.total_calls
        
        if level == UsageLevel.BLOCKED:
            return (
                "blocked",
                "Daily API limit reached. Please try again tomorrow or contact support.",
                "#dc3545"  # Red
            )
        elif level == UsageLevel.RED:
            return (
                "critical",
                f" Critical: Only {remaining} API calls remaining today. Use them wisely!",
                "#dc3545"  # Red
            )
        elif level == UsageLevel.YELLOW:
            return (
                "warning", 
                f"📊 {remaining} API calls remaining today ({total} used)",
                "#ffc107"  # Yellow
            )
        else:
            return (
                "ok",
                f" API usage: {total}/{self._stats.DAILY_LIMIT} calls today",
                "#28a745"  # Green
            )
    
    def get_field_status(self, document_type: str, side: str) -> Dict:
        """
        Get status for a specific document field.
        
        Returns:
            Dict with field retry information
        """
        key = self.get_field_key(document_type, side)
        retry_info = self._stats.field_retries.get(key)
        
        if retry_info is None:
            return {
                "attempts": 0,
                "max_attempts": 2,
                "remaining": 2,
                "can_retry": True,
                "message": "First upload attempt"
            }
        
        return {
            "attempts": retry_info.attempts,
            "max_attempts": retry_info.max_attempts,
            "remaining": retry_info.remaining_attempts,
            "can_retry": retry_info.can_retry,
            "message": f"Attempt {retry_info.attempts}/{retry_info.max_attempts}"
        }
    
    def to_dict(self) -> Dict:
        """Export stats as dictionary (for session storage)."""
        return {
            "total_calls": self._stats.total_calls,
            "session_start": self._stats.session_start.isoformat(),
            "last_call": self._stats.last_call.isoformat() if self._stats.last_call else None,
            "field_retries": {
                key: {
                    "attempts": info.attempts,
                    "document_type": info.document_type,
                    "side": info.side
                }
                for key, info in self._stats.field_retries.items()
            }
        }
    
    def from_dict(self, data: Dict) -> None:
        """Load stats from dictionary (from session storage)."""
        self._stats.total_calls = data.get("total_calls", 0)
        
        session_start = data.get("session_start")
        if session_start:
            self._stats.session_start = datetime.fromisoformat(session_start)
        
        last_call = data.get("last_call")
        if last_call:
            self._stats.last_call = datetime.fromisoformat(last_call)
        
        field_retries = data.get("field_retries", {})
        for key, info in field_retries.items():
            self._stats.field_retries[key] = FieldRetryInfo(
                field_id=key,
                document_type=info.get("document_type", ""),
                side=info.get("side", ""),
                attempts=info.get("attempts", 0)
            )


# Global tracker instance
_tracker: Optional[UsageTracker] = None


def get_tracker() -> UsageTracker:
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


def record_api_call() -> Tuple[bool, str]:
    """Record an API call and return status."""
    return get_tracker().record_call()


def can_make_api_call() -> bool:
    """Check if API calls are allowed."""
    return get_tracker().can_make_call


def get_usage_status() -> Tuple[str, str, str]:
    """Get current usage status for display."""
    return get_tracker().get_status_message()


def can_retry_document(document_type: str, side: str) -> Tuple[bool, int]:
    """Check if document can be retried."""
    return get_tracker().can_retry_field(document_type, side)


def record_document_attempt(document_type: str, side: str) -> Tuple[bool, str]:
    """Record a document upload attempt."""
    return get_tracker().record_field_attempt(document_type, side)

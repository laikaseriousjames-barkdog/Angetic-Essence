import uuid
import contextvars
from typing import Optional

# ContextVar ensures trace_id is preserved across async tasks and threads
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('trace_id', default=None)

def generate_trace_id() -> str:
    """Generate a new unique trace identifier."""
    return str(uuid.uuid4())

def set_trace_id(tid: str) -> None:
    """Assign a trace ID to the current execution context."""
    _trace_id_var.set(tid)

def get_trace_id() -> str:
    """Retrieve the current trace ID or generate one if none exists."""
    tid = _trace_id_var.get()
    if not tid:
        tid = generate_trace_id()
        _trace_id_var.set(tid)
    return tid

def clear_trace_id() -> None:
    """Reset the trace ID for the current context."""
    _trace_id_var.set(None)

class TraceContext:
    """Context manager for trace_id propagation."""
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or generate_trace_id()
        self.previous = None

    def __enter__(self):
        self.previous = _trace_id_var.get()
        _trace_id_var.set(self.trace_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous is not None:
            _trace_id_var.set(self.previous)
        else:
            _trace_id_var.set(None)
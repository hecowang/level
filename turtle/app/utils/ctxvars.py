import contextvars

trace_id_var = contextvars.ContextVar("trace_id", default="")

import logging
from app.utils.ctxvars import trace_id_var

class TraceIDFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True

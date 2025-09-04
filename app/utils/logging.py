import logging, sys, structlog

def configure_logging(level: str = "INFO"):
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), stream=sys.stdout, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger()

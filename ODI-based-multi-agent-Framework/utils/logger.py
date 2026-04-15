"""
Structured Logging System for the Multi-Agent Orchestration Framework.

Provides a centralized logging utility that supports console and file output
with a structured format: [timestamp] [LEVEL] [component] message.

This module underpins observability across all framework components, enabling
traceable execution logs for the Meta-Orchestrator, agents, communication
layer, and evaluation pipeline.
"""

import logging
import os
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
) -> logging.Logger:
    """Create and configure a logger with console and optional file handlers.

    Args:
        name: The name of the logger, typically the component name
              (e.g., 'MetaOrchestrator', 'BaseAgent').
        log_file: Path to the log file. Defaults to 'logs/system.log'.
        level: The minimum logging level. Defaults to DEBUG.

    Returns:
        A configured logging.Logger instance.
    """
    if log_file is None:
        # Resolve relative to the project root (parent of utils/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "system.log")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Structured format: [timestamp] [LEVEL] [component] message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

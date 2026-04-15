"""
Main Entry Point — Dynamic Scenario-Driven Multi-Agent Orchestration Framework.

This script initializes the Meta-Orchestrator, accepts a scenario description
from the user, triggers the full dynamic agent synthesis pipeline, and
outputs the structured JSON results.

Usage:
    python main.py
"""

import json
import sys

from orchestrator.meta_orchestrator import MetaOrchestrator
from utils.config import Config
from utils.logger import setup_logger


def main() -> None:
    """Run the orchestration framework entry point."""
    logger = setup_logger("Main")

    # Banner
    print(f"\n{'='*64}")
    print(f"  {Config.PROJECT_NAME}")
    print(f"  {Config.PHASE} – Dynamic Agent Synthesis Active")
    print(f"{'='*64}\n")

    logger.info(f"{Config.PROJECT_NAME} — {Config.PHASE} started.")

    # Initialize Meta-Orchestrator
    orchestrator = MetaOrchestrator()

    # Accept scenario input
    try:
        scenario_text = input("Enter scenario: ")
    except (EOFError, KeyboardInterrupt):
        print("\nNo input received. Exiting.")
        logger.info("No scenario input received. Exiting.")
        sys.exit(0)

    if not scenario_text.strip():
        print("Empty scenario. Exiting.")
        logger.warning("Empty scenario provided. Exiting.")
        sys.exit(0)

    # Execute the full orchestration pipeline
    try:
        response = orchestrator.execute(scenario_text)
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        print(f"\nError: {e}\n")
        sys.exit(1)

    # Output structured JSON response
    print(f"\n{json.dumps(response, indent=2)}\n")

    logger.info(f"{Config.PHASE} execution completed successfully.")


if __name__ == "__main__":
    main()

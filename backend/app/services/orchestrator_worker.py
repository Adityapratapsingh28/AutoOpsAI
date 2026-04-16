import asyncio
import json
import logging
from ..core.cache import get_redis
from .orchestrator_service import run_orchestrator

logger = logging.getLogger("autoops.orchestrator_worker")

async def start_worker_loop():
    """
    Continuously poll the Redis queue for new workflows to execute.
    Processes one workflow at a time to prevent server OOM exceptions.
    """
    logger.info("👷 Starting background Redis Queue worker...")
    loop = asyncio.get_running_loop()
    
    while True:
        try:
            client = await get_redis()
            if not client:
                await asyncio.sleep(5)
                continue

            # Block until an item is available
            result = await client.brpop("orchestrator_queue", timeout=5)
            if not result:
                continue

            _, payload_bytes = result
            payload = json.loads(payload_bytes)

            workflow_id = payload.get("workflow_id")
            input_text = payload.get("input_text")
            user_id = payload.get("user_id")
            file_id = payload.get("file_id")

            logger.info(f"👷 Worker picked up workflow {workflow_id}")

            # Execute the orchestrator
            # Since run_orchestrator offloads to to_thread, this awaits the completion
            # safely without blocking other FastAPI concurrent requests.
            await run_orchestrator(workflow_id, input_text, user_id, loop, file_id)
            logger.info(f"👷 Worker finished workflow {workflow_id}")

        except asyncio.CancelledError:
            logger.info("👷 Worker shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"👷 Worker encountered an error: {e}")
            await asyncio.sleep(2)

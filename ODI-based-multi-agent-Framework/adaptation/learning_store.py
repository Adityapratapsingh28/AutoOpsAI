"""
Learning Store — Persistent Policy & Insight Storage for CTDE.

Stores learned policies (best practices, common failures, optimal patterns)
and execution insights in PostgreSQL. Used by the CTDE Coordinator to
persist knowledge across runs and provide guidance to future agents.
"""

import os
import json
import asyncio
import asyncpg
import redis
from typing import Any, Dict, List, Optional
from utils.logger import setup_logger


class LearningStore:
    """Persistent PostgreSQL storage for CTDE policies and execution insights.

    Attributes:
        db_url: PostgreSQL connection string from the environment.
    """

    def __init__(self, db_url: Optional[str] = None):
        """Initialize learning store pointing to PostgreSQL."""
        self.logger = setup_logger("LearningStore")
        
        # In a real environment, .env should set DATABASE_URL
        from dotenv import load_dotenv
        load_dotenv()
        
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            self.logger.warning("DATABASE_URL not found! Governance features disabled.")
            
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2)
            self.redis_client.ping()
            self.logger.info("✅ Redis connected in Learning Store.")
        except Exception as e:
            self.logger.warning(f"⚠️ Redis unavailable in Learning Store: {e}")
            self.redis_client = None

        self.logger.info("Learning Store initialized via PostgreSQL.")

    def _sync_db_call(self, coro):
        """
        Since MetaOrchestrator runs in a background thread, this safely 
        spins up a new event loop to run asyncpg queries synchronously.
        """
        if not self.db_url:
            return None
        return asyncio.run(self._run_async(coro))

    async def _run_async(self, coro):
        conn = await asyncpg.connect(self.db_url)
        try:
            return await coro(conn)
        except Exception as e:
            self.logger.error(f"PostgreSQL Error: {e}")
            return None
        finally:
            await conn.close()

    def store_policy(self, agent_role: str, policy_data: Dict[str, Any]) -> None:
        """Store or update a learned policy for a specific agent role."""
        async def _store(conn):
            for category in ["best_practices", "common_failures", "optimal_patterns"]:
                rules = policy_data.get(category, [])
                for rule in rules:
                    # Insert ignoring duplicates (ON CONFLICT DO NOTHING)
                    await conn.execute("""
                        INSERT INTO agent_policies (agent_role, category, rule_text)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (agent_role, category, rule_text) DO NOTHING
                    """, agent_role, category, rule)
        
        self._sync_db_call(_store)
        
        # Invalidate cache
        if self.redis_client:
            try:
                self.redis_client.delete(f"ctde:{agent_role}")
                self.redis_client.delete("governance:policies")
                self.logger.info(f"[CACHE INVALIDATED] ctde:{agent_role}")
            except Exception as e:
                self.logger.warning(f"Redis cache delete error: {e}")
                
        self.logger.info(f"[LEARNING STORE] Policy updated for role: {agent_role}")

    def get_policy(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Retrieve learned policy for a given agent role."""
        cache_key = f"ctde:{agent_role}"
        
        # Check cache First
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    self.logger.debug(f"[CACHE HIT] {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                self.logger.warning(f"Redis cache get error: {e}")

        async def _get(conn):
            rows = await conn.fetch("""
                SELECT category, rule_text 
                FROM agent_policies 
                WHERE agent_role = $1
            """, agent_role)
            
            if not rows:
                return None
                
            policy = {
                "best_practices": [],
                "common_failures": [],
                "optimal_patterns": []
            }
            
            for row in rows:
                cat = row["category"]
                if cat in policy:
                    policy[cat].append(row["rule_text"])
                    
            return policy
            
        policy = self._sync_db_call(_get)
        
        # Set cache
        if policy and self.redis_client:
            try:
                self.redis_client.setex(cache_key, 600, json.dumps(policy))
                self.logger.info(f"[CACHE SET] {cache_key} (TTL=600s)")
            except Exception as e:
                self.logger.warning(f"Redis cache set error: {e}")
                
        return policy

    def store_insight(self, insight: Dict[str, Any]) -> None:
        """Append an execution insight to the persistent store."""
        insight_json = json.dumps(insight, default=str)
        
        async def _store_insight(conn):
            await conn.execute("""
                INSERT INTO execution_insights (insight_data)
                VALUES ($1)
            """, insight_json)
            
            # Count total
            total = await conn.fetchval("SELECT COUNT(*) FROM execution_insights")
            self.logger.info(f"[LEARNING STORE] New insight stored (total: {total})")
            
        self._sync_db_call(_store_insight)

    def get_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent execution insights."""
        async def _get_insights(conn):
            rows = await conn.fetch("""
                SELECT insight_data 
                FROM execution_insights 
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
            
            return [json.loads(row["insight_data"]) for row in rows]
            
        return self._sync_db_call(_get_insights) or []

    def get_all_policies(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored policies grouped by role."""
        async def _get_all(conn):
            rows = await conn.fetch("SELECT agent_role, category, rule_text FROM agent_policies")
            
            policies = {}
            for row in rows:
                role = row["agent_role"]
                cat = row["category"]
                rule = row["rule_text"]
                
                if role not in policies:
                    policies[role] = {
                        "best_practices": [],
                        "common_failures": [],
                        "optimal_patterns": []
                    }
                if cat in policies[role]:
                    policies[role][cat].append(rule)
                    
            return policies
            
        return self._sync_db_call(_get_all) or {}

    # ─────────────────────────────────────────────
    # GOVERNANCE API METHODS (Backwards Compatibility)
    # The API now uses asyncpg directly, so these are 
    # mostly safely deprecated but left for internal hook compatibility.
    # ─────────────────────────────────────────────
    
    def reload_from_disk(self) -> None:
        self.logger.info("[GOVERNANCE] Connected to active PostgreSQL store. No reload required.")

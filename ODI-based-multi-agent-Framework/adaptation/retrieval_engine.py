from typing import Dict, Any, List, Optional
from memory.vector_store import VectorStore
from utils.logger import setup_logger

class RetrievalEngine:
    """Evaluates semantic similarity to decide between REUSE or GENERATE."""
    
    def __init__(self, vector_store: VectorStore, distance_threshold: float = 1.0):
        # In ChromaDB's default L2 distance, lower is more similar.
        # A distance < threshold means strong semantic match.
        self.vector_store = vector_store
        self.distance_threshold = distance_threshold
        self.logger = setup_logger("RetrievalEngine")

    def evaluate_scenario(self, prompt: str) -> Dict[str, Any]:
        """
        Evaluate if a scenario matches a previous experience well enough to reuse.
        
        Returns:
            dict: {"action": "REUSE" or "GENERATE", "experience": <experience_dict>}
        """
        self.logger.info("Evaluating scenario similarity for workflow reuse...")
        experiences = self.vector_store.retrieve_experiences(prompt, top_k=1)
        
        if not experiences:
            self.logger.info("No past experiences found. Action: GENERATE.")
            return {"action": "GENERATE", "experience": None}
            
        best_match = experiences[0]
        distance = best_match.get("distance", 999.0)
        metadata = best_match.get("metadata", {})
        
        # Adjust distance slightly based on confidence score (penalize if confidence is low)
        confidence = float(metadata.get("confidence_score", 1.0))
        effective_distance = distance / confidence if confidence > 0.01 else 999.0
        
        self.logger.info(
            f"Best match distance: {distance:.2f}, Confidence: {confidence:.2f}, "
            f"Effective distance: {effective_distance:.2f} "
            f"(Threshold: {self.distance_threshold})"
        )
        
        # Check against threshold and ensure it was a successful run
        if effective_distance <= self.distance_threshold and metadata.get("outcome") == "success":
            self.logger.info(f"Match found! Reusing workflow from execution '{best_match['id']}'.")
            return {"action": "REUSE", "experience": best_match}
            
        self.logger.info("Match insufficiently similar or failed previously. Action: GENERATE.")
        return {"action": "GENERATE", "experience": None}

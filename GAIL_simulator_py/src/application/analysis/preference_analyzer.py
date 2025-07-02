# src/application/analysis/preference_analyzer.py
import logging
import numpy as np
from typing import Dict, List, Any, Tuple


class PreferenceAnalyzer:
    """
    Analyzes player preferences for machines based on simulation results.
    """
    def __init__(self):
        """Initialize the preference analyzer."""
        self.logger = logging.getLogger("application.analysis.preference")
        
    def analyze_preferences(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze player preferences from simulation results.
        
        Args:
            simulation_results: Results from simulation coordinator
            
        Returns:
            Dictionary with preference analysis
        """
        self.logger.info("Analyzing player preferences")
        
        # Extract preferences from results
        player_preferences = simulation_results.get("player_preferences", {})
        machine_popularity = simulation_results.get("machine_popularity", {})
        
        # Create analysis result
        analysis = {
            "player_rankings": self._calculate_player_rankings(player_preferences),
            "machine_rankings": self._calculate_machine_rankings(machine_popularity),
            "preference_matrix": player_preferences,
            "popularity_scores": machine_popularity,
            "player_segments": self._identify_player_segments(player_preferences),
            "machine_clusters": self._identify_machine_clusters(player_preferences)
        }
        
        self.logger.info("Preference analysis completed")
        return analysis
    
    def _calculate_player_rankings(self, player_preferences: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """
        Calculate machine rankings for each player.
        
        Args:
            player_preferences: Nested dictionary of player preferences
            
        Returns:
            Dictionary mapping player IDs to lists of ranked machine IDs
        """
        rankings = {}
        
        for player_id, preferences in player_preferences.items():
            # Sort machines by preference score (descending)
            sorted_machines = sorted(
                preferences.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Extract machine IDs
            rankings[player_id] = [machine_id for machine_id, _ in sorted_machines]
            
        return rankings
    
    def _calculate_machine_rankings(self, machine_popularity: Dict[str, float]) -> List[str]:
        """
        Calculate overall machine rankings by popularity.
        
        Args:
            machine_popularity: Dictionary mapping machine IDs to popularity scores
            
        Returns:
            List of machine IDs sorted by popularity
        """
        # Sort machines by popularity score (descending)
        sorted_machines = sorted(
            machine_popularity.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Extract machine IDs
        return [machine_id for machine_id, _ in sorted_machines]
    
    def _identify_player_segments(self, player_preferences: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """
        Identify segments of players with similar preferences.
        
        Args:
            player_preferences: Nested dictionary of player preferences
            
        Returns:
            Dictionary mapping segment IDs to lists of player IDs
        """
        # If not enough players, return a single segment
        if len(player_preferences) <= 1:
            return {"segment_1": list(player_preferences.keys())}
            
        # Convert preferences to numerical vectors
        machine_ids = set()
        for preferences in player_preferences.values():
            machine_ids.update(preferences.keys())
        machine_ids = sorted(machine_ids)
        
        player_vectors = {}
        for player_id, preferences in player_preferences.items():
            vector = [preferences.get(machine_id, 0.5) for machine_id in machine_ids]
            player_vectors[player_id] = vector
            
        # Simple clustering based on preference similarity
        # In a real implementation, this would use a proper clustering algorithm
        segments = {}
        segment_id = 1
        
        # Process each player
        remaining_players = set(player_preferences.keys())
        
        while remaining_players:
            # Pick a player
            current_player = next(iter(remaining_players))
            current_vector = player_vectors[current_player]
            
            # Find players with similar preferences
            segment = [current_player]
            remaining_players.remove(current_player)
            
            # Find similar players
            for player_id in list(remaining_players):
                vector = player_vectors[player_id]
                
                # Calculate similarity (cosine similarity)
                similarity = self._calculate_similarity(current_vector, vector)
                
                # If similar enough, add to segment
                if similarity > 0.7:  # Threshold for similarity
                    segment.append(player_id)
                    remaining_players.remove(player_id)
            
            # Add segment to results
            segments[f"segment_{segment_id}"] = segment
            segment_id += 1
        
        return segments
    
    def _calculate_similarity(self, vector1, vector2) -> float:
        """
        Calculate similarity between two preference vectors.
        
        Args:
            vector1: First preference vector
            vector2: Second preference vector
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not vector1 or not vector2:
            return 0.0
            
        # Convert to numpy arrays
        a = np.array(vector1)
        b = np.array(vector2)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
    
    def _identify_machine_clusters(self, player_preferences: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """
        Identify clusters of machines that appeal to similar players.
        
        Args:
            player_preferences: Nested dictionary of player preferences
            
        Returns:
            Dictionary mapping cluster IDs to lists of machine IDs
        """
        # Get all machine IDs
        machine_ids = set()
        for preferences in player_preferences.values():
            machine_ids.update(preferences.keys())
            
        # If not enough machines, return a single cluster
        if len(machine_ids) <= 1:
            return {"cluster_1": list(machine_ids)}
        
        # Create vectors for each machine (player preferences)
        machine_vectors = {machine_id: [] for machine_id in machine_ids}
        
        for player_id, preferences in player_preferences.items():
            for machine_id, score in preferences.items():
                machine_vectors[machine_id].append(score)
                
        # Ensure all vectors have the same length
        max_length = max(len(v) for v in machine_vectors.values())
        for machine_id in machine_vectors:
            # Fill missing values with 0.5 (neutral preference)
            while len(machine_vectors[machine_id]) < max_length:
                machine_vectors[machine_id].append(0.5)
                
        # Simple clustering based on similarity
        clusters = {}
        cluster_id = 1
        
        # Process each machine
        remaining_machines = set(machine_ids)
        
        while remaining_machines:
            # Pick a machine
            current_machine = next(iter(remaining_machines))
            current_vector = machine_vectors[current_machine]
            
            # Find machines with similar appeal
            cluster = [current_machine]
            remaining_machines.remove(current_machine)
            
            # Find similar machines
            for machine_id in list(remaining_machines):
                vector = machine_vectors[machine_id]
                
                # Calculate similarity
                similarity = self._calculate_similarity(current_vector, vector)
                
                # If similar enough, add to cluster
                if similarity > 0.7:  # Threshold for similarity
                    cluster.append(machine_id)
                    remaining_machines.remove(machine_id)
            
            # Add cluster to results
            clusters[f"cluster_{cluster_id}"] = cluster
            cluster_id += 1
        
        return clusters
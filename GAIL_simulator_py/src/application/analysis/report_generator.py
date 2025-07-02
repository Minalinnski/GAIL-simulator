# src/application/analysis/report_generator.py
import logging
import json
import os
import time
from typing import Dict, List, Any, Optional


class ReportGenerator:
    """
    Generates reports from simulation results and analysis.
    """
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory for storing reports
        """
        self.logger = logging.getLogger("application.analysis.report")
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_summary_report(self, simulation_results: Dict[str, Any], 
                              preference_analysis: Dict[str, Any]) -> str:
        """
        Generate a summary report of simulation results.
        
        Args:
            simulation_results: Results from simulation coordinator
            preference_analysis: Results from preference analyzer
            
        Returns:
            Path to the generated report file
        """
        self.logger.info("Generating summary report")
        
        # Create report data
        report = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "simulation_summary": self._create_simulation_summary(simulation_results),
            "player_preferences": self._create_preference_summary(preference_analysis),
            "machine_popularity": self._create_machine_summary(preference_analysis)
        }
        
        # Generate filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"simulation_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        self.logger.info(f"Summary report saved to {filepath}")
        return filepath
        
    def generate_detailed_report(self, simulation_results: Dict[str, Any],
                               preference_analysis: Dict[str, Any]) -> str:
        """
        Generate a detailed report of simulation results.
        
        Args:
            simulation_results: Results from simulation coordinator
            preference_analysis: Results from preference analyzer
            
        Returns:
            Path to the generated report file
        """
        self.logger.info("Generating detailed report")
        
        # Create report data
        report = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "simulation": {
                "duration": simulation_results.get("duration", 0),
                "player_count": len(simulation_results.get("player_preferences", {})),
                "machine_count": len(simulation_results.get("machine_popularity", {})),
                "session_count": len(simulation_results.get("sessions", [])),
                "start_time": simulation_results.get("start_time"),
                "end_time": simulation_results.get("end_time")
            },
            "sessions": simulation_results.get("sessions", []),
            "player_preferences": simulation_results.get("player_preferences", {}),
            "machine_popularity": simulation_results.get("machine_popularity", {}),
            "player_rankings": preference_analysis.get("player_rankings", {}),
            "machine_rankings": preference_analysis.get("machine_rankings", []),
            "player_segments": preference_analysis.get("player_segments", {}),
            "machine_clusters": preference_analysis.get("machine_clusters", {})
        }
        
        # Generate filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"detailed_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        self.logger.info(f"Detailed report saved to {filepath}")
        return filepath
        
    def _create_simulation_summary(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of simulation results.
        
        Args:
            simulation_results: Results from simulation coordinator
            
        Returns:
            Dictionary with simulation summary
        """
        sessions = simulation_results.get("sessions", [])
        
        # Calculate aggregates
        total_spins = sum(s.get("total_spins", 0) for s in sessions)
        total_bet = sum(s.get("total_bet", 0) for s in sessions)
        total_win = sum(s.get("total_win", 0) for s in sessions)
        
        # Calculate overall RTP (Return to Player)
        overall_rtp = total_win / total_bet if total_bet > 0 else 0
        
        # Calculate average session duration
        durations = [s.get("duration", 0) for s in sessions if "duration" in s]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "session_count": len(sessions),
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "overall_rtp": overall_rtp,
            "average_session_duration": avg_duration,
            "simulation_duration": simulation_results.get("duration", 0)
        }
        
    def _create_preference_summary(self, preference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of player preferences.
        
        Args:
            preference_analysis: Results from preference analyzer
            
        Returns:
            Dictionary with preference summary
        """
        player_rankings = preference_analysis.get("player_rankings", {})
        player_segments = preference_analysis.get("player_segments", {})
        
        return {
            "player_count": len(player_rankings),
            "segment_count": len(player_segments),
            "segments": player_segments,
            "top_choices": {
                player_id: rankings[0] if rankings else None
                for player_id, rankings in player_rankings.items()
            }
        }
        
    def _create_machine_summary(self, preference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of machine popularity.
        
        Args:
            preference_analysis: Results from preference analyzer
            
        Returns:
            Dictionary with machine summary
        """
        machine_rankings = preference_analysis.get("machine_rankings", [])
        machine_clusters = preference_analysis.get("machine_clusters", {})
        
        return {
            "machine_count": len(machine_rankings),
            "cluster_count": len(machine_clusters),
            "clusters": machine_clusters,
            "top_3_machines": machine_rankings[:3] if len(machine_rankings) >= 3 else machine_rankings,
            "least_popular": machine_rankings[-1] if machine_rankings else None
        }
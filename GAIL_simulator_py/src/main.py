# src/main.py
import os
import sys
import logging
import argparse
import time

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from src.infrastructure.config.validators.schema_validator import SchemaValidator
from src.infrastructure.logging.log_manager import initialize_logging
from src.infrastructure.rng.rng_provider import RNGProvider
from src.infrastructure.concurrency.task_executor import TaskExecutor, ExecutionMode

from src.domain.events.event_dispatcher import EventDispatcher

from src.application.registry.registry_service import RegistryService
from src.application.simulation.coordinator import SimulationCoordinator
from src.application.analysis.preference_analyzer import PreferenceAnalyzer
from src.application.analysis.report_generator import ReportGenerator


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Slot Machine Simulator")
    
    parser.add_argument(
        "-c", "--config", 
        default="src/application/config/simulation/default_simulation.yaml",
        help="Path to simulation configuration file"
    )
    
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--no-concurrency",
        action="store_true",
        help="Disable concurrent execution"
    )
    
    parser.add_argument(
        "--log-mode",
        choices=["all", "app", "domain", "none"],
        default=None,
        help="Select logging mode: 'all'=verbose, 'app'=application only, 'domain'=domain only, 'none'=minimal"
    )
    
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=None,
        help="Override max_concurrent_sessions from config"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for slot machine simulator."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Start timing
    start_time = time.time()
    
    # Create config loader and validator
    config_loader = YamlConfigLoader(SchemaValidator())
    
    # Load main configuration
    try:
        config = config_loader.load_file(args.config)
        print(f"Loaded configuration from {args.config}")
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        return 1
    
    # Apply command line overrides to config
    if args.no_concurrency:
        config["use_concurrency"] = False
        print("Concurrency disabled by command line argument")
        
    if args.max_sessions:
        config["max_concurrent_sessions"] = args.max_sessions
        print(f"Max concurrent sessions overridden to: {args.max_sessions}")
    
    # Configure logging based on config file and command line args
    log_config = config.get("logging", {})
    
    # Apply log mode overrides
    if args.log_mode:
        if "loggers" not in log_config:
            log_config["loggers"] = {}
            
        if args.log_mode == "all":
            log_config["level"] = "DEBUG"
            
        elif args.log_mode == "app":
            log_config["level"] = "WARNING"
            log_config["loggers"]["application"] = {"level": "DEBUG", "propagate": False}
            log_config["loggers"]["infrastructure"] = {"level": "DEBUG", "propagate": False}
            log_config["loggers"]["domain"] = {"level": "WARNING", "propagate": False}
            
        elif args.log_mode == "domain":
            log_config["level"] = "WARNING"
            log_config["loggers"]["domain"] = {"level": "DEBUG", "propagate": False}
            log_config["loggers"]["application"] = {"level": "WARNING", "propagate": False}
            log_config["loggers"]["infrastructure"] = {"level": "WARNING", "propagate": False}
            
        elif args.log_mode == "none":
            log_config["level"] = "WARNING"
    
    # Apply verbose flag
    if args.verbose:
        log_config["level"] = "DEBUG"
    
    # Initialize logging
    initialize_logging(log_config)
    logger = logging.getLogger("main")
    
    logger.info("Starting Slot Machine Simulator")
    logger.info(f"Configuration file: {args.config}")
    
    try:
        # Create RNG provider
        rng_provider = RNGProvider()
        logger.info("RNG provider initialized")
        
        # Create event dispatcher
        event_dispatcher = EventDispatcher()
        logger.info("Event dispatcher initialized")
        
        # Create registry service
        registry_service = RegistryService(config_loader, rng_provider)
        logger.info("Registry service initialized")
        
        # Load entities from configuration
        loading_start = time.time()
        loading_results = registry_service.load_from_config(config)
        loading_time = time.time() - loading_start
        
        logger.info(f"Entities loaded in {loading_time:.2f} seconds:")
        logger.info(f"  - {len(loading_results['players'])} players")
        logger.info(f"  - {len(loading_results['machines'])} machines")
        
        # Check if we have entities to simulate
        if not loading_results["machines"] or not loading_results["players"]:
            logger.error("No machines or players loaded, cannot proceed")
            logger.error("Please check your file selection configuration:")
            
            file_configs = config.get("file_configs", {})
            for entity_type, entity_config in file_configs.items():
                selection = entity_config.get("selection", {})
                include_patterns = selection.get("include", [])
                exclude_patterns = selection.get("exclude", [])
                logger.error(f"  {entity_type}: include={include_patterns}, exclude={exclude_patterns}")
            
            return 1
        
        # Create task executor
        execution_mode = ExecutionMode.MULTITHREAD if config.get("use_concurrency", True) else ExecutionMode.SEQUENTIAL
        max_workers = config.get("max_concurrent_sessions", None)
        
        task_executor = TaskExecutor(execution_mode, max_workers=max_workers)
        logger.info(f"Task executor initialized: {execution_mode.name}, max_workers: {max_workers}")
        
        # Create simulation coordinator (修正：使用新的架构)
        coordinator = SimulationCoordinator(
            registry_service=registry_service,  # 修改：传入registry_service而不是分离的registries
            event_dispatcher=event_dispatcher,
            task_executor=task_executor,
            output_config=config.get("output", {})
        )
        logger.info("Simulation coordinator initialized")
        
        # Display instance pool statistics if available
        pool_stats = registry_service.get_pool_stats()
        if pool_stats["players"]["created"] > 0 or pool_stats["machines"]["created"] > 0:
            logger.info("Instance pool statistics:")
            logger.info(f"  - Player instances: {pool_stats['players']['created']} created, {pool_stats['players']['available']} available")
            logger.info(f"  - Machine instances: {pool_stats['machines']['created']} created, {pool_stats['machines']['available']} available")
        
        # Run simulation
        logger.info("Starting simulation")
        simulation_start = time.time()
        simulation_results = coordinator.run_simulation(config)
        simulation_time = time.time() - simulation_start
        logger.info(f"Simulation completed in {simulation_time:.2f} seconds")

        # Display results summary
        total_sessions = len(simulation_results["sessions"])
        total_pairs = len(simulation_results["player_machine_pairs"])
        sessions_per_second = total_sessions / simulation_time if simulation_time > 0 else 0
        
        logger.info("="*60)
        logger.info("SIMULATION COMPLETED")
        logger.info("="*60)
        logger.info(f"Total sessions executed: {total_sessions}")
        logger.info(f"Player-machine pairs: {total_pairs}")
        logger.info(f"Simulation time: {simulation_time:.2f} seconds")
        logger.info(f"Performance: {sessions_per_second:.2f} sessions/second")
        logger.info(f"Output directory: {simulation_results.get('simulation_dir', 'N/A')}")
        
        # Display final instance pool statistics
        final_pool_stats = registry_service.get_pool_stats()
        if final_pool_stats["players"]["borrowed"] > 0 or final_pool_stats["machines"]["borrowed"] > 0:
            logger.info("Final instance pool statistics:")
            logger.info(f"  - Player instances: {final_pool_stats['players']['borrowed']} borrowed, {final_pool_stats['players']['returned']} returned")
            logger.info(f"  - Machine instances: {final_pool_stats['machines']['borrowed']} borrowed, {final_pool_stats['machines']['returned']} returned")
        
        # Calculate and display simulation statistics
        if simulation_results["sessions"]:
            total_spins = sum(s.get("total_spins", 0) for s in simulation_results["sessions"])
            total_bet = sum(s.get("total_bet", 0.0) for s in simulation_results["sessions"])
            total_win = sum(s.get("total_win", 0.0) for s in simulation_results["sessions"])
            overall_rtp = total_win / total_bet if total_bet > 0 else 0.0
            
            logger.info("="*60)
            logger.info("SIMULATION STATISTICS")
            logger.info("="*60)
            logger.info(f"Total spins: {total_spins:,}")
            logger.info(f"Total bet: {total_bet:,.2f}")
            logger.info(f"Total win: {total_win:,.2f}")
            logger.info(f"Overall RTP: {overall_rtp:.4f} ({overall_rtp*100:.2f}%)")
            logger.info(f"Net result: {total_win - total_bet:,.2f}")
        else:
            logger.warning("No sessions completed successfully")
        
        # Analyze results (if we have data to analyze)
        if simulation_results["sessions"]:
            logger.info("Analyzing simulation results")
            preference_analyzer = PreferenceAnalyzer()
            preference_analysis = preference_analyzer.analyze_preferences(simulation_results)
            
            # Generate reports (if enabled in config)
            if config.get("analysis", {}).get("generate_reports", True):
                logger.info("Generating reports")
                output_dir = config.get("analysis", {}).get("output_dir", "reports")
                
                # Ensure reports directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                report_generator = ReportGenerator(output_dir)
                
                # Generate summary report
                try:
                    summary_path = report_generator.generate_summary_report(
                        simulation_results, preference_analysis
                    )
                    logger.info(f"Summary report generated: {summary_path}")
                except Exception as e:
                    logger.error(f"Failed to generate summary report: {e}")
                
                # Generate detailed report if requested
                if config.get("analysis", {}).get("include", {}).get("detailed_session_report", False):
                    try:
                        detailed_path = report_generator.generate_detailed_report(
                            simulation_results, preference_analysis
                        )
                        logger.info(f"Detailed report generated: {detailed_path}")
                    except Exception as e:
                        logger.error(f"Failed to generate detailed report: {e}")
        
        # Calculate total runtime
        total_time = time.time() - start_time
        logger.info("="*60)
        logger.info(f"Total runtime: {total_time:.2f} seconds")
        logger.info("Simulation completed successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
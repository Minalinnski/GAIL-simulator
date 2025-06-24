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
    
    # 添加简单的日志模式选择
    parser.add_argument(
        "--log-mode",
        choices=["all", "app", "domain", "none"],
        default=None,
        help="Select logging mode: 'all'=verbose, 'app'=application only, 'domain'=domain only, 'none'=minimal"
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
    
    # 应用日志模式
    if args.log_mode:
        log_config = config.get("logging", {})
        
        if "loggers" not in log_config:
            log_config["loggers"] = {}
            
        if args.log_mode == "all":
            # 显示所有详细日志
            log_config["level"] = "DEBUG"
            log_config["console_level"] = "DEBUG"
            
        elif args.log_mode == "app":
            # 只显示 application 层日志
            log_config["level"] = "WARNING"  # 默认级别设为 WARNING
            log_config["loggers"]["domain"] = {"level": "WARNING", "propagate": False}
            log_config["loggers"]["application"] = {"level": "DEBUG", "propagate": False}
            log_config["loggers"]["infrastructure"] = {"level": "WARNING", "propagate": False}
            
        elif args.log_mode == "domain":
            # 只显示 domain 层日志
            log_config["level"] = "WARNING"  # 默认级别设为 WARNING
            log_config["loggers"]["domain"] = {"level": "DEBUG", "propagate": False}
            log_config["loggers"]["application"] = {"level": "WARNING", "propagate": False}
            log_config["loggers"]["infrastructure"] = {"level": "WARNING", "propagate": False}
            
        elif args.log_mode == "none":
            # 最小化日志输出（只显示警告和错误）
            log_config["level"] = "WARNING"
            log_config["console_level"] = "WARNING"
        
        # 更新配置中的 logging 部分
        config["logging"] = log_config
    
    # 如果指定了 verbose，覆盖其他设置
    if args.verbose:
        if "logging" not in config:
            config["logging"] = {}
        config["logging"]["level"] = "DEBUG"
        config["logging"]["console_level"] = "DEBUG"
    
    # Initialize logging
    log_manager = initialize_logging(config.get("logging", {}))
    logger = logging.getLogger("main")
    logger.info("Slot Machine Simulator starting")
    
    # Initialize RNG provider
    rng_config = config.get("rng", {})
    rng_provider = RNGProvider()
    
    # Initialize event system
    event_dispatcher = EventDispatcher()
    
    # Create task executor with appropriate mode
    if args.no_concurrency:
        execution_mode = ExecutionMode.SEQUENTIAL
    else:
        execution_mode = ExecutionMode.THREADED
        
    task_executor = TaskExecutor(execution_mode)
    
    try:
        # Initialize registry service
        logger.info("Initializing entity registries")
        registry_service = RegistryService(config_loader, rng_provider)
        
        # Load entities from configuration
        logger.info("Loading entities")
        loading_results = registry_service.load_from_config(config)
        
        # Check if we have entities to simulate
        if not loading_results["machines"] or not loading_results["players"]:
            logger.error("No machines or players loaded, cannot proceed")
            return 1
            
        logger.info(f"Loaded {len(loading_results['machines'])} machines and "
                  f"{len(loading_results['players'])} players")
                  
        # Create simulation coordinator
        coordinator = SimulationCoordinator(
            registry_service.machine_registry,
            registry_service.player_registry,
            event_dispatcher,
            task_executor
        )
        
        # Run simulation
        logger.info("Starting simulation")
        simulation_results = coordinator.run_simulation(config)
        logger.info("Simulation completed")
        
        # Analyze results
        logger.info("Analyzing simulation results")
        preference_analyzer = PreferenceAnalyzer()
        preference_analysis = preference_analyzer.analyze_preferences(simulation_results)
        
        # Generate reports
        if config.get("analysis", {}).get("generate_reports", True):
            logger.info("Generating reports")
            output_dir = config.get("analysis", {}).get("output_dir", "reports")
            report_generator = ReportGenerator(output_dir)
            
            # Generate summary report
            summary_path = report_generator.generate_summary_report(
                simulation_results, preference_analysis
            )
            logger.info(f"Summary report saved to {summary_path}")
            
            # Generate detailed report
            detailed_path = report_generator.generate_detailed_report(
                simulation_results, preference_analysis
            )
            logger.info(f"Detailed report saved to {detailed_path}")
            
        # Show summary
        print("\nSimulation Summary:")
        print(f"- Machines: {len(loading_results['machines'])}")
        print(f"- Players: {len(loading_results['players'])}")
        print(f"- Total Sessions: {len(simulation_results['sessions'])}")
        
        # Calculate totals
        total_spins = sum(s.get("total_spins", 0) for s in simulation_results["sessions"])
        # total_bet = sum(s.get("total_bet", 0) for s in simulation_results["sessions"])
        # total_win = sum(s.get("total_win", 0) for s in simulation_results["sessions"])
        # overall_rtp = total_win / total_bet if total_bet > 0 else 0
        
        print(f"- Total Spins: {total_spins}")
        # print(f"- Total Bet: {total_bet:.2f}")
        # print(f"- Total Win: {total_win:.2f}")
        # print(f"- Overall RTP: {overall_rtp:.2%}")
        
        # Show most popular machines
        if preference_analysis.get("machine_rankings"):
            top_machines = preference_analysis["machine_rankings"][:3]
            print("\nMost Popular Machines:")
            for i, machine_id in enumerate(top_machines):
                popularity = simulation_results.get("machine_popularity", {}).get(machine_id, 0)
                print(f"{i+1}. {machine_id} (Popularity: {popularity:.2f})")
        
        # Show elapsed time
        elapsed_time = time.time() - start_time
        print(f"\nTotal execution time: {elapsed_time:.2f} seconds")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Error during simulation: {str(e)}")
        return 1
    finally:
        logging.shutdown()


if __name__ == "__main__":
    sys.exit(main())
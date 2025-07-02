// src/main.cpp
#include "simulation_engine.h"
#include "utils/logger.h"
#include <iostream>
#include <string>
#include <filesystem>

using namespace SlotSimulator;

void PrintUsage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [options]\n"
              << "Options:\n"
              << "  -c, --config <file>    Simulation config file (default: config/simulation.yaml)\n"
              << "  -t, --threads <num>    Number of threads (default: auto-detect)\n"
              << "  -v, --verbose          Enable verbose logging\n"
              << "  -h, --help            Show this help message\n"
              << "  --log-file <file>     Log file path (default: logs/simulator.log)\n"
              << "  --no-console          Disable console output\n";
}

int main(int argc, char* argv[]) {
    // 默认参数
    std::string config_file = "config/simulation.yaml";
    std::string log_file = "logs/simulator.log";
    int thread_count = 0;  // 0表示自动检测
    bool verbose = false;
    bool enable_console = true;
    
    // 解析命令行参数
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            PrintUsage(argv[0]);
            return 0;
        } else if (arg == "-c" || arg == "--config") {
            if (i + 1 < argc) {
                config_file = argv[++i];
            } else {
                std::cerr << "Error: " << arg << " requires a filename\n";
                return 1;
            }
        } else if (arg == "-t" || arg == "--threads") {
            if (i + 1 < argc) {
                thread_count = std::stoi(argv[++i]);
            } else {
                std::cerr << "Error: " << arg << " requires a number\n";
                return 1;
            }
        } else if (arg == "--log-file") {
            if (i + 1 < argc) {
                log_file = argv[++i];
            } else {
                std::cerr << "Error: " << arg << " requires a filename\n";
                return 1;
            }
        } else if (arg == "-v" || arg == "--verbose") {
            verbose = true;
        } else if (arg == "--no-console") {
            enable_console = false;
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            PrintUsage(argv[0]);
            return 1;
        }
    }
    
    // 检查配置文件是否存在
    if (!std::filesystem::exists(config_file)) {
        std::cerr << "Configuration file not found: " << config_file << "\n";
        return 1;
    }
    
    // 初始化日志系统
    LogLevel console_level = verbose ? LogLevel::DEBUG : LogLevel::INFO;
    LogLevel file_level = LogLevel::DEBUG;
    
    Logger::GetInstance().Initialize(log_file, console_level, file_level, 
                                   enable_console, true);
    
    LOG_INFO("Slot Machine Simulator Starting", "Main");
    LOG_INFO("Config file: " + config_file, "Main");
    LOG_INFO("Thread count: " + (thread_count > 0 ? std::to_string(thread_count) : "auto"), "Main");
    
    try {
        // 创建模拟引擎
        SimulationEngine engine;
        
        // 运行模拟
        bool success = engine.Run(config_file, thread_count);
        
        if (success) {
            LOG_INFO("Simulation completed successfully", "Main");
            return 0;
        } else {
            LOG_ERROR("Simulation failed", "Main");
            return 1;
        }
        
    } catch (const std::exception& e) {
        LOG_ERROR("Fatal error: " + std::string(e.what()), "Main");
        return 1;
    }
}
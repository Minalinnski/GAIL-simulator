// src/simulation_engine.cpp
#include "simulation_engine.h"
#include "utils/logger.h"
#include <chrono>
#include <filesystem>

namespace SlotSimulator {

SimulationEngine::SimulationEngine() {
    LOG_DEBUG("SimulationEngine created", "SimulationEngine");
}

SimulationEngine::~SimulationEngine() {
    Cleanup();
    LOG_DEBUG("SimulationEngine destroyed", "SimulationEngine");
}

bool SimulationEngine::Run(const std::string& config_path, int thread_count) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    LOG_INFO("Starting simulation with config: " + config_path, "SimulationEngine");
    
    // 初始化
    if (!Initialize(config_path, thread_count)) {
        LOG_ERROR("Failed to initialize simulation engine", "SimulationEngine");
        return false;
    }
    
    // 生成任务
    auto tasks = GenerateTasks();
    if (tasks.empty()) {
        LOG_ERROR("No tasks generated", "SimulationEngine");
        return false;
    }
    
    stats_.total_tasks = static_cast<int>(tasks.size());
    stats_.total_sessions = 0;
    for (const auto& task : tasks) {
        stats_.total_sessions += task.session_count;
    }
    
    LOG_INFO("Generated " + std::to_string(tasks.size()) + " tasks covering " +
             std::to_string(stats_.total_sessions) + " sessions", "SimulationEngine");
    
    // 执行模拟
    bool success = ExecuteSimulation(tasks);
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    stats_.total_execution_time = duration.count() / 1000.0;
    stats_.success = success;
    
    LOG_INFO("Simulation completed in " + std::to_string(stats_.total_execution_time) + 
             " seconds. Success: " + (success ? "true" : "false"), "SimulationEngine");
    
    return success;
}

bool SimulationEngine::Initialize(const std::string& config_path, int thread_count) {
    try {
        // 创建配置管理器
        config_manager_ = std::make_unique<ConfigManager>();
        
        // 加载配置
        if (!config_manager_->LoadSimulationConfig(config_path)) {
            return false;
        }
        
        if (!LoadConfigurations()) {
            return false;
        }
        
        // 创建工厂
        machine_factory_ = std::make_shared<MachineFactory>();
        player_factory_ = std::make_shared<PlayerFactory>();
        
        if (!RegisterFactories()) {
            return false;
        }
        
        // 使用配置文件中的线程数，如果命令行没有指定的话
        const auto& sim_config = config_manager_->GetSimulationConfig();
        if (thread_count <= 0) {
            thread_count = sim_config.use_concurrency ? sim_config.thread_count : 1;
        }
        
        // 创建任务分发器
        task_distributor_ = std::make_unique<TaskDistributor>(
            machine_factory_, player_factory_, thread_count);
        
        // 创建数据写入器
        data_writer_ = std::make_unique<DataWriter>(sim_config);
        
        // 验证配置
        if (!ValidateConfiguration()) {
            return false;
        }
        
        LOG_INFO("SimulationEngine initialized successfully", "SimulationEngine");
        return true;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Exception during initialization: " + std::string(e.what()), "SimulationEngine");
        return false;
    }
}

bool SimulationEngine::LoadConfigurations() {
    LOG_INFO("Loading machine and player configurations", "SimulationEngine");
    
    if (!config_manager_->LoadMachineConfigs()) {
        LOG_ERROR("Failed to load machine configurations", "SimulationEngine");
        return false;
    }
    
    if (!config_manager_->LoadPlayerConfigs()) {
        LOG_ERROR("Failed to load player configurations", "SimulationEngine");
        return false;
    }
    
    const auto& machine_configs = config_manager_->GetMachineConfigs();
    const auto& player_configs = config_manager_->GetPlayerConfigs();
    
    stats_.total_machines = static_cast<int>(machine_configs.size());
    stats_.total_player_types = static_cast<int>(player_configs.size());
    
    LOG_INFO("Loaded " + std::to_string(stats_.total_machines) + " machines and " +
             std::to_string(stats_.total_player_types) + " player types", "SimulationEngine");
    
    return true;
}

bool SimulationEngine::RegisterFactories() {
    LOG_INFO("Registering machine and player configurations with factories", "SimulationEngine");
    
    // 注册机器配置
    const auto& machine_configs = config_manager_->GetMachineConfigs();
    for (const auto& config : machine_configs) {
        machine_factory_->RegisterMachine(config);
    }
    
    // 注册玩家配置
    const auto& player_configs = config_manager_->GetPlayerConfigs();
    for (const auto& config : player_configs) {
        player_factory_->RegisterPlayer(config);
    }
    
    LOG_INFO("Factory registration completed", "SimulationEngine");
    return true;
}

bool SimulationEngine::ValidateConfiguration() {
    LOG_INFO("Validating configuration", "SimulationEngine");
    
    const auto& machine_configs = config_manager_->GetMachineConfigs();
    const auto& player_configs = config_manager_->GetPlayerConfigs();
    
    if (machine_configs.empty()) {
        LOG_ERROR("No machine configurations loaded", "SimulationEngine");
        return false;
    }
    
    if (player_configs.empty()) {
        LOG_ERROR("No player configurations loaded", "SimulationEngine");
        return false;
    }
    
    // 验证每个机器配置
    for (const auto& config : machine_configs) {
        if (!machine_factory_->IsRegistered(config.machine_id)) {
            LOG_ERROR("Machine not registered: " + config.machine_id, "SimulationEngine");
            return false;
        }
    }
    
    // 验证每个玩家配置
    for (const auto& config : player_configs) {
        if (!player_factory_->IsRegistered(config.model_version, config.cluster_id)) {
            LOG_ERROR("Player not registered: " + config.model_version + "/" + config.cluster_id, 
                     "SimulationEngine");
            return false;
        }
    }
    
    LOG_INFO("Configuration validation passed", "SimulationEngine");
    return true;
}

std::vector<TaskInfo> SimulationEngine::GenerateTasks() {
    const auto& machine_configs = config_manager_->GetMachineConfigs();
    const auto& player_configs = config_manager_->GetPlayerConfigs();
    const auto& sim_config = config_manager_->GetSimulationConfig();
    
    return task_distributor_->GenerateTasks(machine_configs, player_configs, 
                                          sim_config.sessions_per_pair);
}

bool SimulationEngine::ExecuteSimulation(const std::vector<TaskInfo>& tasks) {
    LOG_INFO("Starting task execution", "SimulationEngine");
    
    const auto& sim_config = config_manager_->GetSimulationConfig();
    auto results = task_distributor_->ExecuteTasks(tasks, sim_config);
    
    // 保存结果
    if (!SaveResults(results)) {
        LOG_ERROR("Failed to save simulation results", "SimulationEngine");
        return false;
    }
    
    // 打印统计信息
    auto distributor_stats = task_distributor_->GetStats();
    LOG_INFO("Task execution stats - Completed: " + 
             std::to_string(distributor_stats.completed_tasks) + 
             ", Failed: " + std::to_string(distributor_stats.failed_tasks), "SimulationEngine");
    
    return distributor_stats.failed_tasks == 0;
}

bool SimulationEngine::SaveResults(const std::vector<TaskResult>& results) {
    LOG_INFO("Saving simulation results", "SimulationEngine");
    
    try {
        // 收集所有session结果
        std::vector<SessionStats> all_sessions;
        for (const auto& task_result : results) {
            if (task_result.success) {
                all_sessions.insert(all_sessions.end(),
                                  task_result.session_results.begin(),
                                  task_result.session_results.end());
            }
        }
        
        // 写入数据
        data_writer_->WriteSessionStats(all_sessions);
        data_writer_->GenerateSummaryReport(all_sessions);
        
        LOG_INFO("Saved " + std::to_string(all_sessions.size()) + " session results", 
                "SimulationEngine");
        return true;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Exception while saving results: " + std::string(e.what()), "SimulationEngine");
        return false;
    }
}

void SimulationEngine::Cleanup() {
    LOG_DEBUG("Cleaning up SimulationEngine", "SimulationEngine");
    
    data_writer_.reset();
    task_distributor_.reset();
    player_factory_.reset();
    machine_factory_.reset();
    config_manager_.reset();
}

} // namespace SlotSimulator
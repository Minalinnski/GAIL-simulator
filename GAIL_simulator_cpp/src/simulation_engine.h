// src/simulation_engine.h
#pragma once

#include "core/types.h"
#include "core/config.h"
#include "core/task_distributor.h"
#include "machines/machine_factory.h"
#include "players/player_factory.h"
#include "core/data_writer.h"
#include <memory>
#include <string>

namespace SlotSimulator {

class SimulationEngine {
public:
    SimulationEngine();
    ~SimulationEngine();
    
    // 运行模拟
    bool Run(const std::string& config_path, int thread_count = 0);
    
    // 获取运行统计
    struct SimulationStats {
        int total_machines;
        int total_player_types;
        int total_tasks;
        int total_sessions;
        double total_execution_time;
        bool success;
    };
    
    SimulationStats GetStats() const { return stats_; }

private:
    // 核心组件
    std::unique_ptr<ConfigManager> config_manager_;
    std::shared_ptr<MachineFactory> machine_factory_;
    std::shared_ptr<PlayerFactory> player_factory_;
    std::unique_ptr<TaskDistributor> task_distributor_;
    std::unique_ptr<DataWriter> data_writer_;
    
    SimulationStats stats_;
    
    // 初始化方法
    bool Initialize(const std::string& config_path, int thread_count);
    bool LoadConfigurations();
    bool RegisterFactories();
    bool ValidateConfiguration();
    
    // 执行方法
    std::vector<TaskInfo> GenerateTasks();
    bool ExecuteSimulation(const std::vector<TaskInfo>& tasks);
    bool SaveResults(const std::vector<TaskResult>& results);
    
    // 清理方法
    void Cleanup();
};

} // namespace SlotSimulator
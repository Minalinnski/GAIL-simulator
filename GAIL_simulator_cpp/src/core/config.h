// src/core/config.h
#pragma once

#include "types.h"
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <thread>

namespace SlotSimulator {

class ConfigManager {
public:
    ConfigManager() = default;
    ~ConfigManager() = default;

    // 加载主模拟配置
    bool LoadSimulationConfig(const std::string& config_path);
    
    // 加载所有机器配置
    bool LoadMachineConfigs();
    
    // 加载所有玩家配置  
    bool LoadPlayerConfigs();
    
    // 获取配置
    const SimulationConfig& GetSimulationConfig() const { return simulation_config_; }
    const std::vector<MachineConfig>& GetMachineConfigs() const { return machine_configs_; }
    const std::vector<PlayerConfig>& GetPlayerConfigs() const { return player_configs_; }
    
    // 根据ID获取特定配置
    const MachineConfig* GetMachineConfig(const std::string& machine_id) const;
    const PlayerConfig* GetPlayerConfig(const std::string& player_version, 
                                      const std::string& cluster_id) const;

private:
    SimulationConfig simulation_config_;
    std::vector<MachineConfig> machine_configs_;
    std::vector<PlayerConfig> player_configs_;
    
    // 辅助方法
    bool LoadMachineConfig(const std::string& file_path, MachineConfig& config);
    bool LoadPlayerConfig(const std::string& file_path, PlayerConfig& config);
    std::vector<std::string> GetConfigFiles(const SimulationConfig::FileConfig& file_config);
    
    // YAML解析辅助方法
    void ParseReelsConfig(const YAML::Node& reels_node, MachineConfig& config);
    void ParsePaylinesConfig(const YAML::Node& paylines_node, MachineConfig& config);
    void ParsePayTableConfig(const YAML::Node& pay_table_node, MachineConfig& config);
    void ParseBetTableConfig(const YAML::Node& bet_table_node, MachineConfig& config);
};

} // namespace SlotSimulator
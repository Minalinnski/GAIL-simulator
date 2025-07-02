// src/core/config.cpp
#include "config.h"
#include <filesystem>
#include <iostream>
#include <algorithm>

namespace SlotSimulator {

bool ConfigManager::LoadSimulationConfig(const std::string& config_path) {
    try {
        YAML::Node root = YAML::LoadFile(config_path);
        
        // 解析文件配置
        if (root["file_configs"]) {
            auto file_configs = root["file_configs"];
            
            if (file_configs["machines"]) {
                auto machines = file_configs["machines"];
                simulation_config_.machines_config.directory = 
                    machines["dir"].as<std::string>("config/machines");
                simulation_config_.machines_config.selection_mode = 
                    machines["selection"]["mode"].as<std::string>("all");
                
                if (machines["selection"]["files"]) {
                    for (const auto& file : machines["selection"]["files"]) {
                        simulation_config_.machines_config.files.push_back(file.as<std::string>());
                    }
                }
            }
            
            if (file_configs["players"]) {
                auto players = file_configs["players"];
                simulation_config_.players_config.directory = 
                    players["dir"].as<std::string>("config/players");
                simulation_config_.players_config.selection_mode = 
                    players["selection"]["mode"].as<std::string>("all");
                
                if (players["selection"]["files"]) {
                    for (const auto& file : players["selection"]["files"]) {
                        simulation_config_.players_config.files.push_back(file.as<std::string>());
                    }
                }
            }
        }
        
        // 解析模拟参数
        simulation_config_.sessions_per_pair = root["sessions_per_pair"].as<int>(100);
        simulation_config_.max_spins_per_session = root["max_spins"].as<int>(10000);
        simulation_config_.max_session_duration = root["max_sim_duration"].as<float>(300.0f);
        simulation_config_.use_concurrency = root["use_concurrency"].as<bool>(true);
        simulation_config_.thread_count = root["thread_count"].as<int>(
            std::thread::hardware_concurrency());
        
        // 解析输出配置
        if (root["output"]) {
            auto output = root["output"];
            simulation_config_.output_base_dir = 
                output["directories"]["base_dir"].as<std::string>("results");
            simulation_config_.record_raw_spins = 
                output["session_recording"]["enabled"].as<bool>(true);
            simulation_config_.generate_reports = 
                output["reports"]["generate_reports"].as<bool>(true);
            simulation_config_.batch_write_size = 
                output["batch_write_size"].as<int>(100);
        }
        
        // S3配置（可选）
        if (root["s3"]) {
            simulation_config_.enable_s3_upload = root["s3"]["enabled"].as<bool>(false);
            simulation_config_.s3_bucket = root["s3"]["bucket"].as<std::string>("");
        }
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Failed to load simulation config: " << e.what() << std::endl;
        return false;
    }
}

bool ConfigManager::LoadMachineConfigs() {
    auto config_files = GetConfigFiles(simulation_config_.machines_config);
    
    for (const auto& file_path : config_files) {
        MachineConfig config;
        if (LoadMachineConfig(file_path, config)) {
            machine_configs_.push_back(std::move(config));
        } else {
            std::cerr << "Failed to load machine config: " << file_path << std::endl;
            return false;
        }
    }
    
    std::cout << "Loaded " << machine_configs_.size() << " machine configurations" << std::endl;
    return !machine_configs_.empty();
}

bool ConfigManager::LoadPlayerConfigs() {
    auto config_files = GetConfigFiles(simulation_config_.players_config);
    
    for (const auto& file_path : config_files) {
        PlayerConfig config;
        if (LoadPlayerConfig(file_path, config)) {
            player_configs_.push_back(std::move(config));
        } else {
            std::cerr << "Failed to load player config: " << file_path << std::endl;
            return false;
        }
    }
    
    std::cout << "Loaded " << player_configs_.size() << " player configurations" << std::endl;
    return !player_configs_.empty();
}

bool ConfigManager::LoadMachineConfig(const std::string& file_path, MachineConfig& config) {
    try {
        YAML::Node root = YAML::LoadFile(file_path);
        
        config.machine_id = root["machine_id"].as<std::string>();
        config.window_size = root["window_size"].as<int>(3);
        config.num_reels = root["num_reels"].as<int>(5);
        config.free_spins_count = root["free_spins"].as<int>(10);
        config.free_spins_multiplier = root["free_spins_multiplier"].as<float>(2.0f);
        config.scatter_symbol = root["scatter_symbol"].as<int>(20);
        
        // 解析符号配置
        if (root["symbols"]) {
            auto symbols = root["symbols"];
            if (symbols["normal"]) {
                for (const auto& symbol : symbols["normal"]) {
                    config.normal_symbols.push_back(symbol.as<int>());
                }
            }
            if (symbols["wild"]) {
                for (const auto& wild : symbols["wild"]) {
                    config.wild_symbols.push_back(wild.as<int>());
                }
            }
            if (symbols["scatter"]) {
                config.scatter_symbol = symbols["scatter"].as<int>();
            }
        }
        
        // 兼容旧格式的wild_symbol字段
        if (root["wild_symbol"]) {
            for (const auto& wild : root["wild_symbol"]) {
                config.wild_symbols.push_back(wild.as<int>());
            }
        }
        
        // 解析各个部分
        ParseReelsConfig(root["reels"], config);
        ParsePaylinesConfig(root["paylines"], config);
        ParsePayTableConfig(root["pay_table"], config);
        ParseBetTableConfig(root["bet_table"], config);
        
        // 计算active_lines（使用paylines数量）
        config.active_lines = static_cast<int>(config.paylines.size());
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error parsing machine config " << file_path << ": " << e.what() << std::endl;
        return false;
    }
}

bool ConfigManager::LoadPlayerConfig(const std::string& file_path, PlayerConfig& config) {
    try {
        YAML::Node root = YAML::LoadFile(file_path);
        
        config.player_id = root["player_id"].as<std::string>();
        config.model_version = root["model_version"].as<std::string>("random");
        config.currency = root["currency"].as<std::string>("USD");
        config.active_lines = root["active_lines"].as<int>(25);
        
        // 解析cluster_id（可能在model_config中）
        if (root["cluster_id"]) {
            config.cluster_id = root["cluster_id"].as<std::string>("cluster_0");
        } else if (root["model_config_" + config.model_version] && 
                   root["model_config_" + config.model_version]["cluster_id"]) {
            config.cluster_id = root["model_config_" + config.model_version]["cluster_id"].as<std::string>("cluster_0");
        }
        
        // 解析initial_balance（支持分布配置和简单值）
        if (root["initial_balance"]) {
            auto balance_node = root["initial_balance"];
            if (balance_node.IsMap()) {
                // 分布配置
                config.initial_balance.avg = balance_node["avg"].as<float>(1000.0f);
                config.initial_balance.std = balance_node["std"].as<float>(0.0f);
                config.initial_balance.min = balance_node["min"].as<float>(100.0f);
                config.initial_balance.max = balance_node["max"].as<float>(10000.0f);
            } else {
                // 简单值
                float balance = balance_node.as<float>(1000.0f);
                config.initial_balance.avg = balance;
                config.initial_balance.std = 0.0f;
                config.initial_balance.min = balance;
                config.initial_balance.max = balance;
            }
        }
        
        // 解析模型特定配置
        std::string model_config_key = "model_config_" + config.model_version;
        if (root[model_config_key]) {
            auto model_config_node = root[model_config_key];
            for (auto it = model_config_node.begin(); it != model_config_node.end(); ++it) {
                std::string key = it->first.as<std::string>();
                std::string value;
                
                if (it->second.IsScalar()) {
                    value = it->second.as<std::string>();
                } else if (it->second.IsMap()) {
                    // 对于嵌套配置，序列化为字符串
                    YAML::Emitter emitter;
                    emitter << it->second;
                    value = emitter.c_str();
                } else {
                    value = it->second.as<std::string>();
                }
                
                config.model_configs[config.model_version][key] = value;
            }
        }
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error parsing player config " << file_path << ": " << e.what() << std::endl;
        return false;
    }
}

std::vector<std::string> ConfigManager::GetConfigFiles(
    const SimulationConfig::FileConfig& file_config) {
    
    std::vector<std::string> result;
    std::string dir = file_config.directory;
    
    if (!std::filesystem::exists(dir)) {
        std::cerr << "Config directory does not exist: " << dir << std::endl;
        return result;
    }
    
    // 获取目录中的所有yaml文件
    std::vector<std::string> all_files;
    for (const auto& entry : std::filesystem::directory_iterator(dir)) {
        if (entry.is_regular_file() && 
            (entry.path().extension() == ".yaml" || entry.path().extension() == ".yml")) {
            all_files.push_back(entry.path().string());
        }
    }
    
    // 根据selection_mode过滤文件
    if (file_config.selection_mode == "all") {
        result = all_files;
    } else if (file_config.selection_mode == "include") {
        for (const auto& file : file_config.files) {
            std::string full_path = dir + "/" + file;
            if (std::find(all_files.begin(), all_files.end(), full_path) != all_files.end()) {
                result.push_back(full_path);
            }
        }
    } else if (file_config.selection_mode == "exclude") {
        for (const auto& file_path : all_files) {
            std::string filename = std::filesystem::path(file_path).filename().string();
            if (std::find(file_config.files.begin(), file_config.files.end(), filename) 
                == file_config.files.end()) {
                result.push_back(file_path);
            }
        }
    }
    
    return result;
}

void ConfigManager::ParseReelsConfig(const YAML::Node& reels_node, MachineConfig& config) {
    for (auto reel_set_it = reels_node.begin(); reel_set_it != reels_node.end(); ++reel_set_it) {
        std::string reel_set_name = reel_set_it->first.as<std::string>();  // "normal" or "bonus"
        auto reel_set = reel_set_it->second;
        
        for (auto reel_it = reel_set.begin(); reel_it != reel_set.end(); ++reel_it) {
            std::string reel_name = reel_it->first.as<std::string>();  // "reel1", "reel2", etc.
            auto symbols = reel_it->second;
            
            std::vector<int> reel_symbols;
            for (const auto& symbol : symbols) {
                reel_symbols.push_back(symbol.as<int>());
            }
            
            config.reels[reel_set_name][reel_name] = std::move(reel_symbols);
        }
    }
}

void ConfigManager::ParsePaylinesConfig(const YAML::Node& paylines_node, MachineConfig& config) {
    for (const auto& payline : paylines_node) {
        PaylineIndices indices;
        for (const auto& index : payline["indices"]) {
            indices.push_back(index.as<int>());
        }
        config.paylines.push_back(std::move(indices));
    }
}

void ConfigManager::ParsePayTableConfig(const YAML::Node& pay_table_node, MachineConfig& config) {
    for (const auto& entry : pay_table_node) {
        std::string symbol = entry["symbol"].as<std::string>();
        PayoutArray payouts;
        for (const auto& payout : entry["payouts"]) {
            payouts.push_back(payout.as<float>());
        }
        config.pay_table[symbol] = std::move(payouts);
    }
}

void ConfigManager::ParseBetTableConfig(const YAML::Node& bet_table_node, MachineConfig& config) {
    for (const auto& entry : bet_table_node) {
        std::string currency = entry["currency"].as<std::string>();
        BetOptions bet_options;
        for (const auto& bet : entry["bet_options"]) {
            bet_options.push_back(bet.as<float>());
        }
        config.bet_table[currency] = std::move(bet_options);
    }
}

const MachineConfig* ConfigManager::GetMachineConfig(const std::string& machine_id) const {
    for (const auto& config : machine_configs_) {
        if (config.machine_id == machine_id) {
            return &config;
        }
    }
    return nullptr;
}

const PlayerConfig* ConfigManager::GetPlayerConfig(const std::string& player_version, 
                                                 const std::string& cluster_id) const {
    for (const auto& config : player_configs_) {
        if (config.model_version == player_version && config.cluster_id == cluster_id) {
            return &config;
        }
    }
    return nullptr;
}

} // namespace SlotSimulator
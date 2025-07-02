// src/players/player_factory.h
#pragma once

#include "player_interface.h"
#include "../core/types.h"
#include <memory>
#include <unordered_map>
#include <string>

namespace SlotSimulator {

class PlayerFactory {
public:
    PlayerFactory() = default;
    ~PlayerFactory() = default;
    
    // 注册玩家配置
    void RegisterPlayer(const PlayerConfig& config);
    
    // 创建玩家实例
    std::unique_ptr<PlayerInterface> CreatePlayer(const std::string& model_version, 
                                                 const std::string& cluster_id) const;
    
    // 获取已注册的玩家类型
    std::vector<std::pair<std::string, std::string>> GetRegisteredPlayers() const;
    
    // 检查玩家类型是否已注册
    bool IsRegistered(const std::string& model_version, const std::string& cluster_id) const;

private:
    // 使用 version_cluster 作为key
    std::unordered_map<std::string, PlayerConfig> player_configs_;
    
    std::string MakeKey(const std::string& model_version, const std::string& cluster_id) const;
};

} // namespace SlotSimulator
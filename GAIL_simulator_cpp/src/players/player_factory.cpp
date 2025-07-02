// src/players/player_factory.cpp
#include "player_factory.h"
#include "models/random/random_player.h"
#include "models/v1/v1_player.h"
#include "../utils/logger.h"

namespace SlotSimulator {

std::string PlayerFactory::MakeKey(const std::string& model_version, 
                                  const std::string& cluster_id) const {
    return model_version + "_" + cluster_id;
}

void PlayerFactory::RegisterPlayer(const PlayerConfig& config) {
    std::string key = MakeKey(config.model_version, config.cluster_id);
    player_configs_[key] = config;
    LOG_INFO("Registered player: " + config.model_version + "/" + config.cluster_id, 
             "PlayerFactory");
}

std::unique_ptr<PlayerInterface> PlayerFactory::CreatePlayer(
    const std::string& model_version, const std::string& cluster_id) const {
    
    std::string key = MakeKey(model_version, cluster_id);
    auto it = player_configs_.find(key);
    if (it == player_configs_.end()) {
        LOG_ERROR("Player configuration not found: " + model_version + "/" + cluster_id, 
                 "PlayerFactory");
        return nullptr;
    }
    
    const PlayerConfig& config = it->second;
    
    try {
        // 根据model_version创建不同类型的玩家
        if (model_version == "random") {
            auto player = std::make_unique<RandomPlayer>(config);
            LOG_DEBUG("Created RandomPlayer: " + cluster_id, "PlayerFactory");
            return player;
        } else if (model_version == "v1") {
            auto player = std::make_unique<V1Player>(config);
            LOG_DEBUG("Created V1Player: " + cluster_id, "PlayerFactory");
            return player;
        } else if (model_version == "v2") {
            // TODO: 当V2模型实现后取消注释
            // auto player = std::make_unique<V2Player>(config);
            // LOG_DEBUG("Created V2Player: " + cluster_id, "PlayerFactory");
            // return player;
            LOG_WARNING("V2Player not implemented yet, falling back to random", "PlayerFactory");
            auto player = std::make_unique<RandomPlayer>(config);
            return player;
        } else {
            // 未知类型，回退到随机玩家
            LOG_WARNING("Unknown player model version: " + model_version + 
                       ", falling back to random", "PlayerFactory");
            auto player = std::make_unique<RandomPlayer>(config);
            return player;
        }
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to create player " + model_version + "/" + cluster_id + 
                 ": " + e.what(), "PlayerFactory");
        return nullptr;
    }
}

std::vector<std::pair<std::string, std::string>> PlayerFactory::GetRegisteredPlayers() const {
    std::vector<std::pair<std::string, std::string>> players;
    players.reserve(player_configs_.size());
    
    for (const auto& [key, config] : player_configs_) {
        players.emplace_back(config.model_version, config.cluster_id);
    }
    
    return players;
}

bool PlayerFactory::IsRegistered(const std::string& model_version, 
                                const std::string& cluster_id) const {
    std::string key = MakeKey(model_version, cluster_id);
    return player_configs_.find(key) != player_configs_.end();
}

} // namespace SlotSimulator
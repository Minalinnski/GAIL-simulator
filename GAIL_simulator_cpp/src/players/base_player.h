// src/players/base_player.h
#pragma once

#include "player_interface.h"
#include "../core/types.h"
#include <memory>
#include <random>

namespace SlotSimulator {

class BasePlayer : public PlayerInterface {
public:
    explicit BasePlayer(const PlayerConfig& config);
    virtual ~BasePlayer() = default;
    
    // 实现基础接口
    void Reset() override;
    bool IsActive() const override { return balance_ > 0.0f && active_; }
    
    const std::string& GetId() const override { return config_.player_id; }
    const std::string& GetVersion() const override { return config_.model_version; }
    const std::string& GetCluster() const override { return config_.cluster_id; }
    float GetBalance() const override { return balance_; }
    const std::string& GetCurrency() const override { return config_.currency; }
    
    // 余额管理
    void UpdateBalance(float amount) override { balance_ += amount; }
    void SetBalance(float balance) override { balance_ = balance; }

protected:
    PlayerConfig config_;
    float balance_;
    bool active_;
    mutable std::mt19937_64 rng_;
    
    // 辅助方法供子类使用
    bool IsValidBet(float bet_amount, const SessionData& session_data) const;
    float GetRandomBet(const SessionData& session_data) const;
    float GetRandomDelay(float min_delay = 0.1f, float max_delay = 2.0f) const;
};

} // namespace SlotSimulator
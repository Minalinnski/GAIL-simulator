// random_player.h
#pragma once

#include "../base_player.h"
#include "../../core/types.h"

namespace SlotSimulator {

class RandomPlayer : public BasePlayer {
public:
    explicit RandomPlayer(const PlayerConfig& config);
    
    // 实现决策方法
    PlayerDecision MakeDecision(const std::string& machine_id, 
                               const SessionData& session_data) override;

private:
    // 配置参数
    float min_delay_;
    float max_delay_;
    float end_probability_;
    int max_consecutive_losses_;
    float session_budget_;
    int max_spins_per_session_;
    
    // 会话状态
    mutable int consecutive_losses_;
    mutable float session_spent_;
    
    // 辅助方法
    bool ShouldEndSession(const SessionData& session_data) const;
    void LoadRandomConfig();
};

} // namespace SlotSimulator
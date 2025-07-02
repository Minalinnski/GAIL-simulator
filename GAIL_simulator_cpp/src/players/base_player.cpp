// src/players/base_player.cpp
#include "base_player.h"
#include <algorithm>
#include <iostream>

namespace SlotSimulator {

BasePlayer::BasePlayer(const PlayerConfig& config) 
    : config_(config), active_(true), rng_(std::random_device{}()) {
    
    // 根据分布生成初始余额
    balance_ = config_.initial_balance.GenerateBalance();
    
    LOG_INFO("BasePlayer " + config_.player_id + " (" + config_.model_version + "/" + 
             config_.cluster_id + ") created with balance " + std::to_string(balance_), "BasePlayer");
}

void BasePlayer::Reset() {
    balance_ = config_.initial_balance.GenerateBalance();  // 重新生成随机余额
    active_ = true;
}

bool BasePlayer::IsValidBet(float bet_amount, const SessionData& session_data) const {
    if (bet_amount <= 0.0f) return false;
    if (bet_amount > balance_) return false;
    
    const auto& available_bets = session_data.available_bets;
    return std::find(available_bets.begin(), available_bets.end(), bet_amount) 
           != available_bets.end();
}

float BasePlayer::GetRandomBet(const SessionData& session_data) const {
    const auto& available_bets = session_data.available_bets;
    if (available_bets.empty()) return 1.0f;
    
    // 过滤出可承受的投注额
    std::vector<float> affordable_bets;
    for (float bet : available_bets) {
        if (bet <= balance_) {
            affordable_bets.push_back(bet);
        }
    }
    
    if (affordable_bets.empty()) return 0.0f;  // 无法承受任何投注
    
    std::uniform_int_distribution<size_t> dist(0, affordable_bets.size() - 1);
    return affordable_bets[dist(rng_)];
}

float BasePlayer::GetRandomDelay(float min_delay, float max_delay) const {
    std::uniform_real_distribution<float> dist(min_delay, max_delay);
    return dist(rng_);
}

} // namespace SlotSimulator
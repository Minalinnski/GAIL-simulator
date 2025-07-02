// random_player.cpp
#include "random_player.h"
#include <iostream>
#include <algorithm>

namespace SlotSimulator {

RandomPlayer::RandomPlayer(const PlayerConfig& config) 
    : BasePlayer(config), consecutive_losses_(0), session_spent_(0.0f) {
    
    LoadRandomConfig();
    std::cout << "RandomPlayer initialized with end_probability=" << end_probability_ 
              << ", max_losses=" << max_consecutive_losses_ << std::endl;
    // LOG_INFO("RandomPlayer initialized with end_probability=" + std::to_string(end_probability_) + 
    //      ", max_losses=" + std::to_string(max_consecutive_losses_), "RandomPlayer");
}

void RandomPlayer::LoadRandomConfig() {
    // 从配置中读取随机玩家参数，如果没有则使用默认值
    auto it = config_.model_configs.find("random");
    if (it != config_.model_configs.end()) {
        const auto& random_config = it->second;
        
        auto get_config = [&](const std::string& key, float default_val) -> float {
            auto config_it = random_config.find(key);
            return config_it != random_config.end() ? std::stof(config_it->second) : default_val;
        };
        
        auto get_config_int = [&](const std::string& key, int default_val) -> int {
            auto config_it = random_config.find(key);
            return config_it != random_config.end() ? std::stoi(config_it->second) : default_val;
        };
        
        min_delay_ = get_config("min_delay", 0.1f);
        max_delay_ = get_config("max_delay", 2.0f);
        end_probability_ = get_config("end_probability", 0.001f);
        max_consecutive_losses_ = get_config_int("max_consecutive_losses", 10);
        session_budget_ = get_config("session_budget", balance_ * 0.9f);
        max_spins_per_session_ = get_config_int("max_spins_per_session", 1000);
    } else {
        // 使用默认配置
        min_delay_ = 0.1f;
        max_delay_ = 2.0f;
        end_probability_ = 0.001f;
        max_consecutive_losses_ = 10;
        session_budget_ = balance_ * 0.9f;
        max_spins_per_session_ = 1000;
    }
}

PlayerDecision RandomPlayer::MakeDecision(const std::string& machine_id, 
                                         const SessionData& session_data) {
    // 检查是否应该结束会话
    if (ShouldEndSession(session_data)) {
        return PlayerDecision(0.0f, 0.0f);  // 结束游戏
    }
    
    // 随机选择投注额
    float bet_amount = GetRandomBet(session_data);
    if (bet_amount <= 0.0f) {
        return PlayerDecision(0.0f, 0.0f);  // 无法投注，结束游戏
    }
    
    // 随机延迟
    float delay = GetRandomDelay(min_delay_, max_delay_);
    
    // 更新会话状态
    session_spent_ += bet_amount;
    
    // 检查上一次旋转结果来更新连续失败次数
    if (!session_data.recent_spins.empty()) {
        const auto& last_spin = session_data.recent_spins.back();
        if (last_spin.profit <= 0) {
            consecutive_losses_++;
        } else {
            consecutive_losses_ = 0;
        }
    }
    
    return PlayerDecision(bet_amount, delay);
}

bool RandomPlayer::ShouldEndSession(const SessionData& session_data) const {
    // 1. 随机结束概率
    std::uniform_real_distribution<float> prob_dist(0.0f, 1.0f);
    if (prob_dist(rng_) < end_probability_) {
        return true;
    }
    
    // 2. 连续失败次数检查
    if (consecutive_losses_ >= max_consecutive_losses_) {
        return true;
    }
    
    // 3. 会话预算检查
    if (session_spent_ >= session_budget_) {
        return true;
    }
    
    // 4. 最大旋转次数检查
    if (session_data.stats.total_spins >= max_spins_per_session_) {
        return true;
    }
    
    // 5. 余额不足检查
    if (session_data.current_balance <= 0.0f) {
        return true;
    }
    
    return false;
}

} // namespace SlotSimulator
// src/core/session_controller.cpp
#include "session_controller.h"
#include "../utils/logger.h"
#include <thread>
#include <algorithm>

namespace SlotSimulator {

SessionController::SessionController(std::unique_ptr<PlayerInterface> player,
                                   std::unique_ptr<MachineInterface> machine)
    : player_(std::move(player)), machine_(std::move(machine))
    , in_free_spins_(false), free_spins_remaining_(0) {
    
    if (!player_ || !machine_) {
        throw std::invalid_argument("Player and Machine cannot be null");
    }
}

SessionStats SessionController::RunSession(const std::string& session_id,
                                          int max_spins,
                                          float max_duration_seconds) {
    
    session_start_time_ = std::chrono::high_resolution_clock::now();
    
    // 初始化session统计
    SessionStats stats;
    stats.session_id = session_id;
    stats.player_id = player_->GetId();
    stats.machine_id = machine_->GetId();
    stats.initial_balance = player_->GetBalance();
    stats.final_balance = player_->GetBalance();
    
    LOG_INFO("Starting session: " + session_id + " (" + stats.player_id + 
             " vs " + stats.machine_id + ")", "SessionController");
    
    spin_history_.clear();
    spin_history_.reserve(std::min(max_spins, 10000));  // 预分配空间
    
    try {
        while (player_->IsActive() && 
               !CheckSessionLimits(stats, max_spins, max_duration_seconds)) {
            
            // 准备session数据供玩家决策
            SessionData session_data = PrepareSessionData();
            
            // 玩家做决策
            PlayerDecision decision = player_->MakeDecision(machine_->GetId(), session_data);
            
            // 检查是否结束游戏
            if (!decision.continue_playing || decision.bet_amount <= 0.0f) {
                LOG_DEBUG("Player decided to end session", "SessionController");
                break;
            }
            
            // 验证投注额
            if (!machine_->IsValidBet(decision.bet_amount, player_->GetCurrency())) {
                LOG_WARNING("Invalid bet amount: " + std::to_string(decision.bet_amount), 
                           "SessionController");
                break;
            }
            
            // 检查余额
            if (decision.bet_amount > player_->GetBalance()) {
                LOG_DEBUG("Insufficient balance for bet: " + std::to_string(decision.bet_amount), 
                         "SessionController");
                break;
            }
            
            // 执行旋转
            ExecuteSpin(decision.bet_amount, stats);
            
            // 模拟延迟
            if (decision.delay_time > 0.0f) {
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(static_cast<int>(decision.delay_time * 1000)));
            }
            
            // 定期输出进度
            LogSessionProgress(stats);
        }
        
    } catch (const std::exception& e) {
        LOG_ERROR("Exception in session " + session_id + ": " + e.what(), "SessionController");
    }
    
    // 完成session统计
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - session_start_time_);
    
    stats.session_duration = duration.count() / 1000.0;
    stats.final_balance = player_->GetBalance();
    stats.total_profit = stats.final_balance - stats.initial_balance;
    
    if (stats.total_bet > 0.0f) {
        stats.rtp = stats.total_win / stats.total_bet;
    }
    
    LOG_INFO("Session completed: " + session_id + 
             " (spins: " + std::to_string(stats.total_spins) +
             ", profit: " + std::to_string(stats.total_profit) +
             ", RTP: " + std::to_string(stats.rtp * 100) + "%)", "SessionController");
    
    return stats;
}

SessionData SessionController::PrepareSessionData() const {
    SessionData data;
    data.current_balance = player_->GetBalance();
    data.in_free_spins = in_free_spins_;
    data.free_spins_remaining = free_spins_remaining_;
    
    // 获取可用投注选项
    data.available_bets = machine_->GetBetOptions(player_->GetCurrency());
    
    // 复制最近的旋转历史（最多10次）
    int history_size = std::min(static_cast<int>(spin_history_.size()), 10);
    if (history_size > 0) {
        data.recent_spins.assign(
            spin_history_.end() - history_size, 
            spin_history_.end()
        );
    }
    
    // 准备基础统计信息
    data.stats.total_spins = static_cast<int>(spin_history_.size());
    
    if (!spin_history_.empty()) {
        for (const auto& spin : spin_history_) {
            data.stats.total_bet += spin.bet_amount;
            data.stats.total_win += spin.win_amount;
            data.stats.total_profit += spin.profit;
            
            if (spin.trigger_free_spins) {
                data.stats.free_spins_triggered++;
            }
            if (spin.in_free_spins) {
                data.stats.free_spins_played++;
            }
            
            data.stats.max_win = std::max(data.stats.max_win, spin.win_amount);
        }
    }
    
    return data;
}

void SessionController::ExecuteSpin(float bet_amount, SessionStats& stats) {
    // 扣除投注额
    player_->UpdateBalance(-bet_amount);
    
    // 执行机器旋转
    SpinResult spin_result = machine_->Spin(bet_amount, in_free_spins_, free_spins_remaining_);
    
    // 添加中奖金额到余额
    player_->UpdateBalance(spin_result.win_amount);
    
    // 更新免费旋转状态
    if (spin_result.trigger_free_spins && !in_free_spins_) {
        in_free_spins_ = true;
        free_spins_remaining_ = spin_result.free_spins_remaining;
        LOG_DEBUG("Free spins triggered: " + std::to_string(free_spins_remaining_), 
                 "SessionController");
    } else if (in_free_spins_) {
        free_spins_remaining_ = spin_result.free_spins_remaining;
        if (free_spins_remaining_ <= 0) {
            in_free_spins_ = false;
            LOG_DEBUG("Free spins completed", "SessionController");
        }
    }
    
    // 设置旋转编号
    spin_result.spin_number = static_cast<int>(spin_history_.size() + 1);
    
    // 保存旋转结果
    spin_history_.push_back(spin_result);
    
    // 更新统计
    UpdateSessionStats(stats, spin_result);
}

void SessionController::UpdateSessionStats(SessionStats& stats, const SpinResult& spin_result) const {
    stats.total_spins++;
    stats.total_bet += spin_result.bet_amount;
    stats.total_win += spin_result.win_amount;
    stats.total_profit += spin_result.profit;
    
    if (spin_result.trigger_free_spins) {
        stats.free_spins_triggered++;
    }
    if (spin_result.in_free_spins) {
        stats.free_spins_played++;
    }
    
    stats.max_win = std::max(stats.max_win, spin_result.win_amount);
    
    // 计算最大连续亏损
    if (spin_result.profit < 0) {
        stats.max_loss_streak = std::min(stats.max_loss_streak, spin_result.profit);
    }
}

bool SessionController::CheckSessionLimits(const SessionStats& stats, 
                                         int max_spins, 
                                         float max_duration) const {
    // 检查旋转次数限制
    if (stats.total_spins >= max_spins) {
        return true;
    }
    
    // 检查时间限制
    auto current_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(
        current_time - session_start_time_);
    
    if (duration.count() >= max_duration) {
        return true;
    }
    
    return false;
}

void SessionController::LogSessionProgress(const SessionStats& stats, int log_interval) const {
    if (stats.total_spins % log_interval == 0 && stats.total_spins > 0) {
        LOG_DEBUG("Session progress - Spins: " + std::to_string(stats.total_spins) +
                 ", Balance: " + std::to_string(player_->GetBalance()) +
                 ", Profit: " + std::to_string(stats.total_profit), "SessionController");
    }
}

} // namespace SlotSimulator
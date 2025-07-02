// src/players/models/v1/v1_data_processor.cpp
#include "v1_data_processor.h"
#include <algorithm>

namespace SlotSimulator {

std::vector<float> V1DataProcessor::PrepareBettingInput(const SessionData& session_data) const {
    // V1投注模型需要12维输入：
    // [balance, profit, streak, slot_type, base_point, 
    //  delta_t, delta_profit, delta_payout, prev_bet, 
    //  prev_basepoint, prev_profit, currency_flag]
    
    std::vector<float> input(12, 0.0f);
    
    input[0] = session_data.current_balance;  // balance
    
    float current_profit = 0.0f;
    float prev_bet = 0.0f;
    float prev_profit = 0.0f;
    
    if (!session_data.recent_spins.empty()) {
        const auto& last_spin = session_data.recent_spins.back();
        current_profit = last_spin.profit;
        prev_bet = last_spin.bet_amount;
    }
    
    input[1] = current_profit;                // profit
    input[2] = CalculateStreak(session_data); // streak
    input[3] = 1.0f;                         // slot_type (固定值)
    input[4] = session_data.current_balance; // base_point
    input[5] = 1.0f;                         // delta_t (固定值)
    input[6] = CalculateDeltaProfit(session_data); // delta_profit
    input[7] = 0.0f;                         // delta_payout
    input[8] = prev_bet;                     // prev_bet
    input[9] = session_data.current_balance; // prev_basepoint
    input[10] = prev_profit;                 // prev_profit
    input[11] = 1.0f;                        // currency_flag (USD=1.0)
    
    return input;
}

std::vector<float> V1DataProcessor::PrepareTerminationInput(const SessionData& session_data) const {
    // V1终止模型需要8维输入：
    // [current_balance, total_profit, current_bet, streak,
    //  win_streak, prev_bet, prev_balance, prev_profit]
    
    std::vector<float> input(8, 0.0f);
    
    input[0] = session_data.current_balance;     // current_balance
    input[1] = session_data.stats.total_profit; // total_profit
    
    float current_bet = 0.0f;
    float prev_bet = 0.0f;
    
    if (!session_data.recent_spins.empty()) {
        const auto& last_spin = session_data.recent_spins.back();
        current_bet = last_spin.bet_amount;
        
        if (session_data.recent_spins.size() > 1) {
            prev_bet = session_data.recent_spins[session_data.recent_spins.size() - 2].bet_amount;
        }
    }
    
    input[2] = current_bet;                      // current_bet
    input[3] = CalculateStreak(session_data);    // streak
    input[4] = std::max(0.0f, input[3]);        // win_streak (正值表示连胜)
    input[5] = prev_bet;                         // prev_bet
    input[6] = session_data.current_balance;     // prev_balance
    input[7] = session_data.stats.total_profit; // prev_profit
    
    return input;
}

float V1DataProcessor::CalculateStreak(const SessionData& session_data) const {
    if (session_data.recent_spins.empty()) return 0.0f;
    
    float streak = 0.0f;
    bool winning = session_data.recent_spins.back().profit > 0;
    
    // 从最后一次旋转开始向前计算连续胜负
    for (auto it = session_data.recent_spins.rbegin(); 
         it != session_data.recent_spins.rend(); ++it) {
        bool current_win = it->profit > 0;
        if (current_win == winning) {
            streak += winning ? 1.0f : -1.0f;
        } else {
            break;
        }
    }
    
    return streak;
}

float V1DataProcessor::CalculateDeltaProfit(const SessionData& session_data) const {
    if (session_data.recent_spins.size() < 2) return 0.0f;
    
    const auto& last_spin = session_data.recent_spins.back();
    const auto& prev_spin = session_data.recent_spins[session_data.recent_spins.size() - 2];
    
    return last_spin.profit - prev_spin.profit;
}

} // namespace SlotSimulator
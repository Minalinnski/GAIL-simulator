// src/machines/slot_machine.cpp
#include "slot_machine.h"
#include "../utils/logger.h"
#include <algorithm>

namespace SlotSimulator {

const BetOptions SlotMachine::empty_bet_options_;

SlotMachine::SlotMachine(const MachineConfig& config) 
    : config_(config), rng_(std::random_device{}()) {
    
    // 创建PayTable
    pay_table_ = std::make_unique<PayTable>(config_.pay_table, config_.paylines);
    
    // 创建ReelSet
    for (const auto& [reel_set_name, reels] : config_.reels) {
        reel_sets_[reel_set_name] = std::make_unique<ReelSet>(reels, config_.window_size);
    }
    
    LOG_INFO("SlotMachine " + config_.machine_id + " initialized with " + 
             std::to_string(reel_sets_.size()) + " reel sets", "SlotMachine");
}

SpinResult SlotMachine::Spin(float bet_amount, bool in_free_spins, int free_spins_remaining) {
    SpinResult result;
    result.bet_amount = bet_amount;
    result.in_free_spins = in_free_spins;
    result.timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count() / 1000.0;
    
    // 选择轮盘集合
    std::string reel_set_name = in_free_spins ? "bonus" : "normal";
    if (reel_sets_.find(reel_set_name) == reel_sets_.end()) {
        reel_set_name = "normal";  // 回退到normal
    }
    
    // 生成旋转结果
    result.grid = GenerateSpinGrid(reel_set_name);
    
    // 计算中奖金额
    result.win_amount = CalculateWinAmount(result.grid, bet_amount, config_.active_lines);
    result.profit = result.win_amount - bet_amount;
    
    // 检查免费旋转触发
    if (!in_free_spins) {
        result.trigger_free_spins = CheckFreeSpinsTrigger(result.grid);
        result.free_spins_remaining = result.trigger_free_spins ? config_.free_spins_count : 0;
    } else {
        result.trigger_free_spins = false;
        result.free_spins_remaining = std::max(0, free_spins_remaining - 1);
        // 免费旋转倍数
        result.win_amount *= config_.free_spins_multiplier;
        result.profit = result.win_amount - bet_amount;
    }
    
    return result;
} = in_free_spins ? "bonus" : "normal";
    if (reel_sets_.find(reel_set_name) == reel_sets_.end()) {
        reel_set_name = "normal";  // 回退到normal
    }
    
    // 生成旋转结果
    result.grid = GenerateSpinGrid(reel_set_name);
    
    // 计算中奖金额
    result.win_amount = CalculateWinAmount(result.grid, bet_amount, config_.active_lines);
    result.profit = result.win_amount - bet_amount;
    
    // 检查免费旋转触发
    if (!in_free_spins) {
        result.trigger_free_spins = CheckFreeSpinsTrigger(result.grid);
        result.free_spins_remaining = result.trigger_free_spins ? config_.free_spins_count : 0;
    } else {
        result.trigger_free_spins = false;
        result.free_spins_remaining = std::max(0, free_spins_remaining - 1);
        // 免费旋转倍数
        result.win_amount *= config_.free_spins_multiplier;
        result.profit = result.win_amount - bet_amount;
    }
    
    return result;
}

void SlotMachine::ResetState() {
    // 老虎机是无状态的，这里主要是为了接口一致性
    // 如果将来需要维护一些状态，可以在这里重置
}

const BetOptions& SlotMachine::GetBetOptions(const std::string& currency) const {
    auto it = config_.bet_table.find(currency);
    if (it != config_.bet_table.end()) {
        return it->second;
    }
    return empty_bet_options_;
}

bool SlotMachine::IsValidBet(float bet_amount, const std::string& currency) const {
    const auto& bet_options = GetBetOptions(currency);
    return std::find(bet_options.begin(), bet_options.end(), bet_amount) != bet_options.end();
}

SpinGrid SlotMachine::GenerateSpinGrid(const std::string& reel_set_name) {
    auto it = reel_sets_.find(reel_set_name);
    if (it == reel_sets_.end()) {
        throw std::runtime_error("Reel set not found: " + reel_set_name);
    }
    
    return it->second->GenerateGrid(rng_);
}

float SlotMachine::CalculateWinAmount(const SpinGrid& grid, float bet_amount, int active_lines) {
    return pay_table_->CalculateTotalWin(grid, bet_amount, active_lines);
}

bool SlotMachine::CheckFreeSpinsTrigger(const SpinGrid& grid) {
    // 检查是否有3个或更多scatter符号在不同列上
    int num_reels = grid.size() / config_.window_size;
    int scatter_columns = 0;
    
    for (int col = 0; col < num_reels; ++col) {
        bool has_scatter = false;
        for (int row = 0; row < config_.window_size; ++row) {
            if (grid[row * num_reels + col] == config_.scatter_symbol) {
                has_scatter = true;
                break;
            }
        }
        if (has_scatter) {
            scatter_columns++;
        }
    }
    
    return scatter_columns >= 3;
}

std::vector<int> SlotMachine::GetPaylineSymbols(const SpinGrid& grid, const PaylineIndices& payline) {
    std::vector<int> symbols;
    symbols.reserve(payline.size());
    
    for (int index : payline) {
        if (index >= 0 && index < static_cast<int>(grid.size())) {
            symbols.push_back(grid[index]);
        }
    }
    
    return symbols;
}

int SlotMachine::CountConsecutiveSymbols(const std::vector<int>& symbols) {
    if (symbols.empty()) return 0;
    
    int first_symbol = symbols[0];
    int count = 1;
    
    for (size_t i = 1; i < symbols.size(); ++i) {
        int current_symbol = symbols[i];
        if (current_symbol == first_symbol || IsWildSymbol(current_symbol)) {
            count++;
        } else if (IsWildSymbol(first_symbol)) {
            // 如果第一个是wild，更新为当前非wild符号
            first_symbol = current_symbol;
            count++;
        } else {
            break;
        }
    }
    
    return count;
}

bool SlotMachine::IsWildSymbol(int symbol) const {
    return std::find(config_.wild_symbols.begin(), config_.wild_symbols.end(), symbol) 
           != config_.wild_symbols.end();
}

} // namespace SlotSimulator
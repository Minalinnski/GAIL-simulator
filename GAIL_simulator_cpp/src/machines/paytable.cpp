// paytable.cpp
#include "paytable.h"
#include <algorithm>

namespace SlotSimulator {

PayTable::PayTable(const std::unordered_map<std::string, PayoutArray>& pay_table,
                   const std::vector<PaylineIndices>& paylines)
    : pay_table_(pay_table), paylines_(paylines) {
}

float PayTable::CalculateTotalWin(const SpinGrid& grid, float bet_amount, int active_lines) const {
    float total_win = 0.0f;
    
    int lines_to_check = std::min(active_lines, static_cast<int>(paylines_.size()));
    
    for (int i = 0; i < lines_to_check; ++i) {
        total_win += CalculatePaylineWin(grid, paylines_[i], bet_amount);
    }
    
    return total_win;
}

float PayTable::CalculatePaylineWin(const SpinGrid& grid, const PaylineIndices& payline, 
                                   float bet_amount) const {
    auto symbols = GetPaylineSymbols(grid, payline);
    if (symbols.empty()) return 0.0f;
    
    int consecutive_count = CountConsecutiveSymbols(symbols);
    if (consecutive_count < 3) return 0.0f;  // 至少需要3个连续符号
    
    // 获取基础符号（非wild符号）
    std::string base_symbol = std::to_string(symbols[0]);
    for (int symbol : symbols) {
        if (symbol != 101) {  // 假设101是wild符号
            base_symbol = std::to_string(symbol);
            break;
        }
    }
    
    float payout = GetPayout(base_symbol, consecutive_count);
    return payout * bet_amount;
}

std::vector<int> PayTable::GetPaylineSymbols(const SpinGrid& grid, 
                                            const PaylineIndices& payline) const {
    std::vector<int> symbols;
    symbols.reserve(payline.size());
    
    for (int index : payline) {
        if (index >= 0 && index < static_cast<int>(grid.size())) {
            symbols.push_back(grid[index]);
        }
    }
    
    return symbols;
}

int PayTable::CountConsecutiveSymbols(const std::vector<int>& symbols) const {
    if (symbols.empty()) return 0;
    
    int first_symbol = symbols[0];
    int count = 1;
    
    for (size_t i = 1; i < symbols.size(); ++i) {
        int current_symbol = symbols[i];
        // 简化wild逻辑 - 假设101是wild符号
        if (current_symbol == first_symbol || current_symbol == 101) {
            count++;
        } else if (first_symbol == 101) {
            first_symbol = current_symbol;
            count++;
        } else {
            break;
        }
    }
    
    return count;
}

float PayTable::GetPayout(const std::string& symbol, int count) const {
    auto it = pay_table_.find(symbol);
    if (it == pay_table_.end()) return 0.0f;
    
    const auto& payouts = it->second;
    
    // count: 3->index 0, 4->index 1, 5->index 2
    int index = count - 3;
    if (index >= 0 && index < static_cast<int>(payouts.size())) {
        return payouts[index];
    }
    
    return 0.0f;
}

} // namespace SlotSimulator
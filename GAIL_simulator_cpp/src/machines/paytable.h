// paytable.h
#pragma once

#include "../core/types.h"
#include <vector>
#include <unordered_map>
#include <string>

namespace SlotSimulator {

class PayTable {
public:
    explicit PayTable(const std::unordered_map<std::string, PayoutArray>& pay_table,
                      const std::vector<PaylineIndices>& paylines);
    
    // 计算总中奖金额
    float CalculateTotalWin(const SpinGrid& grid, float bet_amount, int active_lines) const;
    
    // 计算单条payline的中奖
    float CalculatePaylineWin(const SpinGrid& grid, const PaylineIndices& payline, 
                             float bet_amount) const;

private:
    std::unordered_map<std::string, PayoutArray> pay_table_;
    std::vector<PaylineIndices> paylines_;
    
    // 辅助方法
    std::vector<int> GetPaylineSymbols(const SpinGrid& grid, const PaylineIndices& payline) const;
    int CountConsecutiveSymbols(const std::vector<int>& symbols) const;
    float GetPayout(const std::string& symbol, int count) const;
};

} // namespace SlotSimulator
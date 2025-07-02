// src/machines/slot_machine.h
#pragma once

#include "../core/types.h"
#include "reel.h"
#include "paytable.h"
#include <random>
#include <memory>
#include <unordered_map>

namespace SlotSimulator {

class SlotMachine : public MachineInterface {
public:
    explicit SlotMachine(const MachineConfig& config);
    ~SlotMachine() = default;

    // 实现MachineInterface接口
    SpinResult Spin(float bet_amount, bool in_free_spins = false, int free_spins_remaining = 0) override;
    void ResetState() override;
    const std::string& GetId() const override { return config_.machine_id; }
    const BetOptions& GetBetOptions(const std::string& currency) const override;
    bool IsValidBet(float bet_amount, const std::string& currency) const override;
    int GetActiveLines() const override { return config_.active_lines; }
    void SetSeed(uint64_t seed) override { rng_.seed(seed); }

private:
    MachineConfig config_;
    std::unique_ptr<PayTable> pay_table_;
    std::unordered_map<std::string, std::unique_ptr<ReelSet>> reel_sets_;
    
    std::mt19937_64 rng_;
    
    // 内部方法
    SpinGrid GenerateSpinGrid(const std::string& reel_set_name);
    float CalculateWinAmount(const SpinGrid& grid, float bet_amount, int active_lines);
    bool CheckFreeSpinsTrigger(const SpinGrid& grid);
    std::vector<int> GetPaylineSymbols(const SpinGrid& grid, const PaylineIndices& payline);
    int CountConsecutiveSymbols(const std::vector<int>& symbols);
    bool IsWildSymbol(int symbol) const;
    
    static const BetOptions empty_bet_options_;
};

} // namespace SlotSimulator
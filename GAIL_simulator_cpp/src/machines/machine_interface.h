// src/machines/machine_interface.h
#pragma once

#include "../core/types.h"
#include <string>

namespace SlotSimulator {

class MachineInterface {
public:
    virtual ~MachineInterface() = default;
    
    // 核心游戏功能
    virtual SpinResult Spin(float bet_amount, bool in_free_spins = false, 
                           int free_spins_remaining = 0) = 0;
    
    // 状态管理
    virtual void ResetState() = 0;
    
    // 信息获取
    virtual const std::string& GetId() const = 0;
    virtual const BetOptions& GetBetOptions(const std::string& currency) const = 0;
    virtual bool IsValidBet(float bet_amount, const std::string& currency) const = 0;
    
    // 配置相关
    virtual int GetActiveLines() const = 0;
    virtual void SetSeed(uint64_t seed) = 0;
};

} // namespace SlotSimulator
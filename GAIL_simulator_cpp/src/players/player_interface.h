// src/players/player_interface.h
#pragma once

#include "../core/types.h"
#include <string>

namespace SlotSimulator {

class PlayerInterface {
public:
    virtual ~PlayerInterface() = default;
    
    // 核心决策方法 - 基于当前session数据做出决策
    virtual PlayerDecision MakeDecision(const std::string& machine_id, 
                                       const SessionData& session_data) = 0;
    
    // 生命周期管理
    virtual void Reset() = 0;
    virtual bool IsActive() const = 0;
    
    // 获取玩家信息
    virtual const std::string& GetId() const = 0;
    virtual const std::string& GetVersion() const = 0;
    virtual const std::string& GetCluster() const = 0;
    virtual float GetBalance() const = 0;
    virtual const std::string& GetCurrency() const = 0;
    
    // 余额管理
    virtual void UpdateBalance(float amount) = 0;
    virtual void SetBalance(float balance) = 0;
};

} // namespace SlotSimulator
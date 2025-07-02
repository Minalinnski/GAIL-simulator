// src/machines/machine_factory.h
#pragma once

#include "machine_interface.h"
#include "../core/types.h"
#include <memory>
#include <unordered_map>
#include <string>

namespace SlotSimulator {

class MachineFactory {
public:
    MachineFactory() = default;
    ~MachineFactory() = default;
    
    // 注册机器配置
    void RegisterMachine(const MachineConfig& config);
    
    // 创建机器实例
    std::unique_ptr<MachineInterface> CreateMachine(const std::string& machine_id) const;
    
    // 获取已注册的机器列表
    std::vector<std::string> GetRegisteredMachines() const;
    
    // 检查机器是否已注册
    bool IsRegistered(const std::string& machine_id) const;

private:
    std::unordered_map<std::string, MachineConfig> machine_configs_;
};

} // namespace SlotSimulator
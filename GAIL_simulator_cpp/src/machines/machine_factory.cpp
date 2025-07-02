// src/machines/machine_factory.cpp
#include "machine_factory.h"
#include "slot_machine.h"
#include "../utils/logger.h"

namespace SlotSimulator {

void MachineFactory::RegisterMachine(const MachineConfig& config) {
    machine_configs_[config.machine_id] = config;
    LOG_INFO("Registered machine: " + config.machine_id, "MachineFactory");
}

std::unique_ptr<MachineInterface> MachineFactory::CreateMachine(const std::string& machine_id) const {
    auto it = machine_configs_.find(machine_id);
    if (it == machine_configs_.end()) {
        LOG_ERROR("Machine configuration not found: " + machine_id, "MachineFactory");
        return nullptr;
    }
    
    try {
        auto machine = std::make_unique<SlotMachine>(it->second);
        LOG_DEBUG("Created machine instance: " + machine_id, "MachineFactory");
        return machine;
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to create machine " + machine_id + ": " + e.what(), "MachineFactory");
        return nullptr;
    }
}

std::vector<std::string> MachineFactory::GetRegisteredMachines() const {
    std::vector<std::string> machine_ids;
    machine_ids.reserve(machine_configs_.size());
    
    for (const auto& [machine_id, config] : machine_configs_) {
        machine_ids.push_back(machine_id);
    }
    
    return machine_ids;
}

bool MachineFactory::IsRegistered(const std::string& machine_id) const {
    return machine_configs_.find(machine_id) != machine_configs_.end();
}

} // namespace SlotSimulator
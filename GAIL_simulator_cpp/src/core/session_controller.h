// src/core/session_controller.h
#pragma once

#include "types.h"
#include "../machines/machine_interface.h"
#include "../players/player_interface.h"
#include <memory>
#include <vector>
#include <chrono>

namespace SlotSimulator {

class SessionController {
public:
    SessionController(std::unique_ptr<PlayerInterface> player,
                     std::unique_ptr<MachineInterface> machine);
    
    ~SessionController() = default;
    
    // 运行完整session
    SessionStats RunSession(const std::string& session_id,
                           int max_spins = 10000,
                           float max_duration_seconds = 300.0f);

private:
    std::unique_ptr<PlayerInterface> player_;
    std::unique_ptr<MachineInterface> machine_;
    
    // Session状态
    std::vector<SpinResult> spin_history_;
    bool in_free_spins_;
    int free_spins_remaining_;
    
    // 统计和限制
    std::chrono::high_resolution_clock::time_point session_start_time_;
    
    // 辅助方法
    SessionData PrepareSessionData() const;
    void UpdateSessionStats(SessionStats& stats, const SpinResult& spin_result) const;
    bool CheckSessionLimits(const SessionStats& stats, int max_spins, float max_duration) const;
    void ExecuteSpin(float bet_amount, SessionStats& stats);
    void LogSessionProgress(const SessionStats& stats, int log_interval = 1000) const;
};

} // namespace SlotSimulator
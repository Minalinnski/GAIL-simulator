// src/players/models/v1/v1_data_processor.h
#pragma once

#include "../../../core/types.h"
#include <vector>

namespace SlotSimulator {

class V1DataProcessor {
public:
    V1DataProcessor() = default;
    ~V1DataProcessor() = default;
    
    // 准备模型输入数据
    std::vector<float> PrepareBettingInput(const SessionData& session_data) const;
    std::vector<float> PrepareTerminationInput(const SessionData& session_data) const;

private:
    // 辅助方法
    float CalculateStreak(const SessionData& session_data) const;
    float CalculateDeltaProfit(const SessionData& session_data) const;
};

} // namespace SlotSimulator
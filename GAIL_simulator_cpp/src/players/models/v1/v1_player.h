// src/players/models/v1/v1_player.h
#pragma once

#include "../../base_player.h"
#include "v1_model_loader.h"
#include "v1_data_processor.h"
#include <memory>
#include <unordered_map>
#include <yaml-cpp/yaml.h>

namespace SlotSimulator {

class V1Player : public BasePlayer {
public:
    explicit V1Player(const PlayerConfig& config);
    
    // 实现决策方法
    PlayerDecision MakeDecision(const std::string& machine_id, 
                               const SessionData& session_data) override;
    
    void Reset() override;

private:
    std::unique_ptr<V1ModelLoader> model_loader_;
    std::unique_ptr<V1DataProcessor> data_processor_;
    
    // V1特有状态
    mutable bool is_first_bet_;
    mutable float first_bet_amount_;
    std::unordered_map<float, float> first_bet_mapping_;  // 投注额权重映射
    
    // 配置参数
    std::string cluster_path_;
    
    // 辅助方法
    void LoadV1Config();
    void SetDefaultFirstBetMapping();
    float CalculateFirstBet() const;
    bool ShouldTerminate(const SessionData& session_data) const;
    float DecideBetAmount(const SessionData& session_data) const;
    float DecideDelayTime(const SessionData& session_data) const;
};

} // namespace SlotSimulator
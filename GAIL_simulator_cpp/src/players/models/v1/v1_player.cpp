// src/players/models/v1/v1_player.cpp
#include "v1_player.h"
#include "../../../utils/logger.h"
#include <iostream>
#include <random>

namespace SlotSimulator {

V1Player::V1Player(const PlayerConfig& config) 
    : BasePlayer(config), is_first_bet_(true) {
    
    LoadV1Config();
    
    // 创建模型加载器和数据处理器
    model_loader_ = std::make_unique<V1ModelLoader>(cluster_path_);
    data_processor_ = std::make_unique<V1DataProcessor>();
    
    // 预计算首次投注
    first_bet_amount_ = CalculateFirstBet();
    
    LOG_INFO("V1Player " + config_.cluster_id + " initialized with first bet: " + 
             std::to_string(first_bet_amount_), "V1Player");
}

void V1Player::LoadV1Config() {
    auto it = config_.model_configs.find("v1");
    if (it != config_.model_configs.end()) {
        const auto& v1_config = it->second;
        
        auto cluster_path_it = v1_config.find("cluster_path");
        if (cluster_path_it != v1_config.end()) {
            cluster_path_ = cluster_path_it->second;
        } else {
            cluster_path_ = "src/players/models/v1/weights/" + config_.cluster_id;
        }
        
        // 解析first_bet_mapping（如果存在YAML格式的配置）
        auto first_bet_it = v1_config.find("first_bet_mapping");
        if (first_bet_it != v1_config.end()) {
            // 解析YAML格式的first_bet_mapping
            try {
                YAML::Node mapping = YAML::Load(first_bet_it->second);
                first_bet_mapping_.clear();
                for (auto node_it = mapping.begin(); node_it != mapping.end(); ++node_it) {
                    float bet = node_it->first.as<float>();
                    float weight = node_it->second.as<float>();
                    first_bet_mapping_[bet] = weight;
                }
            } catch (const std::exception& e) {
                LOG_WARNING("Failed to parse first_bet_mapping, using defaults: " + 
                           std::string(e.what()), "V1Player");
                SetDefaultFirstBetMapping();
            }
        } else {
            SetDefaultFirstBetMapping();
        }
    } else {
        cluster_path_ = "src/players/models/v1/weights/" + config_.cluster_id;
        SetDefaultFirstBetMapping();
    }
}

void V1Player::SetDefaultFirstBetMapping() {
    // 使用默认的first_bet_mapping
    first_bet_mapping_ = {
        {0.5f, 6617486.0f}, {1.0f, 12389649.0f}, {2.5f, 17502407.0f},
        {5.0f, 11196115.0f}, {8.0f, 3892178.0f}, {15.0f, 2314774.0f},
        {25.0f, 876125.0f}, {50.0f, 200001.0f}, {70.0f, 40075.0f},
        {100.0f, 36310.0f}, {250.0f, 12000.0f}, {500.0f, 6763.0f},
        {1000.0f, 2800.0f}, {2000.0f, 1995.0f}, {5000.0f, 191.0f}
    };
}

float V1Player::CalculateFirstBet() const {
    std::vector<float> bet_options;
    std::vector<float> weights;
    
    for (const auto& [bet, weight] : first_bet_mapping_) {
        bet_options.push_back(bet);
        weights.push_back(weight);
    }
    
    if (bet_options.empty()) {
        return 1.0f;  // 默认值
    }
    
    std::discrete_distribution<int> dist(weights.begin(), weights.end());
    int selected_index = dist(rng_);
    
    return bet_options[selected_index];
}

PlayerDecision V1Player::MakeDecision(const std::string& machine_id, 
                                     const SessionData& session_data) {
    try {
        // 检查是否应该终止
        // if (ShouldTerminate(session_data)) {
        //     return PlayerDecision(0.0f, 0.0f);
        // }
        
        float bet_amount;
        if (is_first_bet_) {
            is_first_bet_ = false;
            bet_amount = first_bet_amount_;
        } else {
            bet_amount = DecideBetAmount(session_data);
        }
        
        float delay_time = DecideDelayTime(session_data);
        
        return PlayerDecision(bet_amount, delay_time);
        
    } catch (const std::exception& e) {
        LOG_ERROR("V1Player decision failed: " + std::string(e.what()), "V1Player");
        // 回退到简单策略
        return PlayerDecision(GetRandomBet(session_data), GetRandomDelay());
    }
}

void V1Player::Reset() {
    BasePlayer::Reset();
    is_first_bet_ = true;
    first_bet_amount_ = CalculateFirstBet();
}

bool V1Player::ShouldTerminate(const SessionData& session_data) const {
    // 使用V1终止模型进行预测
    auto termination_input = data_processor_->PrepareTerminationInput(session_data);
    return model_loader_->PredictTermination(termination_input);
}

float V1Player::DecideBetAmount(const SessionData& session_data) const {
    // 使用V1投注模型进行预测
    auto betting_input = data_processor_->PrepareBettingInput(session_data);
    float predicted_bet = model_loader_->PredictBetAmount(betting_input);
    
    // 确保投注额有效
    if (!IsValidBet(predicted_bet, session_data)) {
        return GetRandomBet(session_data);
    }
    
    return predicted_bet;
}

float V1Player::DecideDelayTime(const SessionData& session_data) const {
    // V1模型可能不预测延迟时间，使用默认逻辑
    return GetRandomDelay(0.1f, 1.0f);
}

} // namespace SlotSimulator
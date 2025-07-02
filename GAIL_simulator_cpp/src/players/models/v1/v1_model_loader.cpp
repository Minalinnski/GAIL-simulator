// src/players/models/v1/v1_model_loader.cpp
#include "v1_model_loader.h"
#include "../../../utils/logger.h"
#include "../../../utils/file_utils.h"
#include "../../ml_interface/model_loader.h"
#include <filesystem>
#include <iostream>
#include <regex>

namespace SlotSimulator {

V1ModelLoader::V1ModelLoader(const std::string& cluster_path) 
    : cluster_path_(cluster_path), models_loaded_(false), cluster_id_(0) {
    
    ExtractClusterInfo();
    
    if (!LoadModels()) {
        LOG_ERROR("Failed to load V1 models from: " + cluster_path, "V1ModelLoader");
        throw std::runtime_error("Failed to load V1 models from: " + cluster_path);
    }
    
    LOG_INFO("V1ModelLoader initialized for cluster " + std::to_string(cluster_id_), "V1ModelLoader");
}

void V1ModelLoader::ExtractClusterInfo() {
    // 从路径中提取cluster ID，例如: "weights/cluster_0" -> cluster_id = 0
    std::regex cluster_regex(R"(cluster_(\d+))");
    std::smatch match;
    
    if (std::regex_search(cluster_path_, match, cluster_regex)) {
        cluster_id_ = std::stoi(match[1].str());
    } else {
        LOG_WARNING("Could not extract cluster ID from path: " + cluster_path_, "V1ModelLoader");
    }
}

bool V1ModelLoader::LoadModels() {
    LOG_INFO("Loading V1 models from: " + cluster_path_, "V1ModelLoader");
    
    // 构建模型文件路径
    betting_model_path_ = BuildModelPath("betting_cluster_" + std::to_string(cluster_id_) + ".pth");
    termination_model_path_ = BuildModelPath("termination_25_model_" + 
                                           (cluster_id_ < 10 ? "0" : "") + 
                                           std::to_string(cluster_id_) + ".pth");
    isolation_forest_path_ = BuildModelPath("termination_25_model_" + 
                                          (cluster_id_ < 10 ? "0" : "") + 
                                          std::to_string(cluster_id_) + "_isolation_forest.pkl");
    metadata_path_ = BuildModelPath("termination_25_model_" + 
                                  (cluster_id_ < 10 ? "0" : "") + 
                                  std::to_string(cluster_id_) + "_metadata.json");
    
    // 验证文件是否存在
    if (!ValidateModelFiles()) {
        return false;
    }
    
    try {
        // 加载投注模型 (PyTorch)
        betting_model_ = ModelLoaderFactory::CreateLoader(
            ModelLoaderFactory::DetectModelType(betting_model_path_)
        );
        if (!betting_model_ || !betting_model_->LoadModel(betting_model_path_)) {
            LOG_ERROR("Failed to load betting model: " + betting_model_path_, "V1ModelLoader");
            return false;
        }
        
        // 加载终止模型 (PyTorch)
        termination_model_ = ModelLoaderFactory::CreateLoader(
            ModelLoaderFactory::DetectModelType(termination_model_path_)
        );
        if (!termination_model_ || !termination_model_->LoadModel(termination_model_path_)) {
            LOG_ERROR("Failed to load termination model: " + termination_model_path_, "V1ModelLoader");
            return false;
        }
        
        // 加载Isolation Forest (Pickle)
        isolation_forest_ = ModelLoaderFactory::CreateLoader(
            ModelLoaderFactory::DetectModelType(isolation_forest_path_)
        );
        if (!isolation_forest_ || !isolation_forest_->LoadModel(isolation_forest_path_)) {
            LOG_ERROR("Failed to load isolation forest: " + isolation_forest_path_, "V1ModelLoader");
            return false;
        }
        
        models_loaded_ = true;
        LOG_INFO("All V1 models loaded successfully", "V1ModelLoader");
        return true;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Exception while loading models: " + std::string(e.what()), "V1ModelLoader");
        return false;
    }
}

std::string V1ModelLoader::BuildModelPath(const std::string& filename) const {
    return cluster_path_ + "/" + filename;
}

bool V1ModelLoader::ValidateModelFiles() const {
    std::vector<std::string> required_files = {
        betting_model_path_,
        termination_model_path_,
        isolation_forest_path_,
        metadata_path_
    };
    
    for (const auto& file_path : required_files) {
        if (!FileUtils::FileExists(file_path)) {
            LOG_ERROR("Required model file not found: " + file_path, "V1ModelLoader");
            return false;
        }
    }
    
    LOG_DEBUG("All required model files found", "V1ModelLoader");
    return true;
}

float V1ModelLoader::PredictBetAmount(const std::vector<float>& betting_input) {
    if (!models_loaded_ || !betting_model_) {
        LOG_ERROR("Betting model not loaded", "V1ModelLoader");
        return 1.0f;  // 默认投注额
    }
    
    try {
        auto output = betting_model_->Predict(betting_input);
        if (output.empty()) {
            LOG_WARNING("Betting model returned empty output", "V1ModelLoader");
            return 1.0f;
        }
        
        // PPO模型通常输出动作概率分布或直接的动作值
        // 这里假设输出是单个值或需要进一步处理
        float predicted_bet = output[0];
        
        // 确保投注额为正值
        if (predicted_bet <= 0.0f) {
            LOG_DEBUG("Betting model predicted non-positive value: " + 
                     std::to_string(predicted_bet), "V1ModelLoader");
            return 1.0f;
        }
        
        return predicted_bet;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Betting prediction failed: " + std::string(e.what()), "V1ModelLoader");
        return 1.0f;
    }
}

bool V1ModelLoader::PredictTermination(const std::vector<float>& termination_input) {
    if (!models_loaded_ || !termination_model_ || !isolation_forest_) {
        LOG_ERROR("Termination models not loaded", "V1ModelLoader");
        return false;
    }
    
    try {
        // 使用DQN模型进行初步预测
        auto dqn_output = termination_model_->Predict(termination_input);
        if (dqn_output.empty()) {
            LOG_WARNING("DQN model returned empty output", "V1ModelLoader");
            return false;
        }
        
        // DQN输出：通常是Q值，选择最大Q值对应的动作
        bool dqn_decision = dqn_output[0] > 0.5f;  // 假设二分类阈值为0.5
        
        // 使用Isolation Forest进行异常检测
        auto isolation_output = isolation_forest_->Predict(termination_input);
        bool is_normal = !isolation_output.empty() && isolation_output[0] > 0.0f;
        
        // 组合决策：如果异常检测认为状态异常，则倾向于终止
        if (!is_normal) {
            LOG_DEBUG("Isolation Forest detected anomaly, suggesting termination", "V1ModelLoader");
            return true;
        }
        
        return dqn_decision;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Termination prediction failed: " + std::string(e.what()), "V1ModelLoader");
        return false;
    }
}

std::string V1ModelLoader::GetModelInfo() const {
    std::string info = "V1ModelLoader - Cluster " + std::to_string(cluster_id_) + 
                      " (" + cluster_path_ + ")";
    
    if (models_loaded_) {
        info += " [LOADED]";
        if (betting_model_) info += " Betting: " + betting_model_->GetModelInfo();
        if (termination_model_) info += " Termination: " + termination_model_->GetModelInfo();
        if (isolation_forest_) info += " IsolationForest: " + isolation_forest_->GetModelInfo();
    } else {
        info += " [NOT LOADED]";
    }
    
    return info;
}

} // namespace SlotSimulator
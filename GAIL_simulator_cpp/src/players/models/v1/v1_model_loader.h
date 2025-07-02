// src/players/models/v1/v1_model_loader.h
#pragma once

#include "../../../core/types.h"
#include "../../ml_interface/model_loader.h"
#include <vector>
#include <string>
#include <memory>
#include <unordered_map>

namespace SlotSimulator {

class V1ModelLoader {
public:
    explicit V1ModelLoader(const std::string& cluster_path);
    ~V1ModelLoader() = default;
    
    // 预测方法
    float PredictBetAmount(const std::vector<float>& betting_input);
    bool PredictTermination(const std::vector<float>& termination_input);
    
    // 模型状态检查
    bool IsLoaded() const { return models_loaded_; }
    std::string GetModelInfo() const;

private:
    std::string cluster_path_;
    bool models_loaded_;
    
    // 模型加载器
    std::unique_ptr<ModelLoader> betting_model_;
    std::unique_ptr<ModelLoader> termination_model_;
    std::unique_ptr<ModelLoader> isolation_forest_;
    
    // 模型文件路径
    std::string betting_model_path_;
    std::string termination_model_path_;
    std::string isolation_forest_path_;
    std::string metadata_path_;
    
    // 内部方法
    bool LoadModels();
    std::string BuildModelPath(const std::string& filename) const;
    bool ValidateModelFiles() const;
    void ExtractClusterInfo();
    
    // 集群信息
    int cluster_id_;
};

} // namespace SlotSimulator
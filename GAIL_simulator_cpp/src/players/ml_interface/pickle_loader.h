// src/players/ml_interface/pickle_loader.h
#pragma once

#include "model_loader.h"
#include <unordered_map>

namespace SlotSimulator {

// 简化的Pickle加载器，专门用于sklearn模型
class PickleLoader : public ModelLoader {
public:
    PickleLoader();
    ~PickleLoader() override;
    
    bool LoadModel(const std::string& model_path) override;
    std::vector<float> Predict(const std::vector<float>& input) override;
    bool IsLoaded() const override;
    std::string GetModelInfo() const override;

private:
    bool loaded_;
    std::string model_path_;
    std::string model_type_;
    
    // 简化的模型参数存储
    std::unordered_map<std::string, std::vector<float>> model_params_;
    
    // 简化的预测方法
    std::vector<float> PredictIsolationForest(const std::vector<float>& input);
    bool LoadIsolationForestModel(const std::string& file_path);
};

} // namespace SlotSimulator
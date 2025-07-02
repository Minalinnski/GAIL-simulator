// src/players/ml_interface/model_loader.h
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>

namespace SlotSimulator {

// 抽象模型加载器接口
class ModelLoader {
public:
    virtual ~ModelLoader() = default;
    
    // 加载模型文件
    virtual bool LoadModel(const std::string& model_path) = 0;
    
    // 模型推理
    virtual std::vector<float> Predict(const std::vector<float>& input) = 0;
    
    // 检查模型是否已加载
    virtual bool IsLoaded() const = 0;
    
    // 获取模型信息
    virtual std::string GetModelInfo() const = 0;
};

// 模型工厂
class ModelLoaderFactory {
public:
    enum class ModelType {
        PYTORCH,
        SKLEARN,
        UNKNOWN
    };
    
    static std::unique_ptr<ModelLoader> CreateLoader(ModelType type);
    static ModelType DetectModelType(const std::string& file_path);
};

} // namespace SlotSimulator
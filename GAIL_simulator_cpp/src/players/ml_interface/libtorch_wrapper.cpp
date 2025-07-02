// src/players/ml_interface/libtorch_wrapper.cpp
#include "libtorch_wrapper.h"
#include "../../utils/logger.h"

namespace SlotSimulator {

LibTorchWrapper::LibTorchWrapper() 
    : loaded_(false)
#ifdef ENABLE_LIBTORCH
    , device_(torch::kCPU)
#endif
{
#ifdef ENABLE_LIBTORCH
    // 检查CUDA是否可用
    if (torch::cuda::is_available()) {
        device_ = torch::kCUDA;
        LOG_INFO("CUDA available, using GPU for inference", "LibTorchWrapper");
    } else {
        LOG_INFO("CUDA not available, using CPU for inference", "LibTorchWrapper");
    }
#else
    LOG_WARNING("LibTorch support not compiled", "LibTorchWrapper");
#endif
}

LibTorchWrapper::~LibTorchWrapper() = default;

bool LibTorchWrapper::LoadModel(const std::string& model_path) {
#ifdef ENABLE_LIBTORCH
    try {
        module_ = std::make_unique<torch::jit::script::Module>(
            torch::jit::load(model_path, device_)
        );
        module_->eval();  // 设置为评估模式
        
        model_path_ = model_path;
        loaded_ = true;
        
        LOG_INFO("Successfully loaded PyTorch model: " + model_path, "LibTorchWrapper");
        return true;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to load PyTorch model " + model_path + ": " + e.what(), 
                 "LibTorchWrapper");
        loaded_ = false;
        return false;
    }
#else
    LOG_ERROR("LibTorch support not enabled, cannot load model: " + model_path, 
             "LibTorchWrapper");
    return false;
#endif
}

std::vector<float> LibTorchWrapper::Predict(const std::vector<float>& input) {
#ifdef ENABLE_LIBTORCH
    if (!loaded_ || !module_) {
        LOG_ERROR("Model not loaded", "LibTorchWrapper");
        return {};
    }
    
    try {
        // 转换输入为tensor
        torch::Tensor input_tensor = torch::from_blob(
            const_cast<float*>(input.data()), 
            {1, static_cast<long>(input.size())}, 
            torch::kFloat
        ).to(device_);
        
        // 执行推理
        std::vector<torch::jit::IValue> inputs{input_tensor};
        torch::Tensor output = module_->forward(inputs).toTensor();
        
        // 转换输出为vector
        output = output.to(torch::kCPU);
        std::vector<float> result(output.data_ptr<float>(), 
                                 output.data_ptr<float>() + output.numel());
        
        return result;
        
    } catch (const std::exception& e) {
        LOG_ERROR("PyTorch inference failed: " + std::string(e.what()), "LibTorchWrapper");
        return {};
    }
#else
    LOG_ERROR("LibTorch support not enabled", "LibTorchWrapper");
    return {};
#endif
}

bool LibTorchWrapper::IsLoaded() const {
    return loaded_;
}

std::string LibTorchWrapper::GetModelInfo() const {
    if (!loaded_) {
        return "Model not loaded";
    }
    
    std::string info = "PyTorch Model: " + model_path_;
#ifdef ENABLE_LIBTORCH
    info += ", Device: " + (device_.is_cuda() ? "CUDA" : "CPU");
#endif
    return info;
}

} // namespace SlotSimulator
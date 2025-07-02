// src/players/ml_interface/libtorch_wrapper.h
#pragma once

#include "model_loader.h"

#ifdef ENABLE_LIBTORCH
#include <torch/torch.h>
#include <torch/script.h>
#endif

namespace SlotSimulator {

class LibTorchWrapper : public ModelLoader {
public:
    LibTorchWrapper();
    ~LibTorchWrapper() override;
    
    bool LoadModel(const std::string& model_path) override;
    std::vector<float> Predict(const std::vector<float>& input) override;
    bool IsLoaded() const override;
    std::string GetModelInfo() const override;

private:
#ifdef ENABLE_LIBTORCH
    std::unique_ptr<torch::jit::script::Module> module_;
    torch::Device device_;
#endif
    bool loaded_;
    std::string model_path_;
};

} // namespace SlotSimulator
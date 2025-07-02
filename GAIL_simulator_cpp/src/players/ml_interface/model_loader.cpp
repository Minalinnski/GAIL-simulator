// src/players/ml_interface/model_loader.cpp
#include "model_loader.h"
#include "libtorch_wrapper.h"
#include "pickle_loader.h"
#include "../../utils/file_utils.h"
#include "../../utils/logger.h"

namespace SlotSimulator {

std::unique_ptr<ModelLoader> ModelLoaderFactory::CreateLoader(ModelType type) {
    switch (type) {
        case ModelType::PYTORCH:
#ifdef ENABLE_LIBTORCH
            return std::make_unique<LibTorchWrapper>();
#else
            LOG_ERROR("LibTorch support not enabled", "ModelLoaderFactory");
            return nullptr;
#endif
        case ModelType::SKLEARN:
            return std::make_unique<PickleLoader>();
        default:
            LOG_ERROR("Unknown model type", "ModelLoaderFactory");
            return nullptr;
    }
}

ModelLoaderFactory::ModelType ModelLoaderFactory::DetectModelType(const std::string& file_path) {
    std::string extension = FileUtils::GetExtension(file_path);
    
    if (extension == ".pth" || extension == ".pt") {
        return ModelType::PYTORCH;
    } else if (extension == ".pkl" || extension == ".pickle") {
        return ModelType::SKLEARN;
    }
    
    return ModelType::UNKNOWN;
}

} // namespace SlotSimulator
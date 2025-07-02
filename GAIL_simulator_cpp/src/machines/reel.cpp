// src/machines/reel.cpp
#include "reel.h"
#include <stdexcept>

namespace SlotSimulator {

Reel::Reel(const std::vector<int>& symbols) : symbols_(symbols) {
    if (symbols_.empty()) {
        throw std::invalid_argument("Reel cannot be empty");
    }
}

std::vector<int> Reel::GetSymbolsAtPosition(int position, int count) const {
    std::vector<int> result;
    result.reserve(count);
    
    int length = static_cast<int>(symbols_.size());
    for (int i = 0; i < count; ++i) {
        int index = (position + i) % length;
        result.push_back(symbols_[index]);
    }
    
    return result;
}

ReelSet::ReelSet(const std::unordered_map<std::string, std::vector<int>>& reels_config, 
                 int window_size) 
    : window_size_(window_size) {
    
    // 按reel名称排序以确保一致的顺序
    std::vector<std::string> reel_names;
    for (const auto& [name, symbols] : reels_config) {
        reel_names.push_back(name);
    }
    std::sort(reel_names.begin(), reel_names.end());
    
    // 创建轮盘
    for (const auto& name : reel_names) {
        auto it = reels_config.find(name);
        if (it != reels_config.end()) {
            reels_.push_back(std::make_unique<Reel>(it->second));
        }
    }
    
    if (reels_.empty()) {
        throw std::invalid_argument("ReelSet must contain at least one reel");
    }
}

SpinGrid ReelSet::GenerateGrid(std::mt19937_64& rng) const {
    int num_reels = static_cast<int>(reels_.size());
    SpinGrid grid;
    grid.reserve(num_reels * window_size_);
    
    // 为每个轮盘生成随机位置并获取符号
    for (const auto& reel : reels_) {
        std::uniform_int_distribution<int> dist(0, reel->GetLength() - 1);
        int position = dist(rng);
        
        auto symbols = reel->GetSymbolsAtPosition(position, window_size_);
        grid.insert(grid.end(), symbols.begin(), symbols.end());
    }
    
    return grid;
}

} // namespace SlotSimulator
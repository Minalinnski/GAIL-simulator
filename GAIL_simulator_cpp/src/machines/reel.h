// src/machines/reel.h
#pragma once

#include "../core/types.h"
#include <vector>
#include <string>
#include <unordered_map>
#include <random>

namespace SlotSimulator {

class Reel {
public:
    explicit Reel(const std::vector<int>& symbols);
    
    // 获取指定位置开始的连续符号
    std::vector<int> GetSymbolsAtPosition(int position, int count) const;
    
    // 获取轮盘长度
    int GetLength() const { return static_cast<int>(symbols_.size()); }
    
private:
    std::vector<int> symbols_;
};

class ReelSet {
public:
    explicit ReelSet(const std::unordered_map<std::string, std::vector<int>>& reels_config, 
                     int window_size);
    
    // 生成完整的符号网格
    SpinGrid GenerateGrid(std::mt19937_64& rng) const;
    
    int GetReelCount() const { return static_cast<int>(reels_.size()); }
    int GetWindowSize() const { return window_size_; }

private:
    std::vector<std::unique_ptr<Reel>> reels_;
    int window_size_;
};

} // namespace SlotSimulator

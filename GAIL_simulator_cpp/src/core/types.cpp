// src/core/types.cpp
#include "types.h"
#include "../utils/random_generator.h"
#include <algorithm>
#include <cmath>

namespace SlotSimulator {

float BalanceDistribution::GenerateBalance() const {
    if (std <= 0.0f) {
        return avg;  // 无随机性，直接返回平均值
    }
    
    // 使用正态分布生成余额
    auto& rng = RandomGenerator::GetInstance().GetThreadLocalRNG();
    std::normal_distribution<float> dist(avg, std);
    
    float balance = dist(rng);
    
    // 限制在min和max之间
    return std::clamp(balance, min, max);
}

} // namespace SlotSimulator
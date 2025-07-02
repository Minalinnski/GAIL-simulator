// src/utils/random_generator.h
#pragma once

#include <random>
#include <mutex>

namespace SlotSimulator {

class RandomGenerator {
public:
    static RandomGenerator& GetInstance();
    
    // 设置全局种子
    void SetSeed(uint64_t seed);
    
    // 获取线程安全的随机数
    int GetRandomInt(int min, int max);
    float GetRandomFloat(float min, float max);
    double GetRandomDouble(double min, double max);
    bool GetRandomBool(double probability = 0.5);
    
    // 获取线程本地的RNG（性能更好）
    std::mt19937_64& GetThreadLocalRNG();

private:
    RandomGenerator();
    
    std::mutex mutex_;
    std::mt19937_64 global_rng_;
    uint64_t base_seed_;
    
    static thread_local std::unique_ptr<std::mt19937_64> thread_rng_;
};

} // namespace SlotSimulator
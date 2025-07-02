// src/utils/random_generator.cpp
#include "random_generator.h"
#include <chrono>
#include <thread>

namespace SlotSimulator {

thread_local std::unique_ptr<std::mt19937_64> RandomGenerator::thread_rng_;

RandomGenerator::RandomGenerator() {
    auto now = std::chrono::high_resolution_clock::now();
    base_seed_ = static_cast<uint64_t>(now.time_since_epoch().count());
    global_rng_.seed(base_seed_);
}

RandomGenerator& RandomGenerator::GetInstance() {
    static RandomGenerator instance;
    return instance;
}

void RandomGenerator::SetSeed(uint64_t seed) {
    std::lock_guard<std::mutex> lock(mutex_);
    base_seed_ = seed;
    global_rng_.seed(seed);
}

int RandomGenerator::GetRandomInt(int min, int max) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::uniform_int_distribution<int> dist(min, max);
    return dist(global_rng_);
}

float RandomGenerator::GetRandomFloat(float min, float max) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::uniform_real_distribution<float> dist(min, max);
    return dist(global_rng_);
}

double RandomGenerator::GetRandomDouble(double min, double max) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::uniform_real_distribution<double> dist(min, max);
    return dist(global_rng_);
}

bool RandomGenerator::GetRandomBool(double probability) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::bernoulli_distribution dist(probability);
    return dist(global_rng_);
}

std::mt19937_64& RandomGenerator::GetThreadLocalRNG() {
    if (!thread_rng_) {
        // 为每个线程创建独立的RNG，使用线程ID作为种子偏移
        uint64_t thread_seed = base_seed_ + std::hash<std::thread::id>{}(std::this_thread::get_id());
        thread_rng_ = std::make_unique<std::mt19937_64>(thread_seed);
    }
    return *thread_rng_;
}

} // namespace SlotSimulator
// src/core/memory_manager.cpp
#include "memory_manager.h"

namespace SlotSimulator {

template<typename T>
ObjectPool<T>::ObjectPool(size_t initial_size) : active_count_(0) {
    factory_ = []() { return std::make_unique<T>(); };
    
    // 预填充池
    for (size_t i = 0; i < initial_size; ++i) {
        pool_.push(factory_());
    }
}

template<typename T>
std::unique_ptr<T> ObjectPool<T>::Acquire() {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::unique_ptr<T> obj;
    if (!pool_.empty()) {
        obj = std::move(pool_.front());
        pool_.pop();
    } else {
        obj = factory_();
    }
    
    active_count_++;
    return obj;
}

template<typename T>
void ObjectPool<T>::Release(std::unique_ptr<T> obj) {
    if (!obj) return;
    
    std::lock_guard<std::mutex> lock(mutex_);
    pool_.push(std::move(obj));
    active_count_--;
}

template<typename T>
size_t ObjectPool<T>::GetPoolSize() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return pool_.size();
}

template<typename T>
size_t ObjectPool<T>::GetActiveCount() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return active_count_;
}

MemoryManager& MemoryManager::GetInstance() {
    static MemoryManager instance;
    return instance;
}

void MemoryManager::Initialize(size_t session_pool_size, size_t spin_pool_size) {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    
    stats_.total_allocated = 0;
    stats_.total_deallocated = 0;
    stats_.current_usage = 0;
    stats_.peak_usage = 0;
    
    // 这里可以初始化各种对象池
    // 示例：session_pool_ = std::make_unique<ObjectPool<SessionStats>>(session_pool_size);
}

MemoryManager::MemoryStats MemoryManager::GetStats() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    return stats_;
}

} // namespace SlotSimulator

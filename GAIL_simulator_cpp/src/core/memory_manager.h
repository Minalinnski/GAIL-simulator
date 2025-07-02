// src/core/memory_manager.h
#pragma once

#include <memory>
#include <vector>
#include <queue>
#include <mutex>
#include <functional>

namespace SlotSimulator {

template<typename T>
class ObjectPool {
public:
    explicit ObjectPool(size_t initial_size = 100);
    ~ObjectPool() = default;
    
    // 获取对象
    std::unique_ptr<T> Acquire();
    
    // 归还对象
    void Release(std::unique_ptr<T> obj);
    
    // 获取统计信息
    size_t GetPoolSize() const;
    size_t GetActiveCount() const;

private:
    mutable std::mutex mutex_;
    std::queue<std::unique_ptr<T>> pool_;
    size_t active_count_;
    std::function<std::unique_ptr<T>()> factory_;
};

class MemoryManager {
public:
    static MemoryManager& GetInstance();
    
    // 预分配内存池
    void Initialize(size_t session_pool_size = 1000,
                   size_t spin_pool_size = 10000);
    
    // 获取统计信息
    struct MemoryStats {
        size_t total_allocated;
        size_t total_deallocated;
        size_t current_usage;
        size_t peak_usage;
    };
    
    MemoryStats GetStats() const;
    
private:
    MemoryManager() = default;
    mutable std::mutex stats_mutex_;
    MemoryStats stats_;
};

} // namespace SlotSimulator
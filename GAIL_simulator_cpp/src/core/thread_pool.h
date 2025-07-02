// src/core/thread_pool.h
#pragma once

#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <future>
#include <functional>
#include <atomic>
#include <deque>
#include <random>

namespace SlotSimulator {

// 工作队列（支持窃取）
template<typename T>
class WorkQueue {
public:
    WorkQueue() = default;
    
    // 禁用拷贝，允许移动
    WorkQueue(const WorkQueue&) = delete;
    WorkQueue& operator=(const WorkQueue&) = delete;
    WorkQueue(WorkQueue&&) = default;
    WorkQueue& operator=(WorkQueue&&) = default;
    
    void PushBack(T item) {
        std::lock_guard<std::mutex> lock(mutex_);
        deque_.push_back(std::move(item));
    }
    
    bool PopBack(T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return false;
        
        item = std::move(deque_.back());
        deque_.pop_back();
        return true;
    }
    
    bool PopFront(T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return false;
        
        item = std::move(deque_.front());
        deque_.pop_front();
        return true;
    }
    
    bool Empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return deque_.empty();
    }
    
    size_t Size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return deque_.size();
    }

private:
    mutable std::mutex mutex_;
    std::deque<T> deque_;
};

class ThreadPool {
public:
    explicit ThreadPool(int thread_count = 0);
    ~ThreadPool();
    
    // 禁用拷贝和移动
    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;
    
    // 提交任务
    template<typename F>
    void Submit(F&& task) {
        if (shutdown_) return;
        
        int target_thread = GetTargetThread();
        queues_[target_thread].PushBack(std::forward<F>(task));
        work_available_.notify_one();
    }
    
    // 批量提交任务
    template<typename Iterator>
    void SubmitBatch(Iterator begin, Iterator end) {
        if (shutdown_) return;
        
        int thread_idx = 0;
        for (auto it = begin; it != end; ++it) {
            queues_[thread_idx % thread_count_].PushBack(*it);
            thread_idx++;
        }
        work_available_.notify_all();
    }
    
    // 等待所有任务完成
    void WaitForCompletion();
    
    // 关闭线程池
    void Shutdown();
    
    // 获取统计信息
    struct Stats {
        int thread_count;
        std::vector<size_t> queue_sizes;
        int active_threads;
        long long total_tasks;
    };
    
    Stats GetStats() const;

private:
    int thread_count_;
    std::vector<std::thread> workers_;
    std::vector<WorkQueue<std::function<void()>>> queues_;
    
    std::condition_variable work_available_;
    std::mutex global_mutex_;
    std::atomic<bool> shutdown_;
    std::atomic<int> active_threads_;
    std::atomic<long long> total_tasks_;
    
    static thread_local int current_thread_id_;
    mutable std::mt19937 rng_;
    mutable std::mutex rng_mutex_;
    
    void WorkerThread(int thread_id);
    bool ExecuteLocalTask(int thread_id);
    bool StealTask(int thread_id);
    int GetTargetThread() const;
    bool AllQueuesEmpty() const;
};

} // namespace SlotSimulator
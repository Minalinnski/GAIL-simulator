// src/core/thread_pool.cpp
#include "thread_pool.h"
#include "../utils/logger.h"
#include <algorithm>

namespace SlotSimulator {

thread_local int ThreadPool::current_thread_id_ = -1;

ThreadPool::ThreadPool(int thread_count) 
    : shutdown_(false), active_threads_(0), total_tasks_(0), rng_(std::random_device{}()) {
    
    if (thread_count <= 0) {
        thread_count = std::thread::hardware_concurrency();
        if (thread_count == 0) thread_count = 4;
    }
    
    thread_count_ = thread_count;
    queues_.resize(thread_count_);
    workers_.reserve(thread_count_);
    
    // 创建工作线程
    for (int i = 0; i < thread_count_; ++i) {
        workers_.emplace_back(&ThreadPool::WorkerThread, this, i);
    }
    
    LOG_INFO("ThreadPool created with " + std::to_string(thread_count_) + " threads", "ThreadPool");
}

ThreadPool::~ThreadPool() {
    Shutdown();
}

void ThreadPool::WorkerThread(int thread_id) {
    current_thread_id_ = thread_id;
    
    LOG_DEBUG("Worker thread " + std::to_string(thread_id) + " started", "ThreadPool");
    
    while (!shutdown_) {
        bool task_executed = false;
        
        // 1. 优先执行本线程队列的任务
        task_executed = ExecuteLocalTask(thread_id);
        
        // 2. 如果本线程队列为空，尝试从其他线程窃取任务
        if (!task_executed) {
            task_executed = StealTask(thread_id);
        }
        
        // 3. 如果仍然没有任务，短暂等待
        if (!task_executed) {
            std::unique_lock<std::mutex> lock(global_mutex_);
            work_available_.wait_for(lock, std::chrono::milliseconds(5), 
                [this] { return shutdown_ || !AllQueuesEmpty(); });
        }
    }
    
    LOG_DEBUG("Worker thread " + std::to_string(thread_id) + " stopped", "ThreadPool");
}

bool ThreadPool::ExecuteLocalTask(int thread_id) {
    std::function<void()> task;
    if (queues_[thread_id].PopBack(task)) {
        active_threads_++;
        try {
            task();
            total_tasks_++;
        } catch (const std::exception& e) {
            LOG_ERROR("Task execution failed in thread " + std::to_string(thread_id) + 
                     ": " + e.what(), "ThreadPool");
        }
        active_threads_--;
        return true;
    }
    return false;
}

bool ThreadPool::StealTask(int thread_id) {
    // 尝试从其他线程窃取任务
    for (int attempts = 0; attempts < thread_count_ - 1; ++attempts) {
        int target = (thread_id + 1 + attempts) % thread_count_;
        
        std::function<void()> task;
        if (queues_[target].PopFront(task)) {
            active_threads_++;
            try {
                task();
                total_tasks_++;
            } catch (const std::exception& e) {
                LOG_ERROR("Stolen task execution failed in thread " + std::to_string(thread_id) + 
                         ": " + e.what(), "ThreadPool");
            }
            active_threads_--;
            return true;
        }
    }
    return false;
}

int ThreadPool::GetTargetThread() const {
    // 如果是工作线程调用，使用当前线程的队列
    if (current_thread_id_ >= 0 && current_thread_id_ < thread_count_) {
        return current_thread_id_;
    }
    
    // 否则随机选择一个线程
    std::lock_guard<std::mutex> lock(rng_mutex_);
    std::uniform_int_distribution<int> dist(0, thread_count_ - 1);
    return dist(rng_);
}

bool ThreadPool::AllQueuesEmpty() const {
    for (const auto& queue : queues_) {
        if (!queue.Empty()) return false;
    }
    return true;
}

void ThreadPool::WaitForCompletion() {
    while (!AllQueuesEmpty() || active_threads_ > 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    
    LOG_DEBUG("All tasks completed", "ThreadPool");
}

void ThreadPool::Shutdown() {
    if (shutdown_) return;
    
    shutdown_ = true;
    work_available_.notify_all();
    
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    LOG_INFO("ThreadPool shutdown. Total tasks: " + std::to_string(total_tasks_.load()), 
             "ThreadPool");
}

ThreadPool::Stats ThreadPool::GetStats() const {
    Stats stats;
    stats.thread_count = thread_count_;
    stats.active_threads = active_threads_;
    stats.total_tasks = total_tasks_;
    
    for (const auto& queue : queues_) {
        stats.queue_sizes.push_back(queue.Size());
    }
    
    return stats;
}

} // namespace SlotSimulator
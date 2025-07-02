// src/core/task_distributor.h
#pragma once

#include "types.h"
#include "thread_pool.h"
#include "../machines/machine_factory.h"
#include "../players/player_factory.h"
#include <vector>
#include <memory>
#include <atomic>
#include <mutex>
#include <unordered_map>

namespace SlotSimulator {

// 单个session任务
struct SessionTask {
    int task_id;
    int session_id;
    std::string player_version;
    std::string player_cluster;
    std::string machine_id;
    SimulationConfig sim_config;
    
    SessionTask() = default;
    SessionTask(int tid, int sid, const std::string& pv, const std::string& pc, 
               const std::string& mid, const SimulationConfig& config)
        : task_id(tid), session_id(sid), player_version(pv), player_cluster(pc)
        , machine_id(mid), sim_config(config) {}
};

// 线程本地实例池
class InstancePool {
public:
    InstancePool(std::shared_ptr<MachineFactory> machine_factory,
                std::shared_ptr<PlayerFactory> player_factory);
    
    // 获取实例（如果池中没有则创建新的）
    std::pair<PlayerInterface*, MachineInterface*> GetInstances(
        const std::string& player_version, 
        const std::string& player_cluster,
        const std::string& machine_id);
    
    // 归还实例到池中
    void ReturnInstances(PlayerInterface* player, MachineInterface* machine,
                        const std::string& player_version, 
                        const std::string& player_cluster,
                        const std::string& machine_id);
    
    // 清理池
    void Clear();

private:
    std::shared_ptr<MachineFactory> machine_factory_;
    std::shared_ptr<PlayerFactory> player_factory_;
    
    // 实例池：key = player_version_cluster_machine_id
    std::unordered_map<std::string, std::vector<std::unique_ptr<PlayerInterface>>> player_pools_;
    std::unordered_map<std::string, std::vector<std::unique_ptr<MachineInterface>>> machine_pools_;
    
    std::string MakeKey(const std::string& player_version, 
                       const std::string& player_cluster,
                       const std::string& machine_id) const;
};

class TaskDistributor {
public:
    using SessionResultCallback = std::function<void(const SessionStats&)>;
    
    TaskDistributor(std::shared_ptr<MachineFactory> machine_factory,
                   std::shared_ptr<PlayerFactory> player_factory,
                   int thread_count = 0);
    
    ~TaskDistributor() = default;
    
    // 生成session级别的任务
    std::vector<SessionTask> GenerateSessionTasks(
        const std::vector<MachineConfig>& machine_configs,
        const std::vector<PlayerConfig>& player_configs,
        const SimulationConfig& sim_config) const;
    
    // 执行所有session任务
    void ExecuteSessionTasks(const std::vector<SessionTask>& tasks,
                           SessionResultCallback result_callback);
    
    // 等待完成
    void WaitForCompletion();
    
    // 获取统计信息
    struct DistributorStats {
        int total_sessions;
        int completed_sessions;  // 改为普通int，在GetStats()中返回load()值
        int failed_sessions;     // 改为普通int，在GetStats()中返回load()值
        double total_execution_time;
        ThreadPool::Stats pool_stats;
    };
    
    DistributorStats GetStats() const; // 声明为函数，在cpp中实现

private:
    std::shared_ptr<MachineFactory> machine_factory_;
    std::shared_ptr<PlayerFactory> player_factory_;
    std::unique_ptr<ThreadPool> thread_pool_;
    
    mutable DistributorStats stats_;
    std::atomic<int> completed_sessions_atomic_;
    std::atomic<int> failed_sessions_atomic_;
    std::chrono::high_resolution_clock::time_point start_time_;
    
    // 线程本地实例池（每个线程一个）
    static thread_local std::unique_ptr<InstancePool> instance_pool_;
    
    // 执行单个session
    void ExecuteSession(const SessionTask& task, SessionResultCallback callback);
    
    // 获取或创建线程本地实例池
    InstancePool* GetInstancePool();
};

} // namespace SlotSimulator
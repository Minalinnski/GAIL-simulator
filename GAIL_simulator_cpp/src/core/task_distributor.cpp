// src/core/task_distributor.cpp
#include "task_distributor.h"
#include "session_controller.h"
#include "../utils/logger.h"
#include <sstream>

namespace SlotSimulator {

thread_local std::unique_ptr<InstancePool> TaskDistributor::instance_pool_;

InstancePool::InstancePool(std::shared_ptr<MachineFactory> machine_factory,
                          std::shared_ptr<PlayerFactory> player_factory)
    : machine_factory_(machine_factory), player_factory_(player_factory) {
}

std::string InstancePool::MakeKey(const std::string& player_version, 
                                 const std::string& player_cluster,
                                 const std::string& machine_id) const {
    return player_version + "_" + player_cluster + "_" + machine_id;
}

std::pair<PlayerInterface*, MachineInterface*> InstancePool::GetInstances(
    const std::string& player_version, 
    const std::string& player_cluster,
    const std::string& machine_id) {
    
    std::string key = MakeKey(player_version, player_cluster, machine_id);
    
    // 尝试从池中获取player实例
    PlayerInterface* player = nullptr;
    auto& player_pool = player_pools_[key];
    if (!player_pool.empty()) {
        auto player_ptr = std::move(player_pool.back());
        player_pool.pop_back();
        player = player_ptr.release();
    } else {
        // 创建新实例
        auto player_ptr = player_factory_->CreatePlayer(player_version, player_cluster);
        player = player_ptr.release();
    }
    
    // 尝试从池中获取machine实例
    MachineInterface* machine = nullptr;
    auto& machine_pool = machine_pools_[key];
    if (!machine_pool.empty()) {
        auto machine_ptr = std::move(machine_pool.back());
        machine_pool.pop_back();
        machine = machine_ptr.release();
    } else {
        // 创建新实例
        auto machine_ptr = machine_factory_->CreateMachine(machine_id);
        machine = machine_ptr.release();
    }
    
    return {player, machine};
}

void InstancePool::ReturnInstances(PlayerInterface* player, MachineInterface* machine,
                                  const std::string& player_version, 
                                  const std::string& player_cluster,
                                  const std::string& machine_id) {
    std::string key = MakeKey(player_version, player_cluster, machine_id);
    
    // 限制池大小，避免内存过度使用
    const size_t MAX_POOL_SIZE = 3;
    
    if (player && player_pools_[key].size() < MAX_POOL_SIZE) {
        player_pools_[key].emplace_back(player);
    } else {
        delete player;
    }
    
    if (machine && machine_pools_[key].size() < MAX_POOL_SIZE) {
        machine_pools_[key].emplace_back(machine);
    } else {
        delete machine;
    }
}

void InstancePool::Clear() {
    player_pools_.clear();
    machine_pools_.clear();
}

TaskDistributor::TaskDistributor(std::shared_ptr<MachineFactory> machine_factory,
                                std::shared_ptr<PlayerFactory> player_factory,
                                int thread_count)
    : machine_factory_(machine_factory), player_factory_(player_factory)
    , completed_sessions_atomic_(0), failed_sessions_atomic_(0) {
    
    thread_pool_ = std::make_unique<ThreadPool>(thread_count);
    
    LOG_INFO("TaskDistributor initialized", "TaskDistributor");
}

std::vector<SessionTask> TaskDistributor::GenerateSessionTasks(
    const std::vector<MachineConfig>& machine_configs,
    const std::vector<PlayerConfig>& player_configs,
    const SimulationConfig& sim_config) const {
    
    std::vector<SessionTask> tasks;
    int task_id = 0;
    
    // 生成所有session任务：X机器 × Y玩家 × N session
    for (const auto& machine_config : machine_configs) {
        for (const auto& player_config : player_configs) {
            for (int session_num = 0; session_num < sim_config.sessions_per_pair; ++session_num) {
                SessionTask task(
                    task_id++,
                    session_num,
                    player_config.model_version,
                    player_config.cluster_id,
                    machine_config.machine_id,
                    sim_config
                );
                tasks.push_back(task);
            }
        }
    }
    
    LOG_INFO("Generated " + std::to_string(tasks.size()) + " session tasks (" +
             std::to_string(machine_configs.size()) + " machines × " +
             std::to_string(player_configs.size()) + " players × " +
             std::to_string(sim_config.sessions_per_pair) + " sessions)", "TaskDistributor");
    
    return tasks;
}

void TaskDistributor::ExecuteSessionTasks(const std::vector<SessionTask>& tasks,
                                         SessionResultCallback result_callback) {
    
    start_time_ = std::chrono::high_resolution_clock::now();
    stats_.total_sessions = static_cast<int>(tasks.size());
    completed_sessions_atomic_ = 0;
    failed_sessions_atomic_ = 0;
    
    LOG_INFO("Starting execution of " + std::to_string(tasks.size()) + " session tasks", 
             "TaskDistributor");
    
    // 创建任务函数并批量提交
    std::vector<std::function<void()>> task_functions;
    task_functions.reserve(tasks.size());
    
    for (const auto& task : tasks) {
        task_functions.emplace_back([this, task, result_callback]() {
            this->ExecuteSession(task, result_callback);
        });
    }
    
    thread_pool_->SubmitBatch(task_functions.begin(), task_functions.end());
    
    LOG_INFO("All session tasks submitted to thread pool", "TaskDistributor");
}

InstancePool* TaskDistributor::GetInstancePool() {
    if (!instance_pool_) {
        instance_pool_ = std::make_unique<InstancePool>(machine_factory_, player_factory_);
    }
    return instance_pool_.get();
}

void TaskDistributor::ExecuteSession(const SessionTask& task, SessionResultCallback callback) {
    try {
        // 从线程本地池获取实例
        auto pool = GetInstancePool();
        auto [player, machine] = pool->GetInstances(
            task.player_version, task.player_cluster, task.machine_id);
        
        if (!player || !machine) {
            LOG_ERROR("Failed to get instances for task " + std::to_string(task.task_id), 
                     "TaskDistributor");
            failed_sessions_atomic_++;
            return;
        }
        
        // 重置状态
        player->Reset();
        machine->ResetState();
        
        // 生成session ID
        std::ostringstream session_id_stream;
        session_id_stream << task.player_version << "_" << task.player_cluster 
                         << "_" << task.machine_id << "_" << task.session_id;
        std::string session_id = session_id_stream.str();
        
        // 执行session
        SessionController session_controller{
            std::unique_ptr<PlayerInterface>(player),
            std::unique_ptr<MachineInterface>(machine)
        };
        
        SessionStats session_stats = session_controller.RunSession(
            session_id, 
            task.sim_config.max_spins_per_session, 
            task.sim_config.max_session_duration
        );
        
        // 获取并归还实例到池中
        auto released_player = session_controller.ReleasePlayer();
        auto released_machine = session_controller.ReleaseMachine();
        pool->ReturnInstances(released_player, released_machine,
                             task.player_version, task.player_cluster, task.machine_id);
        
        // 回调返回结果
        if (callback) {
            callback(session_stats);
        }
        
        completed_sessions_atomic_++;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Session task " + std::to_string(task.task_id) + " failed: " + e.what(), 
                 "TaskDistributor");
        failed_sessions_atomic_++;
    }
}

TaskDistributor::DistributorStats TaskDistributor::GetStats() const {
    DistributorStats result = stats_;
    result.completed_sessions = completed_sessions_atomic_.load();
    result.failed_sessions = failed_sessions_atomic_.load();
    return result;
}

void TaskDistributor::WaitForCompletion() {
    thread_pool_->WaitForCompletion();
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time_);
    stats_.total_execution_time = duration.count() / 1000.0;
    stats_.pool_stats = thread_pool_->GetStats();
    
    LOG_INFO("All session tasks completed. Stats - Completed: " + 
             std::to_string(completed_sessions_atomic_.load()) + 
             ", Failed: " + std::to_string(failed_sessions_atomic_.load()) +
             ", Time: " + std::to_string(stats_.total_execution_time) + "s", 
             "TaskDistributor");
}

} // namespace SlotSimulator
// src/core/types.h
#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include <memory>

namespace SlotSimulator {

// 前向声明
class Player;
class SlotMachine;

// 基础类型定义
using SpinGrid = std::vector<int>;  // 扁平化的符号网格 (row-major order)
using PaylineIndices = std::vector<int>;
using PayoutArray = std::vector<float>;
using BetOptions = std::vector<float>;

// Spin结果结构
struct SpinResult {
    SpinGrid grid;              // 符号网格 (3x5 = 15个元素)
    float bet_amount;           // 投注额
    float win_amount;           // 中奖金额
    float profit;               // 利润 (win - bet)
    bool trigger_free_spins;    // 是否触发免费旋转
    int free_spins_remaining;   // 剩余免费旋转次数
    bool in_free_spins;         // 是否在免费旋转中
    double timestamp;           // 时间戳
    int spin_number;            // 旋转编号
    
    SpinResult() 
        : bet_amount(0.0f), win_amount(0.0f), profit(0.0f)
        , trigger_free_spins(false), free_spins_remaining(0)
        , in_free_spins(false), timestamp(0.0), spin_number(0) {}
};

// 玩家决策结果
struct PlayerDecision {
    float bet_amount;       // 投注额 (0表示结束游戏)
    float delay_time;       // 延迟时间(秒)
    bool continue_playing;  // 是否继续游戏
    
    PlayerDecision(float bet = 0.0f, float delay = 0.0f) 
        : bet_amount(bet), delay_time(delay)
        , continue_playing(bet > 0.0f) {}
};

// Session统计数据
struct SessionStats {
    std::string session_id;
    std::string player_id;
    std::string machine_id;
    
    int total_spins;
    float total_bet;
    float total_win;
    float total_profit;
    float initial_balance;
    float final_balance;
    double session_duration;
    
    // 扩展统计
    int free_spins_triggered;
    int free_spins_played;
    float max_win;
    float max_loss_streak;
    float rtp;  // Return to Player
    
    SessionStats() 
        : total_spins(0), total_bet(0.0f), total_win(0.0f), total_profit(0.0f)
        , initial_balance(0.0f), final_balance(0.0f), session_duration(0.0)
        , free_spins_triggered(0), free_spins_played(0)
        , max_win(0.0f), max_loss_streak(0.0f), rtp(0.0f) {}
};

// Session数据，用于传递给玩家做决策
struct SessionData {
    float current_balance;
    std::vector<SpinResult> recent_spins;  // 最近的旋转记录
    SessionStats stats;
    BetOptions available_bets;
    bool in_free_spins;
    int free_spins_remaining;
    
    SessionData() : current_balance(0.0f), in_free_spins(false), free_spins_remaining(0) {}
};

// 任务信息结构
struct TaskInfo {
    int task_id;
    std::string player_version;     // "v1", "v2", "random"
    std::string player_cluster;     // "cluster_0", "cluster_1", etc.
    std::string machine_id;
    int session_count;              // 该任务需要运行多少个session
    
    TaskInfo() : task_id(0), session_count(0) {}
    TaskInfo(int id, const std::string& pv, const std::string& pc, 
             const std::string& mid, int count)
        : task_id(id), player_version(pv), player_cluster(pc)
        , machine_id(mid), session_count(count) {}
};

// 任务结果
struct TaskResult {
    TaskInfo task_info;
    std::vector<SessionStats> session_results;
    bool success;
    std::string error_message;
    
    TaskResult() : success(false) {}
    explicit TaskResult(const TaskInfo& info) 
        : task_info(info), success(false) {}
};

// 配置结构体
struct MachineConfig {
    std::string machine_id;
    int free_spins_count;
    float free_spins_multiplier;
    std::vector<int> wild_symbols;
    int scatter_symbol;
    int window_size;  // 通常是3(行数)
    
    // Reels配置 - 支持normal和bonus两种模式
    std::unordered_map<std::string, std::unordered_map<std::string, std::vector<int>>> reels;
    
    // Paylines配置
    std::vector<PaylineIndices> paylines;
    
    // Pay table: symbol -> [3_match, 4_match, 5_match]
    std::unordered_map<std::string, PayoutArray> pay_table;
    
    // Bet table: currency -> bet_options
    std::unordered_map<std::string, BetOptions> bet_table;
};

struct PlayerConfig {
    std::string player_id;
    std::string model_version;      // "v1", "v2", "random"
    std::string cluster_id;         // "cluster_0", "cluster_1", etc.
    float initial_balance;
    std::string currency;
    int active_lines;
    
    // 模型特定配置，键为 model_config_{version}
    std::unordered_map<std::string, std::unordered_map<std::string, std::string>> model_configs;
};

struct SimulationConfig {
    // 文件配置
    struct FileConfig {
        std::string directory;
        std::string selection_mode;  // "all", "include", "exclude"  
        std::vector<std::string> files;
    };
    
    FileConfig machines_config;
    FileConfig players_config;
    
    // 模拟参数
    int sessions_per_pair;      // N - 每个player-machine组合的session数量
    int max_spins_per_session;
    float max_session_duration;
    bool use_concurrency;
    int thread_count;           // 线程数量
    
    // 输出配置
    std::string output_base_dir;
    bool record_raw_spins;
    bool generate_reports;
    bool enable_s3_upload;
    std::string s3_bucket;
    int batch_write_size;
};

} // namespace SlotSimulator

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
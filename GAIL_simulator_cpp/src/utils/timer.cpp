// src/utils/timer.h
#pragma once

#include <chrono>
#include <string>
#include <unordered_map>

namespace SlotSimulator {

class Timer {
public:
    Timer() = default;
    
    // 开始计时
    void Start(const std::string& name = "default");
    
    // 停止计时并返回经过的时间（毫秒）
    double Stop(const std::string& name = "default");
    
    // 获取当前经过的时间（不停止计时）
    double Elapsed(const std::string& name = "default") const;
    
    // 重置所有计时器
    void Reset();
    
    // 获取所有计时器的统计信息
    std::unordered_map<std::string, double> GetAllTimings() const;

private:
    std::unordered_map<std::string, std::chrono::high_resolution_clock::time_point> start_times_;
    std::unordered_map<std::string, double> elapsed_times_;
};

class ScopedTimer {
public:
    explicit ScopedTimer(const std::string& name, Timer& timer);
    ~ScopedTimer();

private:
    std::string name_;
    Timer& timer_;
};

// 便捷宏
#define SCOPED_TIMER(timer, name) ScopedTimer _scoped_timer(name, timer)

} // namespace SlotSimulator
// src/utils/timer.cpp
#include "timer.h"

namespace SlotSimulator {

void Timer::Start(const std::string& name) {
    start_times_[name] = std::chrono::high_resolution_clock::now();
}

double Timer::Stop(const std::string& name) {
    auto it = start_times_.find(name);
    if (it == start_times_.end()) {
        return 0.0;
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - it->second);
    
    double elapsed_ms = duration.count() / 1000.0;
    elapsed_times_[name] = elapsed_ms;
    start_times_.erase(it);
    
    return elapsed_ms;
}

double Timer::Elapsed(const std::string& name) const {
    auto it = start_times_.find(name);
    if (it == start_times_.end()) {
        return 0.0;
    }
    
    auto current_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        current_time - it->second);
    
    return duration.count() / 1000.0;
}

void Timer::Reset() {
    start_times_.clear();
    elapsed_times_.clear();
}

std::unordered_map<std::string, double> Timer::GetAllTimings() const {
    return elapsed_times_;
}

ScopedTimer::ScopedTimer(const std::string& name, Timer& timer) 
    : name_(name), timer_(timer) {
    timer_.Start(name_);
}

ScopedTimer::~ScopedTimer() {
    timer_.Stop(name_);
}

} // namespace SlotSimulator
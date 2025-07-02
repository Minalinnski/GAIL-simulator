// logger.h
#pragma once

#include <string>
#include <fstream>
#include <mutex>
#include <memory>
#include <sstream>

namespace SlotSimulator {

enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARNING = 2,
    ERROR = 3
};

class Logger {
public:
    static Logger& GetInstance();
    
    // 配置日志系统
    void Initialize(const std::string& log_file_path = "", 
                   LogLevel console_level = LogLevel::INFO,
                   LogLevel file_level = LogLevel::DEBUG,
                   bool enable_console = true,
                   bool enable_file = true);
    
    // 日志记录方法
    void Log(LogLevel level, const std::string& message, 
             const std::string& component = "");
    
    // 便捷方法
    void Debug(const std::string& message, const std::string& component = "");
    void Info(const std::string& message, const std::string& component = "");
    void Warning(const std::string& message, const std::string& component = "");
    void Error(const std::string& message, const std::string& component = "");
    
    // 设置日志级别
    void SetConsoleLevel(LogLevel level) { console_level_ = level; }
    void SetFileLevel(LogLevel level) { file_level_ = level; }
    
    // 关闭日志系统
    void Shutdown();

private:
    Logger() = default;
    ~Logger();
    
    std::mutex mutex_;
    std::unique_ptr<std::ofstream> file_stream_;
    std::string log_file_path_;
    
    LogLevel console_level_ = LogLevel::INFO;
    LogLevel file_level_ = LogLevel::DEBUG;
    bool enable_console_ = true;
    bool enable_file_ = false;
    
    std::string GetTimestamp() const;
    std::string LogLevelToString(LogLevel level) const;
    void WriteToConsole(const std::string& formatted_message) const;
    void WriteToFile(const std::string& formatted_message);
};

// 便捷宏定义
#define LOG_DEBUG(msg, component) Logger::GetInstance().Debug(msg, component)
#define LOG_INFO(msg, component) Logger::GetInstance().Info(msg, component)
#define LOG_WARNING(msg, component) Logger::GetInstance().Warning(msg, component)
#define LOG_ERROR(msg, component) Logger::GetInstance().Error(msg, component)

// 简化版本（不需要指定组件）
#define LOG_D(msg) LOG_DEBUG(msg, "")
#define LOG_I(msg) LOG_INFO(msg, "")
#define LOG_W(msg) LOG_WARNING(msg, "")
#define LOG_E(msg) LOG_ERROR(msg, "")

} // namespace SlotSimulator

// logger.cpp
#include "logger.h"
#include <iostream>
#include <chrono>
#include <iomanip>
#include <filesystem>

namespace SlotSimulator {

Logger& Logger::GetInstance() {
    static Logger instance;
    return instance;
}

Logger::~Logger() {
    Shutdown();
}

void Logger::Initialize(const std::string& log_file_path, 
                       LogLevel console_level,
                       LogLevel file_level,
                       bool enable_console,
                       bool enable_file) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    console_level_ = console_level;
    file_level_ = file_level;
    enable_console_ = enable_console;
    enable_file_ = enable_file;
    
    if (enable_file && !log_file_path.empty()) {
        log_file_path_ = log_file_path;
        
        // 创建日志目录（如果不存在）
        std::filesystem::path file_path(log_file_path_);
        if (file_path.has_parent_path()) {
            std::filesystem::create_directories(file_path.parent_path());
        }
        
        file_stream_ = std::make_unique<std::ofstream>(log_file_path_, 
                                                      std::ios::out | std::ios::app);
        if (!file_stream_->is_open()) {
            std::cerr << "Failed to open log file: " << log_file_path_ << std::endl;
            enable_file_ = false;
        } else {
            Info("Logger initialized", "Logger");
        }
    }
}

void Logger::Log(LogLevel level, const std::string& message, const std::string& component) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string timestamp = GetTimestamp();
    std::string level_str = LogLevelToString(level);
    
    std::ostringstream oss;
    oss << "[" << timestamp << "] [" << level_str << "]";
    if (!component.empty()) {
        oss << " [" << component << "]";
    }
    oss << " " << message;
    
    std::string formatted_message = oss.str();
    
    // 输出到控制台
    if (enable_console_ && level >= console_level_) {
        WriteToConsole(formatted_message);
    }
    
    // 输出到文件
    if (enable_file_ && level >= file_level_) {
        WriteToFile(formatted_message);
    }
}

void Logger::Debug(const std::string& message, const std::string& component) {
    Log(LogLevel::DEBUG, message, component);
}

void Logger::Info(const std::string& message, const std::string& component) {
    Log(LogLevel::INFO, message, component);
}

void Logger::Warning(const std::string& message, const std::string& component) {
    Log(LogLevel::WARNING, message, component);
}

void Logger::Error(const std::string& message, const std::string& component) {
    Log(LogLevel::ERROR, message, component);
}

void Logger::Shutdown() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (file_stream_ && file_stream_->is_open()) {
        Info("Logger shutting down", "Logger");
        file_stream_->close();
        file_stream_.reset();
    }
}

std::string Logger::GetTimestamp() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    oss << "." << std::setfill('0') << std::setw(3) << ms.count();
    
    return oss.str();
}

std::string Logger::LogLevelToString(LogLevel level) const {
    switch (level) {
        case LogLevel::DEBUG:   return "DEBUG";
        case LogLevel::INFO:    return "INFO ";
        case LogLevel::WARNING: return "WARN ";
        case LogLevel::ERROR:   return "ERROR";
        default:               return "UNKNW";
    }
}

void Logger::WriteToConsole(const std::string& formatted_message) const {
    std::cout << formatted_message << std::endl;
}

void Logger::WriteToFile(const std::string& formatted_message) {
    if (file_stream_ && file_stream_->is_open()) {
        *file_stream_ << formatted_message << std::endl;
        file_stream_->flush();  // 确保立即写入
    }
}

} // namespace SlotSimulator
// src/core/data_writer.h
#pragma once

#include "types.h"
#include <vector>
#include <string>
#include <fstream>
#include <mutex>

namespace SlotSimulator {

class DataWriter {
public:
    explicit DataWriter(const SimulationConfig& config);
    ~DataWriter();
    
    // 写入session统计数据
    void WriteSessionStats(const std::vector<SessionStats>& session_stats);
    
    // 写入原始spin数据（可选）
    void WriteRawSpins(const std::vector<SpinResult>& spins, 
                      const std::string& session_id);
    
    // 生成汇总报告
    void GenerateSummaryReport(const std::vector<SessionStats>& session_stats);
    
    // 批量上传到S3（如果启用）
    void UploadToS3();

private:
    SimulationConfig config_;
    std::string output_dir_;
    std::mutex write_mutex_;
    
    // 文件流
    std::unique_ptr<std::ofstream> session_stats_file_;
    std::unique_ptr<std::ofstream> raw_spins_file_;
    
    // 批处理缓冲区
    std::vector<SessionStats> session_buffer_;
    std::vector<SpinResult> spins_buffer_;
    
    // 内部方法
    void InitializeOutputDirectory();
    void InitializeFiles();
    void WriteSessionStatsHeader();
    void WriteRawSpinsHeader();
    void FlushBuffers();
    std::string SessionStatsToCSV(const SessionStats& stats) const;
    std::string SpinResultToCSV(const SpinResult& spin, const std::string& session_id) const;
    void GeneratePlayerReport(const std::vector<SessionStats>& session_stats);
    void GenerateMachineReport(const std::vector<SessionStats>& session_stats);
};

} // namespace SlotSimulator
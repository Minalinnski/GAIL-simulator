// src/core/data_writer.cpp
#include "data_writer.h"
#include "../utils/logger.h"
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <map>
#include <algorithm>
#include <numeric>

namespace SlotSimulator {

DataWriter::DataWriter(const SimulationConfig& config) : config_(config) {
    InitializeOutputDirectory();
    InitializeFiles();
    
    LOG_INFO("DataWriter initialized - Output directory: " + output_dir_, "DataWriter");
}

DataWriter::~DataWriter() {
    FlushBuffers();
    
    if (session_stats_file_ && session_stats_file_->is_open()) {
        session_stats_file_->close();
    }
    if (raw_spins_file_ && raw_spins_file_->is_open()) {
        raw_spins_file_->close();
    }
    
    LOG_DEBUG("DataWriter destroyed", "DataWriter");
}

void DataWriter::InitializeOutputDirectory() {
    // 创建带时间戳的输出目录
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::ostringstream oss;
    oss << config_.output_base_dir << "/simulation_" 
        << std::put_time(std::localtime(&time_t), "%Y%m%d_%H%M%S");
    
    output_dir_ = oss.str();
    
    try {
        std::filesystem::create_directories(output_dir_);
        std::filesystem::create_directories(output_dir_ + "/sessions");
        std::filesystem::create_directories(output_dir_ + "/reports");
        if (config_.record_raw_spins) {
            std::filesystem::create_directories(output_dir_ + "/raw_spins");
        }
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to create output directories: " + std::string(e.what()), "DataWriter");
        throw;
    }
}

void DataWriter::InitializeFiles() {
    try {
        // 初始化session统计文件
        std::string session_stats_path = output_dir_ + "/sessions/session_stats.csv";
        session_stats_file_ = std::make_unique<std::ofstream>(session_stats_path);
        if (!session_stats_file_->is_open()) {
            throw std::runtime_error("Failed to open session stats file: " + session_stats_path);
        }
        WriteSessionStatsHeader();
        
        // 初始化原始spin数据文件（如果启用）
        if (config_.record_raw_spins) {
            std::string raw_spins_path = output_dir_ + "/raw_spins/raw_spins.csv";
            raw_spins_file_ = std::make_unique<std::ofstream>(raw_spins_path);
            if (!raw_spins_file_->is_open()) {
                throw std::runtime_error("Failed to open raw spins file: " + raw_spins_path);
            }
            WriteRawSpinsHeader();
        }
        
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to initialize output files: " + std::string(e.what()), "DataWriter");
        throw;
    }
}

void DataWriter::WriteSessionStatsHeader() {
    *session_stats_file_ << "session_id,player_id,machine_id,total_spins,total_bet,total_win,"
                        << "total_profit,initial_balance,final_balance,session_duration,"
                        << "free_spins_triggered,free_spins_played,max_win,max_loss_streak,rtp\n";
}

void DataWriter::WriteRawSpinsHeader() {
    if (raw_spins_file_) {
        *raw_spins_file_ << "session_id,spin_number,bet_amount,win_amount,profit,"
                        << "trigger_free_spins,free_spins_remaining,in_free_spins,"
                        << "timestamp,grid\n";
    }
}

void DataWriter::WriteSessionStats(const std::vector<SessionStats>& session_stats) {
    std::lock_guard<std::mutex> lock(write_mutex_);
    
    if (!session_stats_file_ || !session_stats_file_->is_open()) {
        LOG_ERROR("Session stats file is not open", "DataWriter");
        return;
    }
    
    for (const auto& stats : session_stats) {
        *session_stats_file_ << SessionStatsToCSV(stats) << "\n";
        
        // 定期刷新
        if (session_stats.size() % 100 == 0) {
            session_stats_file_->flush();
        }
    }
    
    session_stats_file_->flush();
    LOG_DEBUG("Wrote " + std::to_string(session_stats.size()) + " session stats", "DataWriter");
}

void DataWriter::WriteRawSpins(const std::vector<SpinResult>& spins, 
                              const std::string& session_id) {
    if (!config_.record_raw_spins || !raw_spins_file_ || !raw_spins_file_->is_open()) {
        return;
    }
    
    std::lock_guard<std::mutex> lock(write_mutex_);
    
    for (const auto& spin : spins) {
        *raw_spins_file_ << SpinResultToCSV(spin, session_id) << "\n";
    }
    
    raw_spins_file_->flush();
}

std::string DataWriter::SessionStatsToCSV(const SessionStats& stats) const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6)
        << stats.session_id << ","
        << stats.player_id << ","
        << stats.machine_id << ","
        << stats.total_spins << ","
        << stats.total_bet << ","
        << stats.total_win << ","
        << stats.total_profit << ","
        << stats.initial_balance << ","
        << stats.final_balance << ","
        << stats.session_duration << ","
        << stats.free_spins_triggered << ","
        << stats.free_spins_played << ","
        << stats.max_win << ","
        << stats.max_loss_streak << ","
        << stats.rtp;
    
    return oss.str();
}

std::string DataWriter::SpinResultToCSV(const SpinResult& spin, const std::string& session_id) const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6)
        << session_id << ","
        << spin.spin_number << ","
        << spin.bet_amount << ","
        << spin.win_amount << ","
        << spin.profit << ","
        << (spin.trigger_free_spins ? 1 : 0) << ","
        << spin.free_spins_remaining << ","
        << (spin.in_free_spins ? 1 : 0) << ","
        << spin.timestamp << ",\"";
    
    // 序列化grid数组
    for (size_t i = 0; i < spin.grid.size(); ++i) {
        if (i > 0) oss << ",";
        oss << spin.grid[i];
    }
    oss << "\"";
    
    return oss.str();
}

void DataWriter::GenerateSummaryReport(const std::vector<SessionStats>& session_stats) {
    if (!config_.generate_reports || session_stats.empty()) {
        return;
    }
    
    LOG_INFO("Generating summary reports", "DataWriter");
    
    try {
        GeneratePlayerReport(session_stats);
        GenerateMachineReport(session_stats);
        
        // 生成总体汇总
        std::string summary_path = output_dir_ + "/reports/summary.txt";
        std::ofstream summary_file(summary_path);
        
        if (summary_file.is_open()) {
            summary_file << "Slot Machine Simulation Summary\n";
            summary_file << "================================\n\n";
            
            double total_bet = 0, total_win = 0, total_profit = 0;
            int total_spins = 0;
            double total_duration = 0;
            
            for (const auto& stats : session_stats) {
                total_bet += stats.total_bet;
                total_win += stats.total_win;
                total_profit += stats.total_profit;
                total_spins += stats.total_spins;
                total_duration += stats.session_duration;
            }
            
            double overall_rtp = total_bet > 0 ? total_win / total_bet : 0.0;
            
            summary_file << "Total Sessions: " << session_stats.size() << "\n";
            summary_file << "Total Spins: " << total_spins << "\n";
            summary_file << "Total Bet: $" << std::fixed << std::setprecision(2) << total_bet << "\n";
            summary_file << "Total Win: $" << total_win << "\n";
            summary_file << "Total Profit: $" << total_profit << "\n";
            summary_file << "Overall RTP: " << std::setprecision(4) << (overall_rtp * 100) << "%\n";
            summary_file << "Total Duration: " << std::setprecision(2) << total_duration << " seconds\n";
            summary_file << "Average Session Duration: " << 
                           (total_duration / session_stats.size()) << " seconds\n";
            
            summary_file.close();
        }
        
        LOG_INFO("Summary reports generated successfully", "DataWriter");
        
    } catch (const std::exception& e) {
        LOG_ERROR("Failed to generate summary reports: " + std::string(e.what()), "DataWriter");
    }
}

void DataWriter::GeneratePlayerReport(const std::vector<SessionStats>& session_stats) {
    std::map<std::string, std::vector<const SessionStats*>> player_groups;
    
    // 按玩家分组
    for (const auto& stats : session_stats) {
        player_groups[stats.player_id].push_back(&stats);
    }
    
    std::string report_path = output_dir_ + "/reports/player_report.csv";
    std::ofstream report_file(report_path);
    
    if (!report_file.is_open()) {
        LOG_ERROR("Failed to open player report file: " + report_path, "DataWriter");
        return;
    }
    
    report_file << "player_id,session_count,total_spins,total_bet,total_win,total_profit,"
               << "avg_rtp,avg_session_duration,max_win,min_profit\n";
    
    for (const auto& [player_id, sessions] : player_groups) {
        double total_bet = 0, total_win = 0, total_profit = 0, total_duration = 0;
        int total_spins = 0;
        double max_win = 0, min_profit = 0;
        
        for (const auto* stats : sessions) {
            total_bet += stats->total_bet;
            total_win += stats->total_win;
            total_profit += stats->total_profit;
            total_spins += stats->total_spins;
            total_duration += stats->session_duration;
            max_win = std::max(max_win, static_cast<double>(stats->max_win));
            min_profit = std::min(min_profit, static_cast<double>(stats->total_profit));
        }
        
        double avg_rtp = total_bet > 0 ? total_win / total_bet : 0.0;
        double avg_duration = total_duration / sessions.size();
        
        report_file << std::fixed << std::setprecision(6)
                   << player_id << ","
                   << sessions.size() << ","
                   << total_spins << ","
                   << total_bet << ","
                   << total_win << ","
                   << total_profit << ","
                   << avg_rtp << ","
                   << avg_duration << ","
                   << max_win << ","
                   << min_profit << "\n";
    }
    
    report_file.close();
}

void DataWriter::GenerateMachineReport(const std::vector<SessionStats>& session_stats) {
    std::map<std::string, std::vector<const SessionStats*>> machine_groups;
    
    // 按机器分组
    for (const auto& stats : session_stats) {
        machine_groups[stats.machine_id].push_back(&stats);
    }
    
    std::string report_path = output_dir_ + "/reports/machine_report.csv";
    std::ofstream report_file(report_path);
    
    if (!report_file.is_open()) {
        LOG_ERROR("Failed to open machine report file: " + report_path, "DataWriter");
        return;
    }
    
    report_file << "machine_id,session_count,total_spins,total_bet,total_win,total_profit,"
               << "avg_rtp,free_spins_rate,avg_session_duration\n";
    
    for (const auto& [machine_id, sessions] : machine_groups) {
        double total_bet = 0, total_win = 0, total_profit = 0, total_duration = 0;
        int total_spins = 0, total_free_spins_triggered = 0;
        
        for (const auto* stats : sessions) {
            total_bet += stats->total_bet;
            total_win += stats->total_win;
            total_profit += stats->total_profit;
            total_spins += stats->total_spins;
            total_duration += stats->session_duration;
            total_free_spins_triggered += stats->free_spins_triggered;
        }
        
        double avg_rtp = total_bet > 0 ? total_win / total_bet : 0.0;
        double free_spins_rate = total_spins > 0 ? 
            static_cast<double>(total_free_spins_triggered) / total_spins : 0.0;
        double avg_duration = total_duration / sessions.size();
        
        report_file << std::fixed << std::setprecision(6)
                   << machine_id << ","
                   << sessions.size() << ","
                   << total_spins << ","
                   << total_bet << ","
                   << total_win << ","
                   << total_profit << ","
                   << avg_rtp << ","
                   << free_spins_rate << ","
                   << avg_duration << "\n";
    }
    
    report_file.close();
}

void DataWriter::FlushBuffers() {
    std::lock_guard<std::mutex> lock(write_mutex_);
    
    if (session_stats_file_ && session_stats_file_->is_open()) {
        session_stats_file_->flush();
    }
    
    if (raw_spins_file_ && raw_spins_file_->is_open()) {
        raw_spins_file_->flush();
    }
}

void DataWriter::UploadToS3() {
    if (!config_.enable_s3_upload || config_.s3_bucket.empty()) {
        return;
    }
    
    LOG_INFO("S3 upload functionality not implemented yet", "DataWriter");
    // TODO: 实现S3上传功能
    // 可以使用AWS SDK for C++来实现
}

} // namespace SlotSimulator
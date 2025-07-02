// src/utils/file_utils.cpp
#include "file_utils.h"
#include <filesystem>
#include <fstream>
#include <sstream>

namespace SlotSimulator {

std::string FileUtils::JoinPath(const std::string& path1, const std::string& path2) {
    std::filesystem::path p1(path1);
    std::filesystem::path p2(path2);
    return (p1 / p2).string();
}

std::string FileUtils::GetDirectory(const std::string& file_path) {
    return std::filesystem::path(file_path).parent_path().string();
}

std::string FileUtils::GetFilename(const std::string& file_path) {
    return std::filesystem::path(file_path).filename().string();
}

std::string FileUtils::GetExtension(const std::string& file_path) {
    return std::filesystem::path(file_path).extension().string();
}

bool FileUtils::FileExists(const std::string& file_path) {
    return std::filesystem::exists(file_path) && std::filesystem::is_regular_file(file_path);
}

bool FileUtils::DirectoryExists(const std::string& dir_path) {
    return std::filesystem::exists(dir_path) && std::filesystem::is_directory(dir_path);
}

bool FileUtils::CreateDirectory(const std::string& dir_path) {
    try {
        return std::filesystem::create_directory(dir_path);
    } catch (const std::exception&) {
        return false;
    }
}

bool FileUtils::CreateDirectories(const std::string& dir_path) {
    try {
        return std::filesystem::create_directories(dir_path);
    } catch (const std::exception&) {
        return false;
    }
}

std::vector<std::string> FileUtils::ListFiles(const std::string& directory, 
                                             const std::string& extension) {
    std::vector<std::string> files;
    
    try {
        for (const auto& entry : std::filesystem::directory_iterator(directory)) {
            if (entry.is_regular_file()) {
                std::string file_path = entry.path().string();
                if (extension.empty() || GetExtension(file_path) == extension) {
                    files.push_back(file_path);
                }
            }
        }
    } catch (const std::exception&) {
        // 目录不存在或无法访问
    }
    
    return files;
}

std::string FileUtils::ReadTextFile(const std::string& file_path) {
    std::ifstream file(file_path);
    if (!file.is_open()) {
        return "";
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

bool FileUtils::WriteTextFile(const std::string& file_path, const std::string& content) {
    std::ofstream file(file_path);
    if (!file.is_open()) {
        return false;
    }
    
    file << content;
    return file.good();
}

size_t FileUtils::GetFileSize(const std::string& file_path) {
    try {
        return std::filesystem::file_size(file_path);
    } catch (const std::exception&) {
        return 0;
    }
}

bool FileUtils::RemoveFile(const std::string& file_path) {
    try {
        return std::filesystem::remove(file_path);
    } catch (const std::exception&) {
        return false;
    }
}

bool FileUtils::RemoveDirectory(const std::string& dir_path) {
    try {
        return std::filesystem::remove_all(dir_path) > 0;
    } catch (const std::exception&) {
        return false;
    }
}

} // namespace SlotSimulator
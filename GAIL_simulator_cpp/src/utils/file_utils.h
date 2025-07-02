// src/utils/file_utils.h
#pragma once

#include <string>
#include <vector>

namespace SlotSimulator {

class FileUtils {
public:
    // 路径操作
    static std::string JoinPath(const std::string& path1, const std::string& path2);
    static std::string GetDirectory(const std::string& file_path);
    static std::string GetFilename(const std::string& file_path);
    static std::string GetExtension(const std::string& file_path);
    
    // 文件/目录检查
    static bool FileExists(const std::string& file_path);
    static bool DirectoryExists(const std::string& dir_path);
    static bool CreateDirectory(const std::string& dir_path);
    static bool CreateDirectories(const std::string& dir_path);
    
    // 文件列表
    static std::vector<std::string> ListFiles(const std::string& directory, 
                                            const std::string& extension = "");
    
    // 文件内容
    static std::string ReadTextFile(const std::string& file_path);
    static bool WriteTextFile(const std::string& file_path, const std::string& content);
    
    // 文件大小
    static size_t GetFileSize(const std::string& file_path);
    
    // 清理临时文件
    static bool RemoveFile(const std::string& file_path);
    static bool RemoveDirectory(const std::string& dir_path);
};

} // namespace SlotSimulator
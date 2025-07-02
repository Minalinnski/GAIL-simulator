# CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(GAILSimulator VERSION 1.0.0 LANGUAGES CXX)

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 设置构建类型
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# 编译选项
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -O0 -DDEBUG")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -DNDEBUG")
endif()

# 添加编译警告
if(NOT MSVC)
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 查找依赖库
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# yaml-cpp
find_package(yaml-cpp QUIET)
if(NOT yaml-cpp_FOUND)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(YAML_CPP REQUIRED yaml-cpp)
endif()

# 可选的LibTorch支持
option(ENABLE_LIBTORCH "Enable LibTorch support" OFF)
if(ENABLE_LIBTORCH)
    find_package(Torch QUIET)
    if(Torch_FOUND)
        add_definitions(-DENABLE_LIBTORCH)
        message(STATUS "LibTorch enabled")
    else()
        message(WARNING "LibTorch not found, ML models will use placeholder implementation")
    endif()
endif()

# 包含目录
include_directories(src)

# 收集源文件
file(GLOB_RECURSE SOURCES
    "src/*.cpp"
    "src/*.h"
)

# 移除示例配置文件（如果存在）
list(FILTER SOURCES EXCLUDE REGEX ".*config_examples.*")

# 创建可执行文件
add_executable(gail_simulator ${SOURCES})

# 链接库
target_link_libraries(gail_simulator Threads::Threads)

# 链接yaml-cpp
if(yaml-cpp_FOUND)
    target_link_libraries(gail_simulator yaml-cpp)
else()
    target_link_libraries(gail_simulator ${YAML_CPP_LIBRARIES})
    target_include_directories(gail_simulator PRIVATE ${YAML_CPP_INCLUDE_DIRS})
endif()

# 链接LibTorch（如果可用）
if(ENABLE_LIBTORCH AND Torch_FOUND)
    target_link_libraries(gail_simulator ${TORCH_LIBRARIES})
    target_include_directories(gail_simulator PRIVATE ${TORCH_INCLUDE_DIRS})
    set_property(TARGET gail_simulator PROPERTY CXX_STANDARD 17)
endif()

# 安装规则
install(TARGETS gail_simulator DESTINATION bin)
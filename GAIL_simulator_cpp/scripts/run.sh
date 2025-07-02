#!/bin/bash
# scripts/run.sh - 运行脚本

set -e

CONFIG_FILE="config/simulation.yaml"
VERBOSE=false
THREADS=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--threads)
            THREADS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -c, --config FILE   Configuration file (default: config/simulation.yaml)"
            echo "  -v, --verbose       Verbose output"
            echo "  -t, --threads N     Number of threads"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 检查可执行文件
EXECUTABLE=""
if [ -f "build/Release/slot_simulator" ]; then
    EXECUTABLE="build/Release/slot_simulator"
elif [ -f "build/Debug/slot_simulator" ]; then
    EXECUTABLE="build/Debug/slot_simulator"
else
    echo "Error: slot_simulator executable not found. Please run ./scripts/build.sh first"
    exit 1
fi

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# 构建命令行参数
ARGS="-c $CONFIG_FILE"

if [ "$VERBOSE" = true ]; then
    ARGS="$ARGS -v"
fi

if [ -n "$THREADS" ]; then
    ARGS="$ARGS -t $THREADS"
fi

echo "Running: $EXECUTABLE $ARGS"
./$EXECUTABLE $ARGS
#!/usr/bin/env bash
set -euo pipefail

# 根目录下需要创建的顶级文件夹
dirs=(
  "src"
  "src/core"
  "src/machines"
  "src/players"
  "src/players/models/random"
  "src/players/models/v1"
  "src/players/models/v2"
  "src/players/ml_interface"
  "src/utils"
  "config"
  "config/machines"
  "config/players"
  "third_party"
  "third_party/yaml-cpp"
  "third_party/libtorch"
  "third_party/aws-sdk-cpp"
  "third_party/pickle-cpp"
)

echo "Creating directories..."
for d in "${dirs[@]}"; do
  mkdir -p "$d"
  echo "  ✔ $d"
done

echo "All directories created."

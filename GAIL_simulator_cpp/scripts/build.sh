#!/bin/bash
# Simple build script

set -e

echo "Building GAIL Simulator..."

# Create build directory
mkdir -p build
cd build

# Configure
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
make -j$(nproc)

echo "Build completed. Executable: build/gail_simulator"
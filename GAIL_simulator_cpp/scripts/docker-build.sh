#!/bin/bash
# Docker build script

set -e

echo "Building GAIL Simulator Docker image..."

# Build Docker image
docker build -t gail-simulator:latest .

echo "Docker image built: gail-simulator:latest"

# Run container
echo "To run the container:"
echo "docker run -v \$(pwd)/config:/app/config -v \$(pwd)/results:/app/results gail-simulator:latest"
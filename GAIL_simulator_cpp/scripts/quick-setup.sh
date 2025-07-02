#!/bin/bash
# Quick setup script for development

set -e

echo "Setting up GAIL Simulator development environment..."

# Install dependencies on Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    echo "Installing dependencies with apt-get..."
    sudo apt-get update
    sudo apt-get install -y \
        build-essential \
        cmake \
        pkg-config \
        libyaml-cpp-dev \
        git
fi

# Create directories
mkdir -p build logs results config/{machines,players}

# Create sample config if not exists
if [ ! -f "config/simulation.yaml" ]; then
    cat > config/simulation.yaml << 'EOF'
file_configs:
  machines:
    dir: "config/machines"
    selection:
      mode: "all"
  players:
    dir: "config/players"
    selection:
      mode: "all"

sessions_per_pair: 100
max_spins: 1000
max_sim_duration: 300
use_concurrency: true
thread_count: 0

output:
  directories:
    base_dir: "results"
  session_recording:
    enabled: true
  reports:
    generate_reports: true

logging:
  level: "INFO"
  console: true
  file:
    enabled: true
    path: "logs/simulator.log"
EOF
    echo "Created sample config/simulation.yaml"
fi

echo "Setup completed!"
echo "Run './scripts/build.sh' to build the project"
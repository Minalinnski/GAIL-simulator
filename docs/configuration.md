# Configuration Guide

## Overview

The slot machine simulator uses YAML configuration files for all components. This document explains the configuration system and how it's used throughout the application.

## Configuration Structure

Configurations are organized by domain:

```
src/application/config/
├── machines/          # Slot machine configurations
│   ├── default.yaml
│   └── high_volatility.yaml
├── players/           # Player configurations
│   ├── random_player.yaml
│   └── conservative_player.yaml
└── simulation.yaml    # Main simulation configuration
```

## Loading Process

1. **Infrastructure Layer**: Responsible for loading and validating configurations
   - `YamlConfigLoader`: Loads YAML files and converts them to dictionaries
   - `SchemaValidator`: Validates configurations against JSON schemas

2. **Application Layer**: Manages configurations at runtime
   - `RegistryService`: Coordinates loading of all configurations
   - Provides access to machine and player configurations

3. **Domain Layer**: Uses configurations to create domain objects
   - `MachineFactory`: Creates `SlotMachine` instances from configurations
   - `PlayerFactory`: Creates `Player` instances from configurations

## Player Model Versioning

The player configuration includes a `model_version` field that determines which implementation to use:

```yaml
# Model Version - determines which implementation to use
model_version: "random"  # or "v1", "v2", etc.

# Configuration specific to this version
model_config_random:
  # Configuration parameters for the random model
```

When a player is created:

1. The player entity reads the `model_version` field
2. It uses the decision engine factory to create the appropriate engine
3. The factory looks for the implementation in `models/{version}/entities/{version}_decision_engine.py`
4. If found, it creates that engine, otherwise falls back to the random engine
5. Configuration is passed to the engine via the `model_config_{version}` field

## Configuration Example

Here's an example of how configuration flows through the system:

1. A YAML configuration file is loaded from `src/application/config/players/random_player.yaml`
2. The configuration is validated against the player schema
3. The `PlayerFactory` creates a `Player` instance with this configuration
4. The player reads the `model_version: "random"` field
5. It looks for configuration in the `model_config_random` section
6. The decision engine factory creates a `RandomDecisionEngine` with this configuration
7. When the player makes decisions, the configuration parameters control its behavior

## Reusing Infrastructure

The configuration system reuses the infrastructure layer components:

```python
from infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from infrastructure.config.validators.schema_validator import SchemaValidator

# Create loader and validator
schema_validator = SchemaValidator()
config_loader = YamlConfigLoader(schema_validator)

# Load a configuration file
config = config_loader.load_file("src/application/config/players/random_player.yaml")
```

The same infrastructure is used for all configurations, ensuring consistent loading and validation.

## Adding New Model Versions

To add a new model version:

1. Create a new directory under `src/domain/player/models/{version}/`
2. Implement the required components:
   - `entities/{version}_decision_engine.py`
   - `services/{version}_model_service.py`
   - `services/data_processor_service.py`
3. Create a player configuration with `model_version: "{version}"`
4. Add configuration parameters in `model_config_{version}`
5. The factory will automatically discover and use your new implementation

This versioning system allows for multiple model implementations to coexist in the codebase.
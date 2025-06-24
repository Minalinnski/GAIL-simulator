 # src/infrastructure/config/validators/schema_validator.py
import jsonschema
import logging
from typing import Dict, Any, Tuple, List


class SchemaValidator:
    """
    Validates configuration data against JSON schemas.
    """
    def __init__(self):
        """Initialize the schema validator."""
        self.logger = logging.getLogger(__name__)
        
    def validate(self, config: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a configuration against a JSON schema.
        
        Args:
            config: The configuration dictionary to validate
            schema: The JSON schema to validate against
            
        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: Boolean indicating if validation passed
            - error_messages: List of error messages if validation failed
        """
        try:
            jsonschema.validate(instance=config, schema=schema)
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            # Format error for better readability
            error_path = '.'.join(str(p) for p in e.path) if e.path else 'root'
            error_message = f"At {error_path}: {e.message}"
            
            self.logger.error(f"Schema validation error: {error_message}")
            return False, [error_message]
        except jsonschema.exceptions.SchemaError as e:
            # There's something wrong with the schema itself
            self.logger.error(f"Invalid schema: {e}")
            return False, [f"Schema error: {str(e)}"]
            
    def validate_with_defaults(self, config: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a configuration and fill in default values from the schema.
        
        Args:
            config: The configuration dictionary to validate
            schema: The JSON schema to validate against
            
        Returns:
            Tuple of (is_valid, error_messages, updated_config)
            - is_valid: Boolean indicating if validation passed
            - error_messages: List of error messages if validation failed
            - updated_config: Configuration with default values applied
        """
        # Create a deep copy to avoid modifying the original
        import copy
        updated_config = copy.deepcopy(config)
        
        # Apply defaults from schema
        try:
            self._apply_defaults(updated_config, schema)
            
            # Validate the config with defaults applied
            is_valid, errors = self.validate(updated_config, schema)
            return is_valid, errors, updated_config
        except Exception as e:
            self.logger.error(f"Error applying defaults: {str(e)}")
            return False, [f"Error applying defaults: {str(e)}"], config
            
    def _apply_defaults(self, config: Dict[str, Any], schema: Dict[str, Any], path: str = ""):
        """
        Recursively apply default values from schema to config.
        
        Args:
            config: Configuration to update with defaults
            schema: Schema containing default values
            path: Current path in the schema (for logging)
        """
        if not isinstance(schema, dict):
            return
            
        # Handle default at current level
        if 'default' in schema and path not in config:
            parts = path.split('.') if path else []
            
            # Navigate to the right part of the config
            current = config
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            # Set the default value if last part doesn't exist
            if parts and parts[-1] not in current:
                current[parts[-1]] = schema['default']
                self.logger.debug(f"Applied default value for {path}: {schema['default']}")
                
        # Process object properties
        if 'properties' in schema and isinstance(schema['properties'], dict):
            for prop_name, prop_schema in schema['properties'].items():
                new_path = f"{path}.{prop_name}" if path else prop_name
                
                # If this is an object with properties, ensure it exists in config
                if ('type' in prop_schema and prop_schema['type'] == 'object' and
                    'properties' in prop_schema):
                    current = config
                    parts = path.split('.') if path else []
                    
                    # Navigate to current position and ensure objects exist
                    for part in parts:
                        if part:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                    
                    # Ensure the property exists as an empty dict if needed
                    if prop_name not in current:
                        current[prop_name] = {}
                        
                    # Recursively apply defaults to this object
                    self._apply_defaults(config, prop_schema, new_path)
                else:
                    # For other types, just apply defaults
                    self._apply_defaults(config, prop_schema, new_path)
                    
        # Process array items
        if 'items' in schema and isinstance(schema['items'], dict):
            if path in config and isinstance(config[path], list):
                for i, item in enumerate(config[path]):
                    item_path = f"{path}[{i}]"
                    self._apply_defaults(config, schema['items'], item_path)
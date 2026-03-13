"""
Config Loader Module

Loads and manages configuration from YAML files and environment variables.
"""

import os
import logging
from typing import Any, Dict, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader with environment variable substitution.

    Loads YAML config and replaces ${VAR} placeholders with environment variables.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader.

        Args:
            config_path: Path to config file
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}

    def _get_default_config_path(self) -> str:
        """Get default config path."""
        # Default to config/config.yaml in project root
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'config.yaml'
        )

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}")
            return {}

        if not YAML_AVAILABLE:
            logger.warning("YAML module not available, cannot load config")
            return {}

        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)

            # Process environment variables
            self._config = self._process_env_vars(raw_config)
            logger.info(f"Loaded config from {self.config_path}")
            return self._config

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _process_env_vars(self, obj: Any) -> Any:
        """
        Recursively process environment variables in config.

        Args:
            obj: Object to process

        Returns:
            Processed object
        """
        if isinstance(obj, dict):
            return {k: self._process_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._process_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_vars(obj)
        else:
            return obj

    def _substitute_env_vars(self, value: str) -> str:
        """
        Substitute environment variables in string.

        Supports ${VAR} and ${VAR:-default} syntax.

        Args:
            value: String with potential env var placeholders

        Returns:
            Substituted string
        """
        import re

        def replace(match):
            var_expr = match.group(1)

            # Handle default value syntax
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.environ.get(var_name.strip(), default.strip())

            return os.environ.get(var_expr.strip(), '')

        return re.sub(r'\$\{([^}]+)\}', replace, value)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value by key.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire config section.

        Args:
            section: Section name

        Returns:
            Section configuration
        """
        return self._config.get(section, {})


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader(config_path)
    return loader.load()


# Default config instance
_default_config: Optional[Dict[str, Any]] = None


def get_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get global configuration.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    global _default_config
    if _default_config is None:
        _default_config = load_config(config_path)
    return _default_config

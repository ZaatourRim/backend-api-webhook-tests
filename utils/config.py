from pathlib import Path
import yaml
import os

def load_settings() -> dict:
    """
    Loads settings from config/settings.yaml and returns them as a dict.
    """

    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "settings.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Settings file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_env_or_setting(path: str, env_var: str, default=None):
    """Helper to fetch a value from environment first then from settings.yaml.

    Args:
        path (str): dotted path in the settings dict, e.g: "api.base_url"
        env_var (str): name of the environment variable to check first
        default (_type_, optional): default value if neither env or settings has it. Defaults to None.
    """
    # checking in environment
    value = os.getenv(env_var)
    if value is not None:
        return value
    
    # fallback check in settings
    settings = load_settings()
    parts = path.split(".")
    current = settings
    for p in parts:
        if not isinstance(current, dict) or p not in current:
            return default
        current = current[p]
    return current
        

"""
Streamlit configuration management for desktop mode.

Generates a temporary .streamlit/config.toml that configures Streamlit
to run in headless mode without opening a browser or collecting telemetry.
"""

import tempfile
from pathlib import Path
from typing import Optional


# Streamlit config template for headless desktop mode.
# Key settings:
#   - headless = true: Don't try to open a browser
#   - port: Dynamically assigned free port
#   - enableCORS/enableXsrfProtection = false: Required for pywebview embedding
#   - gatherUsageStats = false: No telemetry in packaged app
_CONFIG_TEMPLATE = """\
[server]
headless = true
port = {port}
address = "127.0.0.1"
enableCORS = false
enableXsrfProtection = false
runOnSave = false
fileWatcherType = "none"
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = {port}

[theme]
base = "dark"

[runner]
fastReruns = true
"""


def create_streamlit_config(port: int, config_dir: Optional[Path] = None) -> Path:
    """
    Generate a .streamlit/config.toml for headless desktop mode.

    Args:
        port: The port Streamlit should listen on.
        config_dir: Directory to write the config into. If None, uses a
                     temporary directory that persists for the session.

    Returns:
        Path to the directory containing the generated config.toml.
    """
    if config_dir is None:
        config_dir = Path(tempfile.mkdtemp(prefix="filesense_"))

    streamlit_dir = config_dir / ".streamlit"
    streamlit_dir.mkdir(parents=True, exist_ok=True)

    config_path = streamlit_dir / "config.toml"
    config_content = _CONFIG_TEMPLATE.format(port=port)
    config_path.write_text(config_content, encoding="utf-8")

    return config_dir

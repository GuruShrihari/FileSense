"""
Streamlit configuration for desktop mode.

Generates a temporary .streamlit/config.toml that runs Streamlit
in headless mode without opening a browser or collecting telemetry.
"""

import tempfile
from pathlib import Path
from typing import Optional

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
    """Generate a .streamlit/config.toml for headless desktop mode."""
    if config_dir is None:
        config_dir = Path(tempfile.mkdtemp(prefix="filesense_"))

    streamlit_dir = config_dir / ".streamlit"
    streamlit_dir.mkdir(parents=True, exist_ok=True)

    config_path = streamlit_dir / "config.toml"
    config_path.write_text(_CONFIG_TEMPLATE.format(port=port), encoding="utf-8")

    return config_dir

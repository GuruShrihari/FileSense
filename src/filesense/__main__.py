"""
Entry point for FileSense application.

Run with: python -m filesense

In desktop mode (default), this launches the pywebview window with
the Streamlit server running in the background. No browser is opened.
"""

import sys


def main() -> None:
    """Main application entry point — launches the desktop GUI."""
    from filesense.launcher import launch
    launch()


if __name__ == "__main__":
    main()

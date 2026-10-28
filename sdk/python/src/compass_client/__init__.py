"""compass_client — dünner Python-Client für COMPASS (REST-Referenz), kein MCP nötig."""

from .client import VERSION, AsyncCompass, Compass, CompassFehler

__all__ = ["Compass", "AsyncCompass", "CompassFehler"]
# die Version steht EINMAL, in client.py -- von dort nimmt sie
# auch der `User-Agent` des SDK. Zwei Stellen waeren zwei Wahrheiten, sobald
# eine davon vergessen wird.
__version__ = VERSION

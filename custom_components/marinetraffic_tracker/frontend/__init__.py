"""Frontend asset registration for maritime tracker card.

Registers the custom Lovelace card and vendored map assets as static resources
for serving through Home Assistant's /api/frontend_latest/static/custom_components/
namespace.
"""

from __future__ import annotations

import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

# Path to this frontend module.
FRONTEND_DIR = Path(__file__).parent

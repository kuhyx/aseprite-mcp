"""Every MCP tool module; importing this package registers all @mcp.tool()s."""

from . import (
    analysis as analysis,
)
from . import (
    animation as animation,
)
from . import (
    canvas as canvas,
)
from . import (
    drawing as drawing,
)
from . import (
    export as export,
)
from . import (
    fx as fx,
)
from . import (
    guide as guide,
)
from . import (
    layers as layers,
)
from . import (
    native_fx as native_fx,
)
from . import (
    palette as palette,
)
from . import (
    pixel_read as pixel_read,
)
from . import (
    preview as preview,
)
from . import (
    quality as quality,
)
from . import (
    scene as scene,
)
from . import (
    script as script,
)
from . import (
    selection as selection,
)
from . import (
    slices as slices,
)
from . import (
    text as text,
)
from . import (
    tilemap as tilemap,
)
from . import (
    transform as transform,
)


def register_all_tools() -> None:
    """No-op: importing this package (already done above) registers every tool."""

"""Fresh Vercel cron entrypoint bound to the current AION production build."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_ops_path = Path(__file__).with_name("ops.py")
_spec = spec_from_file_location("aion_cron_ops", _ops_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load AION cron ops handler")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app

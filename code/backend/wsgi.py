from app import create_app
from config import load_config, mysql_connect_factory
from store import MemoryStore, MySQLStore

_cfg = load_config()
_store = (
    MySQLStore(mysql_connect_factory(_cfg)) if _cfg["STORE"] == "mysql" else MemoryStore()
)
app = create_app(store=_store, config=_cfg)

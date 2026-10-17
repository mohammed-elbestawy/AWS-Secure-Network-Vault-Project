"""Delete expired secrets. Run by vault-purge.timer every five minutes."""
from config import load_config, mysql_connect_factory
from store import MySQLStore, utcnow

if __name__ == "__main__":
    cfg = load_config()
    store = MySQLStore(mysql_connect_factory(cfg))
    print("purged", store.purge_expired(utcnow()))

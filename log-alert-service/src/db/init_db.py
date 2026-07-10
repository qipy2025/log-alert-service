from src.db.mysql import init_db
from src.db.cache import get_cache_client

if __name__ == "__main__":
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)

    print("\n[1/2] Initializing MySQL database...")
    try:
        init_db()
        print("OK - MySQL database initialized")
    except Exception as e:
        print(f"ERROR - MySQL database initialization failed: {e}")
        exit(1)

    print("\n[2/2] Initializing memory cache...")
    try:
        cache_client = get_cache_client()
        cache_client.ping()
        print("OK - Memory cache initialized")
    except Exception as e:
        print(f"ERROR - Memory cache initialization failed: {e}")
        exit(1)

    print("\n" + "=" * 50)
    print("Database initialization completed")
    print("=" * 50)

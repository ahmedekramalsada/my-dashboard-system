import asyncpg
import logging
import secrets
import string
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.DB")

# ─────────────────────────────────────────────────────────────────────────────
# Connection Pool — shared across all requests (much more efficient than
# opening a new connection per API call)
# ─────────────────────────────────────────────────────────────────────────────
_pool: asyncpg.Pool | None = None

def _sys_dsn() -> str:
    return (
        f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(
            dsn=_sys_dsn(),
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("asyncpg connection pool created.")
    return _pool

async def close_pool():
    global _pool
    if _pool and not _pool._closed:
        await _pool.close()
        logger.info("asyncpg connection pool closed.")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def generate_secure_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_secret_key(length: int = 32) -> str:
    return secrets.token_hex(length)

# ─────────────────────────────────────────────────────────────────────────────
# Tenant Registry
# ─────────────────────────────────────────────────────────────────────────────
async def ensure_tenant_registry():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                name         TEXT PRIMARY KEY,
                theme        TEXT NOT NULL DEFAULT 'fashion',
                site_type    TEXT NOT NULL DEFAULT 'ecommerce',
                admin_email  TEXT NOT NULL,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                db_name      TEXT NOT NULL,
                db_user      TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'running'
            )
        """)
        # Add status column to existing deployments that don't have it
        await conn.execute("""
            ALTER TABLE tenants ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'running';
            ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_type TEXT NOT NULL DEFAULT 'ecommerce';
        """)
    logger.info("Tenant registry table ensured.")


async def register_tenant(tenant_name: str, site_type: str, theme: str, admin_email: str, db_name: str, db_user: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tenants (name, site_type, theme, admin_email, created_at, db_name, db_user, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'running')
            ON CONFLICT (name) DO UPDATE
              SET site_type   = EXCLUDED.site_type,
                  theme       = EXCLUDED.theme,
                  admin_email = EXCLUDED.admin_email,
                  created_at  = EXCLUDED.created_at,
                  db_name     = EXCLUDED.db_name,
                  db_user     = EXCLUDED.db_user,
                  status      = 'running'
        """, tenant_name, site_type, theme, admin_email, datetime.now(timezone.utc), db_name, db_user)


async def deregister_tenant(tenant_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tenants WHERE name = $1", tenant_name)


async def set_tenant_status(tenant_name: str, status: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE tenants SET status = $1 WHERE name = $2", status, tenant_name)


async def list_tenants() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT name, site_type, theme, admin_email, created_at, db_name, db_user, status "
            "FROM tenants ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────────────────────────
# Tenant Database Lifecycle
# ─────────────────────────────────────────────────────────────────────────────
async def provision_tenant_db(tenant_name: str) -> dict:
    """
    Create an isolated PostgreSQL database + role for a tenant.
    If they already exist, the role password is synced to prevent drift.
    """
    safe = tenant_name.replace("-", "_").lower()
    db_name = f"db_{safe}"
    role_name = f"user_{safe}"
    password = generate_secure_password()

    pool = await get_pool()
    # Use a raw connection for DDL (CREATE DATABASE can't run in a transaction)
    conn = await asyncpg.connect(dsn=_sys_dsn())
    try:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not db_exists:
            logger.info(f"Creating role {role_name} and database {db_name}...")
            await conn.execute(f"CREATE ROLE {role_name} WITH LOGIN PASSWORD '{password}';")
            await conn.execute(f"CREATE DATABASE {db_name} OWNER {role_name};")
            # Postgres 15+ requires explicit CONNECT grant
            await conn.execute(f"GRANT CONNECT ON DATABASE {db_name} TO {role_name};")
            logger.info(f"Provisioned: {db_name} / {role_name}")
        else:
            # Sync password to avoid auth drift after API container restarts
            logger.warning(f"{db_name} already exists — syncing role password.")
            await conn.execute(f"ALTER ROLE {role_name} WITH PASSWORD '{password}';")
    finally:
        await conn.close()

    return {
        "DB_HOST": settings.DB_HOST,
        "DB_PORT": settings.DB_PORT,
        "DB_NAME": db_name,
        "DB_USER": role_name,
        "DB_PASSWORD": password,
    }


async def delete_tenant_db(tenant_name: str):
    safe = tenant_name.replace("-", "_").lower()
    db_name = f"db_{safe}"
    role_name = f"user_{safe}"

    conn = await asyncpg.connect(dsn=_sys_dsn())
    try:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if db_exists:
            # Terminate active connections before dropping
            await conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1 AND pid<>pg_backend_pid()",
                db_name,
            )
            await conn.execute(f"DROP DATABASE {db_name};")
            await conn.execute(f"DROP ROLE IF EXISTS {role_name};")
            logger.info(f"Dropped {db_name} and {role_name}")
        else:
            logger.warning(f"Database {db_name} not found — skipping.")
    finally:
        await conn.close()
    return True

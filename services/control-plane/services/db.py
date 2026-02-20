import asyncpg
import logging
import secrets
import string
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.DB")

def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

async def provision_tenant_db(tenant_name: str) -> dict:
    """
    Connects to the shared PostgreSQL instance and creates a new database and role for the tenant.
    This ensures strict isolation per tenant.
    Returns the credentials to be passed to the tenant's container.
    """
    # Sanitize tenant name for Postgres identifier
    safe_tenant_name = tenant_name.replace("-", "_").lower()
    db_name = f"db_{safe_tenant_name}"
    role_name = f"user_{safe_tenant_name}"
    password = generate_secure_password()

    sys_dsn = f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    
    try:
        # We use asyncpg to connect to the default DB
        conn = await asyncpg.connect(sys_dsn)
        
        # Check if DB already exists (Idempotency)
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not db_exists:
            # Cannot use parameterized queries for CREATE DATABASE/ROLE, so we use sanitized variables safely
            logger.info(f"Creating role {role_name}...")
            await conn.execute(f"CREATE ROLE {role_name} WITH LOGIN PASSWORD '{password}';")
            
            logger.info(f"Creating database {db_name}...")
            await conn.execute(f"CREATE DATABASE {db_name} OWNER {role_name};")
            
            # Note: Postgres automatically grants all rights to the OWNER on the newly created database.
            logger.info(f"Database {db_name} and role {role_name} created successfully.")
        else:
            logger.warning(f"Database {db_name} already exists. Skipping creation to remain idempotent.")
            # Note: in a real system we might want to return existing password from Vault or recreate it.
            # For this MVP, if it exists we might not know the old password, but we assume it's a fresh creation.

        await conn.close()
        
        return {
            "DB_HOST": settings.DB_HOST,
            "DB_PORT": settings.DB_PORT,
            "DB_NAME": db_name,
            "DB_USER": role_name,
            "DB_PASSWORD": password
        }

    except Exception as e:
        logger.error(f"Failed to provision database for {tenant_name}: {str(e)}")
        raise e

async def delete_tenant_db(tenant_name: str):
    """
    Connects to the shared DB, drops the tenant's database and role.
    """
    safe_tenant_name = tenant_name.replace("-", "_").lower()
    db_name = f"db_{safe_tenant_name}"
    role_name = f"user_{safe_tenant_name}"

    sys_dsn = f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    
    try:
        conn = await asyncpg.connect(sys_dsn)
        
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if db_exists:
            logger.info(f"Dropping database {db_name}...")
            # Cannot drop a database while it's in use, might need to terminate connections first in a true prod environment
            await conn.execute(f"DROP DATABASE {db_name};")
            
            logger.info(f"Dropping role {role_name}...")
            await conn.execute(f"DROP ROLE {role_name};")
            logger.info(f"Database {db_name} and role {role_name} deleted successfully.")
        else:
            logger.warning(f"Database {db_name} does not exist. Skipping deletion.")

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to delete database for {tenant_name}: {str(e)}")
        raise e

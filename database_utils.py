import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from django.utils import timezone
from tickets.models import Ticket, AuditLog
import logging
import uuid


# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_database_config() -> Dict[str, str]:
    """
    Get database configuration from environment variables
    
    Returns:
        Dict[str, str]: Database configuration parameters
    """
    return {
        'dbname': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT', '5432')
    }

def connect_to_postgres() -> Optional[psycopg2.extensions.connection]:
    """
    Connect to PostgreSQL database using environment variables
    
    Returns:
        psycopg2.connection: Database connection object or None if failed
    """
    try:
        config = get_database_config()
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {str(e)}")
        return None

@contextmanager
def get_db_connection():
    """
    Context manager for database connections
    Automatically handles connection closing
    
    Usage:
        with get_db_connection() as conn:
            # use connection
            pass
    """
    conn = None
    try:
        conn = connect_to_postgres()
        if conn is None:
            raise Exception("Failed to establish database connection")
        yield conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

@contextmanager
def get_db_cursor(cursor_factory=RealDictCursor):
    """
    Context manager for database cursor
    Automatically handles connection and cursor closing
    
    Args:
        cursor_factory: Cursor factory to use (default: RealDictCursor)
    
    Usage:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM table")
            results = cur.fetchall()
    """
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

def execute_query(query: str, params: tuple = None, fetch_one: bool = False) -> Optional[Any]:
    """
    Execute a single query and return results
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        fetch_one (bool): If True, return single row; if False, return all rows
        
    Returns:
        Query results or None if error
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(query, params)
            
            if fetch_one:
                return cur.fetchone()
            else:
                return cur.fetchall()
                
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

def execute_insert_update(query: str, params: tuple = None) -> bool:
    """
    Execute INSERT/UPDATE/DELETE queries
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(query, params)
            return True
    except Exception as e:
        print(f"Error executing insert/update: {str(e)}")
        return False

def test_database_connection() -> bool:
    """
    Test database connectivity
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()
                print(f"Database connection test successful: {result}")
                return True
    except Exception as e:
        print(f"Database connection test failed: {str(e)}")
        return False

def get_table_info(table_name: str) -> Optional[List[Dict]]:
    """
    Get column information for a specific table
    
    Args:
        table_name (str): Name of the table
        
    Returns:
        List[Dict]: Column information or None if error
    """
    query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """
    return execute_query(query, (table_name,))

def check_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database
    
    Args:
        table_name (str): Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """
    result = execute_query(query, (table_name,), fetch_one=True)
    return result['exists'] if result else False

# Example usage and testing
if __name__ == "__main__":
    print("=== Database Utils Test ===")
    
    # Test basic connection
    if test_database_connection():
        print("✅ Database connection successful")
        
        # Test table existence
        test_tables = ['tickets_ticket', 'tickets_organization', 'tessa_audit_logs']
        for table in test_tables:
            exists = check_table_exists(table)
            print(f"Table '{table}' exists: {exists}")
            
            if exists:
                columns = get_table_info(table)
                print(f"  Columns in {table}: {len(columns) if columns else 0}")
    else:
        print("❌ Database connection failed") 
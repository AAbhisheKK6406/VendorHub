import mysql.connector
from mysql.connector import Error
import config

# Dictionary containing database configuration parameters
db_config = {
    'host': config.DB_HOST,
    'port': config.DB_PORT,
    'user': config.DB_USER,
    'password': config.DB_PASSWORD,
    'database': config.DB_NAME
}

def get_database_connection():
    """
    Establishes and returns a connection to the MySQL database.
    Returns:
        mysql.connector.connection.MySQLConnection object if successful, or None if it fails.
    """
    try:
        # Attempt to open a connection pipeline to the MySQL server
        connection = mysql.connector.connect(**db_config)
        
        # Verify if the connection is active
        if connection.is_connected():
            return connection
            
    except Error as database_error:
        # Catch and print any MySQL-specific errors (e.g., wrong password, database missing)
        print(f"Error while connecting to MySQL database: {database_error}")
        return None

def close_database_connection(connection):
    """
    Safely closes the provided database connection to free up server resources.
    Args:
        connection: The active MySQL connection object to close.
    """
    try:
        # Check if the connection exists and is currently open before trying to close it
        if connection and connection.is_connected():
            connection.close()
            print("MySQL connection closed safely.")
            
    except Error as closing_error:
        print(f"Error while closing the MySQL connection: {closing_error}")
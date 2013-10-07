import logging
import sqlite3
import hashlib
import os

# Global database connection for Accounts module
conn = None
cursor = None

AUTHQUERY = "SELECT COUNT(*) FROM accounts WHERE user=? and passwd=?"
GETUSER = "SELECT * FROM accounts WHERE username=?"

def initializeDatabase():
    """
    Initize database for use.
    """
    global conn
    global cursor

    #try:
    conn = sqlite3.connect(os.path.join('data', 'bbs.db'))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    #except:
    #    logging.error("Failed trying to load database for using accounting.")
        
        
def authQuery(username, passwd):
    """
    Authenticate username and password.
    """
    global conn
    global cursor

    if conn == None:
        initializeDatabase()
        
    try:
        hasher = hashlib.sha512()
        hasher.update(passwd.encode('utf-8'))
        cursor.execute(AUTHQUERY, (username, hasher.hexdigest()))
        result = cursor.fetchone()
    except:
        pass
    
def getUser(username):
    """
    Get user info.
    """
    global cursor
    global conn
    if conn == None:
        initializeDatabase()
    try:
        cursor.execute(GETUSER, [username])
        user = cursor.fetchone()
        user.keys()
    except:
        logging.error(' EXCEPT')
        
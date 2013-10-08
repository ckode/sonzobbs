import logging
import sqlite3
import hashlib
import os

# Global database connection for Accounts module
conn = None
cursor = None

# Predefined database queries.
AUTHQUERY = "SELECT COUNT(*) FROM accounts WHERE user=? and passwd=?"
GETUSER = "SELECT * FROM accounts WHERE username=?"
UPDATEUSER = "UPDATE accounts SET username=?, passwd=?, firstname=?, lastname=?, globals=?, ansi=?, active=? WHERE username=?"
ADDUSER = "INSERT INTO accounts (username, passwd, firstname, lastname, globals, ansi, acctive) values (?, ?, ?, ?, ?, ?, ?)"

# Decorators
#========================================
def inititalizeDatabase(func):
    """
    Initize database for use.
    """
    global conn
    global cursor

    if conn == None:
        try:
            conn = sqlite3.connect(os.path.join('data', 'bbs.db'))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        except:
            logging.error(" Failed trying to load database for using accounting.")
        
    return func


@inititalizeDatabase
def authQuery(passwd):
    """
    Authenticate username and password.
    """
    global conn
    global cursor
    try:
        hasher = hashlib.sha512()
        hasher.update(passwd.encode('utf-8'))
        cursor.execute(AUTHQUERY, (username, hasher.hexdigest()))
        result = cursor.fetchone()
    except:
        pass

    if result:
        pass


@inititalizeDatabase
def getUser(username):
    """
    Get user info.
    """
    global cursor
    global conn
    try:
        cursor.execute(GETUSER, [username])
        user = cursor.fetchone()
    except:
        logging.error(' Failed to query accounts database.')
        return None
    return user


@inititalizeDatabase
def saveUser(userdata):
    """
    Save user's data to database.
    """
    global conn
    global cursor
    global UPDATEUSER
    try:
        cursor.execute(UPDATEUSER, userdata)
        conn.commit()
    except:
        logging.error(" Failed to updated user ({}) in database.".format(userdata[0]))


@inititalizeDatabase
def addUserToDatabase(userdata):
    """
    Add new user to database.
    """
    global conn
    global cursor
    global ADDUSER
    # See if the user already exist first.
    if getUser(userdata[0]):
        logging.error(" User '{}' already exists.".format(userdata[0]))
        return False

    try:
        cursor.execute(ADDUSER, userdata)
        conn.commit()
    except:
        logging.error(" Failed to add user ({}) in database.".format(userdata[0]))
        return False
    return True



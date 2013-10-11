import logging
import sqlite3
import hashlib
import os

# Global database connection for Accounts module
conn = None
cursor = None

# Predefined database queries.
AUTHQUERY = "SELECT COUNT(*) as count FROM accounts WHERE username=? and passwd=?"
GETUSER = "SELECT * FROM accounts WHERE username=? COLLATE NOCASE"
UPDATEUSER = "UPDATE accounts SET username=?, passwd=?, firstname=?, lastname=?, email=?, globals=?, ansi=?, active=? WHERE username=?"
ADDUSER = "INSERT INTO accounts (username, passwd, firstname, lastname, email, globals, ansi, active) values (?, ?, ?, ?, ?, ?, ?, ?)"
ADDUSERTOGROUP = "INSERT INTO account_perms (account, access_group) VALUES (?, ?)"
GETALL = "SELECT * FROM accounts"

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
def authUser(client, passwd):
    """
    Authenticate username and password.
    """
    global conn
    global cursor
    result = None
    user = getUserFromDatabase(client)
    try:
        hasher = hashlib.sha512()
        hasher.update(passwd.encode('utf-8'))
        cursor.execute(AUTHQUERY, (user['username'], hasher.hexdigest()))
        result = cursor.fetchone()
    except:
        logging.error(" Error authenticating user {}".format(client))

    return True if result['count'] == 1 else False


@inititalizeDatabase
def userExist(username):
    """
    Authenticate username and password.
    """
    global conn
    global cursor
    global GETUSER
    result = None
    
    try:
        cursor.execute(GETUSER % [client.getAttr('username')])
        result = cursor.fetchone()
    except:
        pass

    return True if result else False


@inititalizeDatabase
def getUserFromDatabase(username):
    """
    Get user info.
    """
    global cursor
    global conn
    global GETUSER
    user = None
    try:
        cursor.execute(GETUSER, [username])
        user = cursor.fetchone()
    except:
        logging.error(' Failed to query accounts database.')
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
    if getUserFromDatabase(userdata[0]):
        logging.error(" Unable to add user, '{}' already exists.".format(userdata[0]))
        return False
    try:
        cursor.execute(ADDUSER, userdata)
        conn.commit()
        # Add user to default group 
        # TODO: Make default group defineable in BBS config
        user = getUserFromDatabase(userdata[0])
        cursor.execute(ADDUSERTOGROUP, [user['id'], 2])
        conn.commit()
    except:
        logging.error(" Failed to add user ({}) in database.".format(userdata[0]))
        return False
    return True



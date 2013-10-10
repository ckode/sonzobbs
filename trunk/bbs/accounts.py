import logging
import sqlite3
import os
import hashlib

from sonzoserv.telnet import TelnetProtocol
from bbs.board import parser, BBSUSERS, splash, sendClient
from bbs.menu import getFullMenu, getMiniMenu, getLoginScreen
from bbs.sql.accts import getUserFromDatabase, saveUser, addUserToDatabase

# Global database connection for Accounts module
conn = None
cursor = None

class Account(TelnetProtocol):
    """
    Server side BBS account object.
    """

    def __init__(self, sock, addr):
        """
        Initialize a BBS Account object.
        """
        TelnetProtocol.__init__(self, sock, addr)
        self._attr = {}
        self._attr['id'] = None
        self._attr['username'] = ''
        self._attr['passwd'] = ''
        self._attr['firstname'] = ''
        self._attr['lastname'] = ''
        self._attr['email'] = ''
        self._attr['globals'] = 1
        self._attr['active'] = 0
        self._attr['menu'] = 'MAINMENU'
        self._attr['state'] = 'CONNECTING'
        self._attr['ansi'] = self._ansi
        self._attr['door'] = None
        self._attr['sec_code'] = ''
        self.parser = parser


    def setAttr(self, attr, value):
        """
        Set account attribute to value.
        """
        if attr in self._attr.keys():
            if attr == 'ansi':
                self._ansi = value
            self._attr[attr] = value
        else:
            logging.error( "Failed to assign '{}' to attribute '{}'".format(value, attr))


    def getAttr(self, attr):
        """
        Return user attribute.
        """
        if attr in self._attr.keys():
            return self._attr[attr]
        else:
            return None


    def loadUser(self):
        #TODO: Make sure authentication happens before this.
        result = getUserFromDatabase(self._attr['username'])
        if result:
            for attr in result.keys():
                # Don't load ansi setting from the database if empty, 
                # keep negotiated ansi setting.
                if attr == 'ansi' and result[attr] == None:
                    continue
                self.setAttr(attr, result[attr])
            self.setAttr('state', 'AUTHENTICATED')
        else:
            logging.error(" User '{}' not found in account database.".format(self._attr['username']))


    def onConnect(self):
        """
        onConnect()
        """
        BBSUSERS.append(self)
        splash(self)
        sendClient(self, getLoginScreen(), colorcodes=self.inANSIMode())    


    def onDisconnect(self):
        """"
        onDisconnect()
        """
        BBSUSERS.remove(self)
        logging.info(" {} has disconnected.".format(self.getAddrPort()))


    def dataReceived(self, data):
        """
        dataReceived()
        """
        parser(self, data)


    def setMenu(self, menu):
        """
        Set users current menu.
        """
        self._attr['menu'] = menu


    def getMenu(self):
        """
        Get users current menu.
        """
        return self._attr['menu']


    def setPassword(self, passwd):
        """
        Change or set the user's password.
        """
        hasher = hashlib.sha512()
        hasher.update(passwd.encode('utf-8'))
        self._attr['passwd'] = hasher.hexdigest()
        self.save()


    def save(self):
        """
        Update users in database.
        """
        # This list structure and elements must match bbs.sql.accts.UPDATEUSER SQL statement structure and elements.
        userdata = [self._attr['username'],
                    self._attr['passwd'],
                    self._attr['firstname'],
                    self._attr['lastname'],
                    self._attr['globals'],
                    self._attr['ansi'],
                    self._attr['active'],
                    self._attr['username']  # <- Second username for WHERE clause in UPDATE query
                    ]
        saveUser(userdata)


    def createUser(self):
        """
        Update users in database.
        """
        # This list structure and elements must match bbs.sql.accts.ADDUSER SQL statement structure and elements.
        userdata = [self._attr['username'],
                    self._attr['passwd'],
                    self._attr['firstname'],
                    self._attr['lastname'],
                    self._attr['email'],
                    self._attr['globals'],
                    self._attr['ansi'],
                    self._attr['active']
                    ]
        addUserToDatabase(userdata)

    def authenticate(self, user, passwd):
        """
        Authenticate user against user database.
        """
        hasher = hashlib.sha512()
        hasher.update(passwd.encode('utf-8'))
        # return authQuery(username,
        passwd = hasher.hexdigest()
        
        
class Roles:
    """
    Roles class assign BBS permissions.

    Database Table: roles
    Roles permissions are are hard coded into the BBS and use
    an predefined integer that links them to the defined permission.
    """
    def __init__(self):
        """
        Initialize BBS Roles
        """
        self._id = None
        self._name = None
        self._role = None


class Groups:
        """
        Initialize BBS Groups

        Database Table: groups
        id = primary_key
        name = String, nullable=False
        user = Integer, ForeignKey('users.id'), nullable=False
        """
        def __init__(self):
            self._id = None
            self._name = None
            self._user = None


class GroupPermissions:
        """
        Initialize BBS Group Permissions

        Database Table: group_perms

        id = primary_key
        group = Integer, ForeignKey('groups.id'), nullable=False
        role = Integer, ForeignKey('roles.id'), nullable=True
        """
        def __init__(self):
            self._id = None
            self._group = None
            self._role = None


class AccountGroupings:
    """
    User to Group relationships

    Database Table: user_perms

    id = primary_key
    user = Integer, ForeignKey('users.id'), nullable=False
    group = Integer, ForeignKey('groups.id'), nullable=False
    """
    def __init__(self):
        self._id = None
        self._user = None
        self._group = None


def initializeUserAccounting():
    """
    Initialize user accounting system.
    """
    global conn
    global cursor

    try:
        conn = sqlite3.connect(os.path.join('data', 'bbs.db'))
        cursor = conn.cursor()
    except:
        logging.error("Failed trying to load database for using accounting.")



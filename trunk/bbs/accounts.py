import logging
import sqlite3
import os


from sonzoserv.telnet import TelnetProtocol
from bbs.board import parser, BBSUSERS, splash, sendClient
from bbs.menu import getFullMenu, getMiniMenu


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
        self._id = 1
        self._status = None
        self._username = ''
        self._password = ''
        self.door = None
        self._globals = True
        self._menu = 'MAINMENU'
        self._parser = parser


    def onConnect(self):
        """
        onConnect()
        """
        # Remove this once login code is complete
        self.username = self._port
        BBSUSERS.append(self)
        splash(self)
        sendClient(self, getFullMenu(self), colorcodes=True)


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
        self._menu = menu


    def getMenu(self):
        """
        Get users current menu.
        """
        return self._menu



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



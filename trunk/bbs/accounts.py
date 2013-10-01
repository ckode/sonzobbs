import logging

from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from sonzoserv.telnet import TelnetProtocol
from bbs.board import parser, BBSUSERS, splash, sendClient
from bbs.menu import getFullMenu, getMiniMenu

Base = declarative_base()
accounts = create_engine('sqlite:///data/users.db', echo=True)
Base.metadata.create_all(accounts)
bbs = create_engine('sqlite:///data/bbs.db', echo=True)
Base.metadata.create_all(bbs)

class Account(TelnetProtocol, Base):
    """
    Server side BBS account object.
    """
    
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    fname = Column(String)
    lname = Column(String)
    password = Column(String)
    #ban = ""
    #globals = Column(Integer)
    #account_class = Column(Integer)
    
    
    def __init__(self, sock, addr):
        """
        Initialize a BBS Account object.
        """
        TelnetProtocol.__init__(self, sock, addr)
        self.status = None
        self.username = ''
        self.password = ''
        self.acctclasses = []
        self.door = None
        self.globals = True
        self.menu = 'MAINMENU'
        self.parser = parser
        
 
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
        
        
    def dataRecieved(self, data):
        """
        dataRecieved()
        """
        parser(self, data)
        
        
    def setMenu(self, menu):
        """
        Set users current menu.
        """
        self.menu = menu
    
    
    def getMenu(self):
        """
        Get users current menu.
        """
        return self.menu
        

class Roles(Base):

    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
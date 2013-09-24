import logging


from sonzoserv.telnet import TelnetProtocol
from bbs.board import BBSUSERS, parser, splash, sendClient
from bbs.menu import getFullMenu, getMiniMenu



class Account(TelnetProtocol):
    """
    Server side BBS account object.
    """
    
    def __init__(self, sock, addr):
        """
        Initialize a BBS Account object.
        """
        TelnetProtocol.__init__(self, sock, addr)
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
        
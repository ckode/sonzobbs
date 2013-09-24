import logging
import os
import string

from bbs.menu import getMenuOptions, menuOptionSelected, MenuOptionException
from bbs.menu import getMiniMenu, getFullMenu, verifyMenuDatabase

from bbs.doors import DoorEngine

BBSUSERS = []
BBS = None
SERVER = None
SPLASH = None

stripchars = string.printable.replace(chr(10) + chr(13), '')
ANSI_CODES = (
    ( '^k', '\x1b[22;30m' ),    # black
    ( '^K', '\x1b[1;30m' ),     # bright black (grey)
    ( '^r', '\x1b[22;31m' ),    # red
    ( '^R', '\x1b[1;31m' ),     # bright red
    ( '^g', '\x1b[22;32m' ),    # green
    ( '^G', '\x1b[1;32m' ),     # bright green
    ( '^y', '\x1b[22;33m' ),    # yellow
    ( '^Y', '\x1b[1;33m' ),     # bright yellow
    ( '^b', '\x1b[22;34m' ),    # blue
    ( '^B', '\x1b[1;34m' ),     # bright blue
    ( '^m', '\x1b[22;35m' ),    # magenta
    ( '^M', '\x1b[1;35m' ),     # bright magenta
    ( '^c', '\x1b[22;36m' ),    # cyan
    ( '^C', '\x1b[1;36m' ),     # bright cyan
    ( '^w', '\x1b[22;37m' ),    # white
    ( '^W', '\x1b[1;37m' ),     # bright white
    ( '^0', '\x1b[40m' ),       # black background
    ( '^1', '\x1b[41m' ),       # red background
    ( '^2', '\x1b[42m' ),       # green background
    ( '^3', '\x1b[43m' ),       # yellow background
    ( '^4', '\x1b[44m' ),       # blue background
    ( '^5', '\x1b[45m' ),       # magenta background
    ( '^6', '\x1b[46m' ),       # cyan background
    ( '^d', '\x1b[39m' ),       # default (should be white on black)
    ( '^I', '\x1b[7m' ),        # inverse text on
    ( '^i', '\x1b[27m' ),       # inverse text off
    ( '^~', '\x1b[0m' ),        # reset all
    ( '^U', '\x1b[4m' ),        # underline on
    ( '^u', '\x1b[24m' ),       # underline off
    ( '^!', '\x1b[1m' ),        # bold on
    ( '^.', '\x1b[22m'),        # bold off
    ( '^s', '\x1b[2J'),         # clear screen
    ( '^l', '\x1b[2K'),         # clear to end of line
    )

class SonzoBBS:
    """
    SoznoBBS Class
    """
    
    def __init__(self, config):
        """
        Initalize SonzoBBS Class
        """
        global SPLASH
        global SERVER
        
        self.version = config['version']
        self._bbsname = config['bbsname']
        verifyMenuDatabase()
        
        try:
            with open(os.path.join('data', 'splash.txt'), "r") as fp:
                SPLASH = fp.read()
        except:
            logging.info(" No Splash screen found.")
            SPLASH = None
        
        
        # Temp stuff to listen for a test door program
        dodoors = True
        if dodoors:
            # The following, is a test door defined.
            cfgs = []
            first = {}
            first['PORT'] = '2222'
            first['NAME'] = 'Teleconference'
            first['IP'] = '*'
            first['ID'] = 'TELECONFERENCE'
            cfgs.append(first)
            
            self.doors = DoorEngine(cfgs)
            if self.doors:
                # Install the function to process the door messages 
                # into the main loop.
                SERVER.install(func=self.doors.processDoors) 
        
        logging.info(" Sonzo BBS version {}".format(self.version))        
        logging.info(" Listening for connections...  CTRL-C to break.")
        #self.run()

        

        
def parser(client, line):
    """
    Parse the line.
    """
    global stripchars
    
    # Need to look for global messages before this.
    if client.door:
        BBS.doors.sendDoorMessage(client.username, client.door, line)
        return
    
    line = line.upper()
    line = "".join(filter(lambda x: x in stripchars, line))
    opts = getMenuOptions(client.getMenu())
    if line in opts:
        try:
            menuOptionSelected(client, line)
            sendClient(client, getFullMenu(client), colorcodes=client.inANSIMode())
        except MenuOptionException as e:
            # Probably should never see this raised exception.  It's a safety net.
            if e.__repr__() == "INVALID":
                sendClient(client, '\n^G<= ^MInvalid selection, please try again. ^G=>\n', colorcodes=client.inANSIMode())
                sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())
            elif e.__repr__() == "MenuOptionException('LOGOFF',)":
                sendClient(client, "^GGoodbye!", colorcodes=client.inANSIMode())
                client.disconnect()
                return
            else:
                if BBS.doors.hasDoor(e.message):
                    client.door = e.message
                    BBS.doors.connectUser(client.username, e.message)
                
                #sendClient(client, '\n^G<= ^MEntering Door ^G=>\n', colorcodes=client.inANSIMode())
                #sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())
                return
    else:
        sendClient(client, '\n^G<= ^MInvalid selection, please try again. ^G=>\n', colorcodes=client.inANSIMode())
        sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())

        
def splash(client):
    """
    Do splash screen on initial login.
    """
    sendClient(client, colorize(SPLASH, client.inANSIMode()))


def strip_caret_codes(text):
    """
    Strip out any caret codes from a string.
    """
    ## temporarily escape out ^^
    text = text.replace('^^', '\x00')
    for token, foo in ANSI_CODES:
        text = text.replace(token, '')
    return text.replace('\x00', '^')
    
    
def colorize(text, ansi=True):
    """
    If the client wants ansi, replace the tokens with ansi sequences --
    otherwise, simply strip them out.
    """
    global ANSI_CODES
    if ansi:
        text = text.replace('^^', '\x00')
        for token, code in ANSI_CODES:
            text = text.replace(token, code)
        text = text.replace('\x00', '^')
    else:
        text = strip_caret_codes(text)
    return text 
        
        
def sendClient(client, data, **kw):
    """
    Send data to user.
    """
    if 'colorcodes' in kw.keys():
        client.send(colorize(data, client.inANSIMode()))
    else:
        client.send(data)
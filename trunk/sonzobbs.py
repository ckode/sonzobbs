from sonzoserv.telnet import TelnetServer
from bbs.accounts import Account
#from bbs.board import SonzoBBS, BBS, SERVER
import bbs.board

import logging




if __name__ == '__main__':
    global SERVER
    # Delete this conf dict once configurations are setup.
    config = {'bbsname': "Sonzo BBS",
              'port': 23,
              'addr': '',
              'timeout': 0.1
             }
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)         
    #logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)         
    #logging.basicConfig(filename='sonzobbs.log', loglevel=logging.WARNING)
    bbsaccount = Account
    
    cfg = {'bbsname': 'SonzoBBS', 'version': 0.1}
    bbs.board.SERVER = TelnetServer(client=bbsaccount, address='', port=23)
    #print(SERVER)
    bbs.board.BBS = bbs.board.SonzoBBS(cfg)
    bbs.board.SERVER.run()
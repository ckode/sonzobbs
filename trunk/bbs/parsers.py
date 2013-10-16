import string

from bbs.board import sendClient, splash
from bbs.menu import getMenuOptions, menuOptionSelected, MenuOptionException
from bbs.menu import getMiniMenu, getFullMenu, verifyMenuDatabase, getLoginScreen
from bbs.sql.accts import authUser, getUserFromDatabase
from bbs.menu import getPasswordScreen

import bbs.board

PASSWDSIZE = 6
stripchars = string.printable.replace(chr(10) + chr(13), '')

def parser(client, line):
    """
    Parse the line.
    """
    global stripchars
    #global BBS
    
    #line = line.upper()
    line = "".join(filter(lambda x: x in stripchars, line))

    if client.getAttr('state') != 'AUTHENTICATED':
        login_parser(client, line)
        return
    
    # Need to look for global messages before this.
    if client.getAttr('door'):
        BBS.doors.sendDoorMessage(client.getAttr('username'), client.getAttr('door'), line)
        return


    if line == "":
        sendClient(client, getFullMenu(client), colorcodes=client.inANSIMode())
        return

    opts = getMenuOptions(client.getMenu())
    if line.upper() in opts:
        try:
            menuOptionSelected(client, line)
            sendClient(client, getFullMenu(client), colorcodes=client.inANSIMode())
        except MenuOptionException as e:
            # Probably should never see this raised exception.  It's a safety net.
            if e.__repr__() == "INVALID":
                sendClient(client, '\n^G<= ^MInvalid selection, please try again. ^G=>\n',
                           colorcodes=client.inANSIMode())
                sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())
            elif e.__repr__() == 'LOGOFF':
                sendClient(client, "^GGoodbye!", colorcodes=client.inANSIMode())
                client.disconnect()
                return
            else:
                if bbs.board.BBS.doors.hasDoor(e.message):
                    if bbs.board.BBS.doors.connectUser(client.getAttr('username'), e.message):
                        client.setAttr('door', e.message)
                    else:
                        sendClient(client, '\n^G<= ^MSorry, {} appears to be off-line. ^G=>\n'.format(e.message),
                                   colorcodes=client.inANSIMode())
                        sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())
                return
    else:
        sendClient(client, '\n^G<= ^MInvalid selection, please try again. ^G=>\n', colorcodes=client.inANSIMode())
        sendClient(client, getMiniMenu(client), colorcodes=client.inANSIMode())


def login_parser(client, input):
    """
    Parser for logging client in.
    """
    state = client.getAttr('state')

    if state.startswith('SIGNUP'):
        signup_parser(client, state, input)
        return

    if state == 'CONNECTING':
        if input == "":
            sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())
            return
        elif input.lower() == 'new':
            client.setAttr('state', 'SIGNUP-GETNAME')
            sendClient(client, "\n^GPlease enter a username you would like to use: ", colorcodes=client.inANSIMode())
            client.uname_attempt = 0
            return
        elif len(input) > 1:
            user = getUserFromDatabase(input)
            if user:
                client.setAttr('state', 'LOGIN')
                client.setAttr('username', user['username'])
                client.password_mode_on()
                sendClient(client, getPasswordScreen(), colorcodes=client.inANSIMode())
            else:
                sendClient(client, "\n^GThat user does not exist.  Please try again.", colorcodes=client.inANSIMode())
                sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())
            return
        
    elif state == 'LOGIN':
        client.password_mode_off()
        if input == '':
            client.setAttr('state', 'CONNECTING')
            sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())
        if len(input) > 2:
            if authUser(client.getAttr('username'), input):
                client.loadUser()
                sendClient(client, getFullMenu(client), colorcodes=client.inANSIMode())
            else:
                sendClient(client, "^MInvalid login, please try again.\n", colorcodes=client.inANSIMode())
                client.setAttr('state', 'CONNECTING')
                client.setAttr('username', '')
                sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())


def signup_parser(client, state, input):
    """
    Parser user input for newly joining members.
    """
    global PASSWDSIZE
    
    if state == 'SIGNUP-GETNAME':
        if input == "" or len(input) < 2 or getUserFromDatabase(input):
            sendClient(client, "\n^GSorry, that name is already in use, or invalid. Please try a gain.", colorcodes=client.inANSIMode())
            sendClient(client, "\n^GPlease enter a username you would like to use: ", colorcodes=client.inANSIMode())
            client.uname_attempt = client.uname_attempt + 1
            if client.uname_attempt == 3:
                client.setAttr('state', 'CONNECTING')
                splash(client)
                sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())                    
            return
        else:
            client.setAttr('state', 'SIGNUP-VERIFYNAME')
            client.setAttr('username', input)
            sendClient(client, "\n^GExample: ^g{} says, ^wHello, how are you?".format(input), colorcodes=client.inANSIMode())
            sendClient(client, "\n^GIs this okay?  (y/n): ", colorcodes=client.inANSIMode())
            return
    elif state == 'SIGNUP-VERIFYNAME':
        if input.lower() == 'y' or input.lower() == 'yes':
            client.pwd_attempt = 0
            client.setAttr('state', 'SIGNUP-PASSWORD')
            sendClient(client, "Please enter a password you would like to use: ", colorcodes=client.inANSIMode())
            client.password_mode_on()
            return
        else:
            client.setAttr('state', 'SIGNUP-GETNAME')
            sendClient(client, "^GPlease enter a username you would like to use: ", colorcodes=client.inANSIMode())
            return
    elif state == 'SIGNUP-PASSWORD':
        client.pwd_attempt = client.pwd_attempt + 1
        if client.pwd_attempt == 3:
            client.setAttr('state', 'CONNECTING')
            splash(client)
            sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())                
            return
        if len(input) > PASSWDSIZE:
            client.tmppass = input
            client.setAttr('state', 'SIGNUP-VERIFYPASSWORD')
            sendClient(client, "^GPlease verify your password: ", colorcodes=client.inANSIMode())
            return
        else:
            sendClient(client, "\n^GYour password must consist of at least {} characters.".format(PASSWDSIZE + 1), colorcodes=client.inANSIMode())
            sendClient(client, "\nPlease enter a password you would like to use: ", colorcodes=client.inANSIMode())
            return
    elif state == 'SIGNUP-VERIFYPASSWORD':
        if input == client.tmppass:
            client.password_mode_off()
            import hashlib
            hasher = hashlib.sha512()
            hasher.update(input.encode('utf-8'))
            client.setAttr('passwd', hasher.hexdigest())
            client.setAttr('state', 'AUTHENTICATED')
            # Remove this once completed signin process.
            client.setAttr('firstname', 'Jon')
            client.setAttr('lastname', 'Doe')
            client.setAttr('email', 'here@there.com')
            client.setAttr('ansi', client._ansi)
            client.createUser()
            sendClient(client, "\n^MWelcome!", colorcodes=client.inANSIMode())
            return
        else:
            client.pwd_attempt = client.pwd_attempt + 1
            if client.pwd_attempt == 4:
                client.setAttr('state', 'CONNECTING')
                splash(client)
                sendClient(client, getLoginScreen(), colorcodes=client.inANSIMode())
                return
            client.tmppass = ''
            client.setAttr('state', 'SIGNUP-PASSWORD')
            sendClient(client, "\nYou password does not match, please try again.", colorcodes=client.inANSIMode())
            sendClient(client, "\nPlease enter a password you would like to use: ", colorcodes=client.inANSIMode())
            client.pwd_attempt = 0
            return
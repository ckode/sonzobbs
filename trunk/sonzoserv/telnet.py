#   Copyright 2013 David Brown - dcbrown73 - at - yahoo - . - com
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ##########################################################################
#
# Source taken from the miniboa is Copyright 2009 Jim Storch
#
# Miniboa Source  https://code.google.com/p/miniboa/
#
#  Licensed under the Apache 2 License
#
# ##########################################################################
#
# Changes made by Mark Richardson November 2012
# -Removed dict has_key references as they are not Python 3 compatible.
# -Added support for detecting the terminal speed.
# -Added an Auto-Sensing feature that allows a dict of required terminal
#  features to be detected upon initial connection.
# 
# Omegus Source: https://github.com/Omegus/miniboa
#
# Licensed under the Apache 2 license
#
# ##########################################################################


import logging
import socket
import select
import sys
import re
import time

from sonzoserv.task import LoopingCall, CallLater, InstallFunction
from collections import deque


#--[ Global Constants ]--------------------------------------------------------

UNKNOWN = -1
## Cap sockets to 512 on Windows because winsock can only process 512 at time
## Cap sockets to 1000 on Linux because you can only have 1024 file descriptors
MAX_CONNECTIONS = 512 if sys.platform == 'win32' else 1000
PARA_BREAK = re.compile(r"(\n\s*\n)", re.MULTILINE)
AUTOSENSE_TIMEOUT = 2

#--[ Telnet Commands ]---------------------------------------------------------

SE      = chr(240)      # End of subnegotiation parameters
NOP     = chr(241)      # No operation
DATMK   = chr(242)      # Data stream portion of a sync.
BREAK   = chr(243)      # NVT Character BRK
IP      = chr(244)      # Interrupt Process
AO      = chr(245)      # Abort Output
AYT     = chr(246)      # Are you there
EC      = chr(247)      # Erase Character
EL      = chr(248)      # Erase Line
GA      = chr(249)      # The Go Ahead Signal
SB      = chr(250)      # Sub-option to follow
WILL    = chr(251)      # Will; request or confirm option begin
WONT    = chr(252)      # Wont; deny option request
DO      = chr(253)      # Do = Request or confirm remote option
DONT    = chr(254)      # Don't = Demand or confirm option halt
IAC     = chr(255)      # Interpret as Command
SEND    = chr(  1)      # Sub-process negotiation SEND command
IS      = chr(  0)      # Sub-process negotiation IS command

#--[ Telnet Options ]----------------------------------------------------------

BINARY  = chr(  0)      # Transmit Binary
ECHO    = chr(  1)      # Echo characters back to sender
RECON   = chr(  2)      # Reconnection
SGA     = chr(  3)      # Suppress Go-Ahead
STATUS  = chr(  5)      # Status of Telnet Options
TTYPE   = chr( 24)      # Terminal Type
NAWS    = chr( 31)      # Negotiate About Window Size
TSPEED  = chr( 32)      # Terminal Speed
LINEMO  = chr( 34)      # Line Mode


Telopts = {
    chr(0): "Binary representation",
    chr(1): "Server Echo",
    chr(2): "Reconnection",
    chr(3): "Supress Go Ahead (SGA)",
    chr(4): "Approx Message Size Negotiation",
    chr(5): "Status",
    chr(6): "Timing Mark",
    chr(7): "Remote Controlled Trans and Echo",
    chr(8): "Output Line Width",
    chr(9): "Output Page Size",
    chr(10): "Output Carriage-Return Disposition",
    chr(11): "Output Horizontal Tab Stops",
    chr(12): "Output Horizontal Tab Disposition",
    chr(13): "Output Formfeed Disposition",
    chr(14): "Output Vertical Tabstops",
    chr(15): "Output Vertical Tab Disposition",
    chr(16): "Output Linefeed Disposition",
    chr(17): "Extended ASCII",
    chr(18): "Logout",
    chr(19): "Byte Macro",
    chr(20): "Data Entry Terminal",
    chr(21): "SUPDUP",
    chr(22): "SUPDUP Output",
    chr(23): "Send Location",
    chr(24): "Terminal Type",
    chr(25): "End of Record",
    chr(26): "TACACS User Identification",
    chr(27): "Output Marking",
    chr(28): "Terminal Location Number",
    chr(29): "Telnet 3270 Regime",
    chr(30): "X.3 PAD",
    chr(31): "Negotiate About Window Size (NAWS)",
    chr(32): "Terminal Speed",
    chr(33): "Remote Flow Control",
    chr(34): "Line Mode",
    chr(35): "X Display Location",
    chr(36): "Environment Option",
    chr(37): "Authentication Option",
    chr(38): "Encryption Option",
    chr(39): "New Environment Option",
    chr(40): "TN3270E",
    chr(41): "XAUTH",
    chr(42): "CHARSET",
    chr(43): "Telnet Remote Serial Port (RSP)",
    chr(44): "Com Port Control Option",
    chr(45): "Telnet Suppress Local Echo",
    chr(46): "Telnet Start TLS",
    chr(47): "KERMIT",
    chr(48): "SEND-URL",
    chr(49): "FORWARD_X",
    chr(138): "TELOPT PRAGMA LOGON",
    chr(139): "TELOPT SSPI LOGON",
    chr(140): "TELOPT PRAGMA HEARTBEAT",
    chr(255): "Extended-Options-List"
    }

#--[ Terminal Type enumerations - Mark Richardson Nov 2012]--------------------
TERMINAL_TYPES = ['ANSI', 'XTERM', 'TINYFUGUE', 'zmud', 'VT100', 'IBM-3179-2']

#--[ Connection Lost ]---------------------------------------------------------

class ConnectionLost(Exception):
    """
    Custom exception to signal a lost connection to the Telnet Server.
    """
    
    
    
class TelnetServer(object):
    """
    Telnet Server
    """
    
    def __init__(self, address='', client='', port=23, timeout=0.1):
        """
        Initialize a new TelnetServer.
        
        Initialized by passing keyword arguments.  If no keywords are passed, 
        the defaults are used.
        
        def __init__(self, address='', client=TelnetProtocol, port=23, timeout=0.1):
        
        - client: A class defintion that handles the client's telnet protocol negotiations.
        - address: IP Address to bind too.
        - port: Port to bind too.
        - timeout: Socket polling timeout.
        
        The client must be the local TelnetProtocol class or a subclass of the TelnetProtocol.
        """
        if sys.version_info[0] is not 3:
            logging.error(" Python version 3 is required for this application.")
            sys.exit(1)
            
        self._SERVER = True
        self._addr = address
        self._port = port
        self._timeout = timeout
        self._clients = {}
        self._negotiating_clients = {}
        self._deadclients = []
        if client == '':
            self._clientclass = TelnetProtocol
        else:
            self._clientclass = client
        
        # Embbed function in run() loop
        self._installedFunctions = []
        # Installed, timed looping calls.
        self._loopingCalls = []
        # Functions to be called later.
        self._callLater = [] 
        
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self._socket.bind((self._addr, self._port))
            self._socket.listen(5)
        except socket.error as err:
            logging.critical("Error: Failed to create the server socket: " + str(err))
            raise
        
        self._server_fileno = self._socket.fileno()
    
        
    def run(self):
        """
        Start Telnet Server's Main Loop.
        
        Example:
        - <srvr>.run()
        """
        while self._SERVER:
            self._poll()
            
            # Execute installed functions
            for function in self._installedFunctions:
                function.execute()
                
            # Excute timed loopingCalls.
            for call in self._loopingCalls:
                call.execute()
                    
            # Execute callLater functions then remove from self.callLater list.
            for call in self._callLater:
                if call.runtime <= time.time():
                    call.execute()
                    self._callLater.remove(call)

            self._processClients()                    
    
        logging.info(" Shutting down.")
        self._clients.clear()
        self._negotiating_clients.clear()        
        sys.exit(1)
        
        
    def onConnect(self, client):
        """
        New connection handler
        
        Override with custom connection code.
        """
        pass

    
    def onDisconnect(self, client):
        """
        Disconnect handler
        
        Override with custom disconnect code.
        """
        pass
     
    
    def install(self, *args, **kwargs):
        """
        Install a function to be executed during the main loop.
        
        Example:
        - obj.install(arg1, <arg2>, ..., func=<func>)
        """
        if kwargs['func']:
            newcall = InstallFunction(*args, func=kwargs['func'])
            if newcall:
                self._installedFunctions.append(newcall)
        else:
            logging.error("Error: Could not install function. Required 'func' keyword missing from TelnetServer.install() call")


    def shutdown(self):
        """
        Disconnect all users and shutdown.
        
        Example:
        - <srvr>.shutdown()
        """
        self._SERVER = False    
        
        
    def loopingCall(self, *args, **kwargs):
        """
        Install looping call.
        
        newobj = obj.loopingCall(arg1, <arg2>, ..., func=<func>)
        newobj.start(<delay>)
        
        Delay is an int or float and specified in seconds.
        """
        if kwargs['func']:
            newcall = LoopingCall(*args, func=kwargs['func'])
        
        if newcall:
            self._loopingCalls.append(newcall)
        else:
            logging.error("Error: Could not install loopingCall function.")
    
        return newcall
    
    
    def callLater(self, *args, **kwargs):
        """
        Install a function to be called after a delay of <x> seconds.
        
        Example:
        -  obj.callLater(arg1, <arg2>, ..., func=<your_function>, delay=<value>)
        
        Delay is a int or float specified in seconds.
        """
        if kwargs['func'] and kwargs['delay']:
            newcall = CallLater(*args, func=kwargs['func'], delay=kwargs['delay'])
        
        if newcall:
            self._callLater.append(newcall)
        else:
            logging.error("Error: Could not install callLater function.") 


    def _clientCount(self):
        """
        Return current connection count.
        """
        return len(self._clients)

                    
    def _processClients(self):
        """
        Process client's input.
        """
        for client in self._clients.values():
            while True:
                msg = client._getCommand()
                if not msg:
                    break
                else:
                    client.dataRecieved(msg)  


    def _poll(self):
        """
        Poll the server for new connections and handling OI for existing
        connections.
        """
        recv_list = [self._server_fileno]
        dead_list = []
        done_negotiating = []
        
        for client in self._negotiating_clients.values():
            client._check_auto_sense()
            if client._protocol_negotiation == True:
                self._clients[client._getSocket()] = client
                done_negotiating.append(client._getSocket())
                client.onConnect()
                
        
        for client in self._clients.values():
            if client._isConnected():
                recv_list.append(client._getSocket())
            else:
                client.onDisconnect()
                dead_list.append(client._getSocket())
                
        for client in self._negotiating_clients.values():
            if client._isConnected():
                recv_list.append(client._getSocket())
            else:
                done_negotiating.append(client._getSocket())                

        send_list = []
        for client in self._clients.values():
            if client._sendPending() or client._echo_buffer:
                send_list.append(client._getSocket())

        for client in self._negotiating_clients.values():
            if client._sendPending():
                send_list.append(client._getSocket())
                
        try:                
            rlist, slist, elist = select.select(recv_list, send_list, [], self._timeout)    
        except socket.error as err:
            logging.critical("Socket Select() error: '{}: {}'".format(err[0], err[1]))
            raise
        
        for fileno in rlist:
            # Is it the server's socket for a new connection?
            if fileno == self._server_fileno:
                try:
                    sock, addr = self._socket.accept()
                except socket.error as err:
                    logging.error("Socket error on accept(): '{}: {}'".format(err[0], err[1]))
                    sock.close()
                    continue
            
                if self._clientCount() >= MAX_CONNECTIONS:
                    logging.warning("New connection rejected.  Maximum connection count reached.")
                    self.rejectNewConnection()
                    sock.close()
                    continue

                #new_client = self.newConnection(sock, addr)
                new_client = self._clientclass(sock, addr)
                new_client._request_will_echo()
                new_client._detect_term_caps()
                self._negotiating_clients[new_client._getSocket()] = new_client
                continue
            
            if fileno in self._clients.keys():  
                try: 
                    self._clients[fileno]._recv()
                except ConnectionLost:
                    onDisconnect()
                    
            elif fileno in self._negotiating_clients.keys():            
                try: 
                    self._negotiating_clients[fileno]._recv()
                except ConnectionLost:
                    done_negociating.append(fileno)
                    
        # Send pending buffers to client        
        for fileno in slist:
            if fileno in self._clients.keys():
                self._clients[fileno]._send()
            elif fileno in self._negotiating_clients.keys():
                self._negotiating_clients[fileno]._send()
        
        # remove clients no longer connected        
        for dead in dead_list:
            del self._clients[dead] 
        del dead_list            

                # Remove clients from negotiating list once done.
        for dead in done_negotiating:
            del self._negotiating_clients[dead]
        del done_negotiating 


        
class TelnetOption(object):
    """
    Simple class used to track the status of an extended Telnet option.
    """
    def __init__(self):
        self.local_option = UNKNOWN     # Local state of an option
        self.remote_option = UNKNOWN    # Remote state of an option
        self.reply_pending = False      # Are we expecting a reply?
        self.option_text = "Unknown"    # Friendly text for debug or display
    
        
       
        
class TelnetProtocol(object):
    """
    Telent Client Class
    """
    
    def __init__(self, socket, addr):
        """
        Initialize a new client object.
        """

        self._protocol = "telnet"
        self._protocol_negotiation = False
        self._connected = True
        self._new_messages = True
        self._socket = socket
        self._fileno = self._socket.fileno()
        self._addr = addr[0]
        self._port = addr[1]
        self._cmd_list = deque()
        self._terminal_type = 'UNKNOWN'
        self._terminal_speed = 'UNKNOWN'
        self._character_mode = False
        self._cmd_ready = False
        self._cmd_list = deque()
        self._ansi = False
        self._columns = 80
        self._rows = 24
        self._send_pending = False
        self._echo_buffer = ''
        self._echo_buffer_count = 0
        self._send_buffer = ''
        self._recv_buffer = ''
        self._connect_time = time.time()
        self._autosensetimeout = None
        # If you want to kick for being idle too long
        self._last_message = time.time()
        # Are we kicking the client off?
        self._kicked = False
        
        
        ## State variables for interpreting incoming telnet commands
        self._telnet_got_iac = False        # Are we inside an IAC sequence?
        self._telnet_got_cmd = None         # Did we get a telnet command?
        self._telnet_got_sb = False         # Are we inside a subnegotiation?
        self._telnet_opt_dict = {}          # Mapping for up to 256 TelnetOptions
        self._telnet_echo = False           # Echo input back to the client?
        self._telnet_echo_password = False  # Echo back '*' for passwords?
        self._telnet_sb_buffer = ''         # Buffer for sub-negotiations
        self._auto_sensing_done = False     #True when all the negotiations are done    


    
    def dataRecieved(self, data):
        """
        Return data recived.
        
        Override this function.
        """
        pass
        
        
    def inCharacterMode(self):
        """
        Is the client in character mode? 
        
        Example:
        - obj.inCharacterMode()
        """
        if self._character_mode:
            return True
        else:
            return False
    
    def setCharacterMode(self):
        """
        Set client Character Mode opposite of what it is now.
        
        Example:
        - obj.setCharacterMode()
        """
        if self._character_mode:
            self._character_mode = False
        else:
            self._character_mode = True
            
            
    def getCharacterMode(self):
        """
        Return which mode the client is currently in.
        
        (Character Mode / LineMode
        
        Example:
        - get.setCharacterMode()
        """
        return self._character_mode
        

    def inANSIMode(self):
        """
        Return current ANSI setting.
        
        Example:
        - obj.inANSIMode()
        """
        return self._ansi
    
    
    def setANSIMode(self):
        """
        Change ANSI mode to opposite what it is now.
        
        Example:
        - obj.setANSIMode()
        """
        if self._ansi:
            self._ansi = False 
        else:
            self._ansi = True

        
    def getAddrPort(self):
        """
        Return the client's IP address and port number as a list.
        
        Example: (unpacked)
        - addr, port = obj.getAddrPort()
        Exmaple: (packed)
        - addrport = obj.getAddrPort()
        """
        return "{}:{}".format(self._addr, self._port)        


    def disconnect(self):
        """
        Disconnect user.

        Example:
        - obj.disconnect()
        """
        self._new_messages = False
        self._connected = False		
        
    def send(self, message):
        """
        Add new messages to the client.
        
        Example:
        - obj.send(message)
        """
        if self._new_messages:
            self._send_buffer = self._send_buffer + message.replace('\n', '\r\n')
            self._send_pending = True
        
           
    def _send(self):
        """
        Called by TelnetServer to send data to the client.
        """
        
        if self._telnet_echo and self._echo_buffer:
            try:
                sent = self._socket.send(bytes(self._echo_buffer, "cp1252"))
            except socket.error as err:
                self._connected = False
                return False            
            self._echo_buffer = ''

            
            
        if self.inCharacterMode():
            try:
                sent = self._socket.send(bytes(self._send_buffer, "cp1252"))
                self._bytes_sent = sent
                self._send_buffer = self._send_buffer[sent:]
            except socket.error as err:
                self._connected = False
                return False 
        else:
            # Is the user currently typing?
            if not len(self._recv_buffer):
                self._send_pending = False
                try:
                    sent = self._socket.send(bytes(self._send_buffer, "cp1252"))
                except socket.error as err:
                    self._connected = False
                    return False            
            
                self._bytes_sent = sent
                self._send_buffer = self._send_buffer[sent:]
            else:
                # Is the users send buffer getting to large while waiting for them to finish typing? Kick them!
                if len(self._send_buffer) > 8388608:
                    self._kicked = True
                    return
                self._send_pending = True
             

            
            
    def _recv(self):
        """
        Called my TelnetServer to recieve data from the client.
        """
        try:
            #Encode recieved bytes in ansi
            data = str(self._socket.recv(2048), "cp1252")
        except socket.error as err:
            logging.error("RECIEVE socket error '{}:{}' from {}".format(err[0], err[1], self.addrport()))
            raise ConnectionLost()        
        
        
        if not len(data):
            logging.debug("No data received.  Connection lost.")
            raise ConnectionLost()
        
        # Workaround for clients that send CR as "\r0" (carrage return plus a null)
        if data == "{}{}".format(chr(13), chr(0)):
            data = "\n"
            
        for byte in data:
            self._iac_sniffer(byte)
             
        if self.inCharacterMode():
            if self._recv_buffer:
                self._cmd_list.append(self._recv_buffer)
                self._recv_buffer = ''
                self._cmd_ready = True
        else:
            while True:
                mark = self._recv_buffer.find('\n')
                if mark == -1:
                    break
                cmd = self._recv_buffer[:mark].strip()
                cmd = cmd + '\n\r'
                self._cmd_list.append(cmd)
                self._cmd_ready = True
                self._recv_buffer = self._recv_buffer[mark+1:]
                

    def _sendPending(self):
        """
        Is there data waiting to send to the client?
        """
        if len(self._send_buffer):
            return True
        return False
    
 
    def _commandReady(self):
        """
        Is there a command ready?
        
        """
        return self._cmd_ready
                    
            
    def _getCommand(self):
        """
        Return first command line command list.
        """
        if self._commandReady() and len(self._cmd_list):
            return self._cmd_list.pop()
        else:
            self._cmd_ready = False
            return
     
            
    def _isConnected(self):
        """
        Is the client connected?
        """
        if self._connected and not self._kicked:
            return True
        return False
    
    
    def _getSocket(self):
        """
        Return client's socket id.
        """
        return self._fileno
    
    
    def _detect_term_caps(self):
        """
        Send initial terminal negotiation options that we need and wait for the
        replies so the variables can be set before moving out of the Auto-Sensing
        phase. Added by Mark Richardson, Nov 2012.
        """
        self.send("Auto-Sensing...\n\r{}{}{}{}{}{}\n\r".format(chr(1), chr(1), chr(1), chr(1), chr(1), chr(1)))
        self._request_terminal_type()
        self._request_terminal_speed()
        self._request_naws()
        self._autosensetimeout = time.time()
                       

    def _check_auto_sense(self):
        """
        Checks the state of the telnet option negotiation started by detect_term_caps()
        to see if they are all completed. If they are then the client_state should
        be changed to allow progress. If we dont get a reply to one of these
        a timer should allow client to proceed.
        """
        if self._check_reply_pending(TTYPE) is False and \
            self._check_reply_pending(TSPEED) is False and \
            self._check_reply_pending(NAWS) is False:
            if(self._terminal_type in TERMINAL_TYPES):
                self._ansi = True
            self._protocol_negotiation = True
            logging.debug("Term Type: {}".format(self._terminal_type))
            return
        
        # For megamud since it reports TTYPE=False, TSPEED=False, NAWS=True, 
        # and a terminal type of IBM-3179-2.
        elif self._check_reply_pending(TTYPE) is False and \
                self._check_reply_pending(TSPEED) is False and \
                self._check_reply_pending(NAWS) is True and \
                self._terminal_type == 'IBM-3179-2':
                self.__ansi = True
                self._protocol_negotiation = True
                logging.debug("Term Type: {}".format(self._terminal_type))
                return
        else:
            if time.time() - self._autosensetimeout > AUTOSENSE_TIMEOUT:
                self._ansi = False
                self._protocol_negotiation = True
                logging.debug("Term Type: {}".format(self._terminal_type))
                return
                
        return
    
# Private telnet negotiation functions

    def _request_do_sga(self):
        """
        Request do Suppress Go-Ahead Option (SGA) RFC-858.
        """
        logging.debug("Requesting suppress go-ahead.")
        self._iac_do(SGA)
        self._note_reply_pending(SGA, True)
        
        
    def _request_will_echo(self):
        """
        Request WILL echo to echo client's text.  RFC-857
        """
        logging.debug("Requesting will echo.")
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)
        self._telnet_echo = True
        
        
    def _request_wont_echo(self):
        """
        Request WON'T echo to not echo client's text.  RC-857
        """
        logging.debug("Requesting won't echo.")
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)
        self._telnet_echo = False        
        
        
    def password_mode_on(self):
        """
        Request disable echo for passwords protection.
        """
        logging.debug("Requesting to disable echo for passwords")
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)
        
        
    def password_mode_off(self):
        """
        Request echo on since we aren't entering a password at this time.
        """
        logging.debug("Request to enable echo since not entering a password at this time.".format(self.address))
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)        
        

    def _request_naws(self):
        """
        Request to Negotiate About Window Size.  See RFC 1073.
        """
        self._iac_do(NAWS)
        self._note_reply_pending(NAWS, True)
        
    
    def _request_terminal_type(self):
        """
        Begins the Telnet negotiations to request the terminal type from
        the client.  See RFC 779.
        """
        self._iac_do(TTYPE)
        self._note_reply_pending(TTYPE, True)
    
        
    def _request_terminal_speed(self):
        """
        Begins the Telnet negotiations to request the terminal speed from
        the client.  See RFC 1079.
        """
        self._iac_do(TSPEED)
        self._note_reply_pending(TSPEED, True)          
    
        
    def _recv_byte(self, byte):
        """
        Non-printable filtering currently disabled because it did not play
        well with extended character sets.
        """
        ## Filter out non-printing characters
        #if (byte >= ' ' and byte <= '~') or byte == '\n':
             
        if self._telnet_echo:
            self._echo_byte(byte)
        if chr(8) is byte or chr(127) is byte:
            if self._recv_buffer is not chr(13) or len(self._recv_buffer) is not 0:
                self._recv_buffer = self._recv_buffer[:-1]
                return
        self._recv_buffer += byte


    def _echo_byte(self, byte):
        """
        Echo a character back to the client and convert LF into CR\LF.
        """ 
        # Enter key hit, reset buffer and append \r        
        if byte == '\n':
            self._echo_buffer += '\r\n'
            self._echo_buffer_count = 0
            return
        # Return gives two bytes. Ignore the second one. (chr(13))
        if byte == chr(13):
            return
            
        if self._telnet_echo_password:
            self._echo_buffer += '*'
        # If  backspace or delete, delete last character in echo as long as there is 
        # a typed character to delete.
        if byte is chr(8) or byte is chr(127):
            if self._echo_buffer_count < 1:
                return
            self._echo_buffer_count = self._echo_buffer_count - 1
            self._echo_buffer += "{}{}".format(chr(8), "{}[0K".format(chr(27)))
        else:
            self._echo_buffer_count = self._echo_buffer_count + 1
            self._echo_buffer += byte


    def _iac_sniffer(self, byte):
        """
        Watches incomming data for Telnet IAC sequences.
        Passes the data, if any, with the IAC commands stripped to
        _recv_byte().
        """
        ## Are we not currently in an IAC sequence coming from the client?
        if self._telnet_got_iac is False:

            if byte == IAC:
                ## Well, we are now
                self._telnet_got_iac = True
                return

            ## Are we currenty in a sub-negotion?
            elif self._telnet_got_sb is True:
                ## Sanity check on length
                if len(self._telnet_sb_buffer) < 64:
                    self._telnet_sb_buffer += byte
                else:
                    self._telnet_got_sb = False
                    self._telnet_sb_buffer = ""
                return

            else:
                ## Just a normal NVT character
                self._recv_byte(byte)
                return

        ## Byte handling when already in an IAC sequence sent from the client
        else:

            ## Did we get sent a second IAC?
            if byte == IAC and self._telnet_got_sb is True:
                ## Must be an escaped 255 (IAC + IAC)
                self._telnet_sb_buffer += byte
                self._telnet_got_iac = False
                return

            ## Do we already have an IAC + CMD?
            elif self._telnet_got_cmd:
                ## Yes, so handle the option
                self._three_byte_cmd(byte)
                return

            ## We have IAC but no CMD
            else:

                ## Is this the middle byte of a three-byte command?
                if byte == DO:
                    self._telnet_got_cmd = DO
                    return

                elif byte == DONT:
                    self._telnet_got_cmd = DONT
                    return

                elif byte == WILL:
                    self._telnet_got_cmd = WILL
                    return

                elif byte == WONT:
                    self._telnet_got_cmd = WONT
                    return

                else:
                    ## Nope, must be a two-byte command
                    self._two_byte_cmd(byte)



    def _two_byte_cmd(self, cmd):
        """
        Handle incoming Telnet commands that are two bytes long.
        """
        logging.debug("Got two byte cmd '{}'".format(ord(cmd)))

        if cmd == SB:
            ## Begin capturing a sub-negotiation string
            self._telnet_got_sb = True
            self._telnet_sb_buffer = ''

        elif cmd == SE:
            ## Stop capturing a sub-negotiation string
            self._telnet_got_sb = False
            self._sb_decoder()

        elif cmd == NOP:
            pass

        elif cmd == DATMK:
            pass

        elif cmd == IP:
            pass

        elif cmd == AO:
            pass

        elif cmd == AYT:
            pass

        elif cmd == EC:
            pass

        elif cmd == EL:
            pass

        elif cmd == GA:
            pass

        else:
            logging.warning("Send an invalid 2 byte command")

        self._telnet_got_iac = False
        self._telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """
        Handle incoming Telnet commmands that are three bytes long.
        """
        cmd = self._telnet_got_cmd
        logging.debug("Got three byte cmd {}:{}".format(ord(cmd), ord(option)))

        ## Incoming DO's and DONT's refer to the status of this end
        if cmd == DO:
            if option == BINARY or option == SGA or option == ECHO:
                
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_local_option(option, True)

                elif (self._check_local_option(option) is False or
                        self._check_local_option(option) is UNKNOWN):
                    self._note_local_option(option, True)
                    self._iac_will(option)
                    ## Just nod unless setting echo
                    if option == ECHO:
                        self._telnet_echo = True

            else:
                ## All other options = Default to refusing once
                if self._check_local_option(option) is UNKNOWN:
                    self._note_local_option(option, False)
                    self._iac_wont(option)

        elif cmd == DONT:
            if option == BINARY or option == SGA or option == ECHO:

                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_local_option(option, False)

                elif (self._check_local_option(option) is True or
                        self._check_local_option(option) is UNKNOWN):
                    self._note_local_option(option, False)
                    self._iac_wont(option)
                    ## Just nod unless setting echo
                    if option == ECHO:
                        self._telnet_echo = False
            else:
                ## All other options = Default to ignoring
                pass


        ## Incoming WILL's and WONT's refer to the status of the client
        elif cmd == WILL:
            if option == ECHO:

                ## Nutjob client offering to echo the server...
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    # No no, bad client!
                    self._iac_dont(ECHO)

            elif option == NAWS or option == SGA:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_remote_option(option, True)

                elif (self._check_remote_option(option) is False or
                        self._check_remote_option(option) is UNKNOWN):
                    self._note_remote_option(option, True)
                    self._iac_do(option)
                    ## Client should respond with SB (for NAWS)

            elif option == TTYPE:
                if self._check_reply_pending(TTYPE):
                    #self._note_reply_pending(TTYPE, False)
                    self._note_remote_option(TTYPE, True)
                    ## Tell them to send their terminal type
                    self.send("{}{}{}{}{}{}".format(IAC, SB, TTYPE, SEND, IAC, SE))

                elif (self._check_remote_option(TTYPE) is False or
                        self._check_remote_option(TTYPE) is UNKNOWN):
                    self._note_remote_option(TTYPE, True)
                    self._iac_do(TTYPE)
            
            elif option == TSPEED:
                if self._check_reply_pending(TSPEED):
                    self._note_reply_pending(TSPEED, False)
                    self._note_remote_option(TSPEED, True)
                    ## Tell them to send their terminal speed
                    self.send("{}{}{}{}{}{}".format(IAC, SB, TSPEED, SEND, IAC, SE))
                    
                elif (self._check_remote_option(TSPEED) is False or
                      self._check_remote_option(TSPEED) is UNKNOWN):
                    self._note_remote_option(TSPEED, True)
                    self._iac_do(TSPEED)                

        elif cmd == WONT:
            if option == ECHO:

                ## Client states it wont echo us -- good, they're not supposes to.
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    self._iac_dont(ECHO)
                    
            if option == TSPEED:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_remote_option(option, False)
                elif (self._check_remote_option(option) is True or
                      self._check_remote_option(option) is UNKNOWN):
                    self._note_remote_option(option, False)
                    self._iac_dont(option)
                self.terminal_speed = "Not Supported"

            elif option == SGA or option == TTYPE:

                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_remote_option(option, False)

                elif (self._check_remote_option(option) is True or
                        self._check_remote_option(option) is UNKNOWN):
                    self._note_remote_option(option, False)
                    self._iac_dont(option)

                ## Should TTYPE be below this?

            else:
                ## All other options = Default to ignoring
                pass
        else:
            logging.warning("Send an invalid 3 byte command")

        self._telnet_got_iac = False
        self._telnet_got_cmd = None


    def _sb_decoder(self):
        """
        Figures out what to do with a received sub-negotiation block.
        """
        bloc = self._telnet_sb_buffer
        if len(bloc) > 2:

            if bloc[0] == TTYPE and bloc[1] == IS:
                self._terminal_type = bloc[2:]
                self._note_reply_pending(TTYPE, False)
                #logging.debug("Terminal type = '{}'".format(self.terminal_type))
                
            if bloc[0] == TSPEED and bloc[1] == IS:
                speed = bloc[2:].split(',')
                self._terminal_speed = speed[0]
                
            if bloc[0] == NAWS:
                if len(bloc) != 5:
                    logging.warning("Bad length on NAWS SB: " + str(len(bloc)))
                else:
                    self._columns = (256 * ord(bloc[1])) + ord(bloc[2])
                    self._rows = (256 * ord(bloc[3])) + ord(bloc[4])

                #logging.info("Screen is {} x {}".format(self.columns, self.rows))

        self._telnet_sb_buffer = ''


    #---[ State Juggling for Telnet Options ]----------------------------------

    ## Sometimes verbiage is tricky.  I use 'note' rather than 'set' here
    ## because (to me) set infers something happened.

    def _check_local_option(self, option):
        """Test the status of local negotiated Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        return self._telnet_opt_dict[option].local_option


    def _note_local_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        self._telnet_opt_dict[option].local_option = state
        self._telnet_opt_dict[option].option_text = Telopts[option]


    def _check_remote_option(self, option):
        """Test the status of remote negotiated Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        return self._telnet_opt_dict[option].remote_option


    def _note_remote_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        self._telnet_opt_dict[option].remote_option = state
        self._telnet_opt_dict[option].option_text = Telopts[option]


    def _check_reply_pending(self, option):
        """Test the status of requested Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        return self._telnet_opt_dict[option].reply_pending


    def _note_reply_pending(self, option, state):
        """Record the status of requested Telnet options."""
        if option not in self._telnet_opt_dict:
            self._telnet_opt_dict[option] = TelnetOption()
        self._telnet_opt_dict[option].reply_pending = state


    #---[ Telnet Command Shortcuts ]-------------------------------------------

    def _iac_do(self, option):
        """Send a Telnet IAC "DO" sequence."""
        self.send("{}{}{}".format(IAC, DO, option))


    def _iac_dont(self, option):
        """Send a Telnet IAC "DONT" sequence."""
        self.send("{}{}{}".format(IAC, DONT, option))


    def _iac_will(self, option):
        """Send a Telnet IAC "WILL" sequence."""
        self.send("{}{}{}".format(IAC, WILL, option))


    def _iac_wont(self, option):
        """Send a Telnet IAC "WONT" sequence."""
        self.send("{}{}{}".format(IAC, WONT, option))

        

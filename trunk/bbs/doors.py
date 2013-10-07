import json
import zmq
import time
import logging
import configparser

import bbs.board

from collections import deque


REQUIRED_OPTIONS = ['ID', 'NAME', 'DESCRIPTION', 'IP', 'PORT', 'NOTIFICATIONS', 'ENABLE', 'MENU', 'MENUOPTION', 'GROUP']

class Door:
    """
    Door Class
    """
    def __init__(self, config):
        """
        Initialize new door.
        """
        self._in = deque()
        self._out = deque()
        self._id = config['ID']
        self._name = config['NAME']
        self._ip = config['IP']
        self._port = config['PORT']
        self._notify = config['NOTIFICATIONS']
        self._desc = config['DESCRIPTION']
        self._state = config['ENABLE']
        self._menu = config['MENU']
        self._menuoption = config['MENUOPTION']
        self._group = config['GROUP']

        # Door connection state info
        self.connected = False
        self.lastMessage = 0
        self.lastHeartbeat = 0
        self.sock = None

        self.HEARTBEAT = {'TYPE': 'HEARTBEAT',
                          'USER': "",
                          'DOOR': '{}'.format(self._name),
                          'MESSAGE': ""
                          }
        self.HEARTBEAT_RESPONSE = {'TYPE': 'HEARTBEAT_RESPONSE',
                                   'USER': "",
                                   'DOOR': '{}'.format(self._name),
                                   'MESSAGE': ""
                                   }
        self.DISCONNECT = {'TYPE': 'DISCONNECT',
                          'USER': '',
                          'DOOR': self._id,
                          'MESSAGE': ""
                          }

        try:
            context = zmq.Context()
            self.sock = context.socket(zmq.PAIR)
            self.sock.bind("tcp://%s:%s" % (self._ip, self._port))
            time.sleep(2)
        except:
            self._state = False
        return

    def run(self):
        """
        Run test server
        """
        while True:
            self.sendMessages()
            msg = self.recieveMessages()
            if msg:
                time.sleep(1)

    def processDoorQueues(self):
        """
        Process outgoing door messages
        and return incoming door messages.
        """
        messages = deque()
        self.sendMessages()
        self.recieveMessages()
        if self._in:
            bbs.board.BBS.handleDoorMessages(self._in)
            self._in.clear()
        elif time.time() - self.lastMessage > 15:
            if self.connected == True:
                self._in.append(self.DISCONNECT)
                self.connected = False
                return
        elif time.time() - self.lastMessage > 5:
            if time.time() - self.lastHeartbeat > 5:
                self.sendHeartbeat()


    def sendHeartbeat(self):
        """
        Send a heartbeat message to door.
        """
        self.lastHeartbeat = time.time()
        self.sendDoorMessage(self.HEARTBEAT)


    def sendDoorMessage(self, message):
        """
        Add new message to queue to send to the door.
        """
        self._out.append(message)
        return

    def recieveMessages(self):
        """
        Receive and queue all messages.
        """
        while True:
            try:
                msg = self.sock.recv(zmq.DONTWAIT)
            except:
                    return
            message = self._unpackDoorMessage(msg)
            if message:
                self.lastMessage = time.time()
                self.connected = True

                if message['TYPE'] == 'HEARTBEAT':
                    self._out.append(self.HEARTBEAT_RESPONSE)
                elif message['TYPE'] == 'HEARTBEAT_RESPONSE':
                    continue
                else:
                    self._in.append(message)
        return

    def connectUser(self, user):
        """
        Connect new user to door.
        """
        CONNECT = {'TYPE': 'SYSTEM',
                   'USER': user,
                   'DOOR': self._id,
                   'MESSAGE': "CONNECT"
                   }
        if self.connected:
            self.sendDoorMessage(CONNECT)
        else:
            # If not connected, tell the BBS that.
            self._in.append(self.DISCONNECT)

    def sendMessages(self):
        """
        Send all waiting messages to door.
        """
        while self._out:
            msg = self._packDoorMessage(self._out.pop())
            if msg:
                try:
                    self.sock.send(msg.encode('ascii', 'ignore'), zmq.NOBLOCK)
                except:
                    logging.error(" Failed sending zmq message: {}".format(msg))


    def _unpackDoorMessage(self, message):
        """
        Convert door message back to a dictionary.
        """
        msg = {}
        try:
            msg = json.loads(message.decode(encoding='ascii'))
        except:
            logging.error(" Unable to unserialize message: {}".format(msg,))
            return False
        # Ensure the messages has all required fields
        if self._validateDoorMessage(msg, False):
            return msg
        else:
            return False

    def _packDoorMessage(self, message):
        """
        Create a door message.
        """
        # Ensure the messages has all required fields
        if self._validateDoorMessage(message, True):
            try:
                msg = json.dumps(message)
            except:
                logging.error(" Unable to serializing message: {}".format(message))
                return False
            return msg
        else:
            return False

    def _validateDoorMessage(self, message, packing):
        """
        Validate door message contains the correct fields.
        """
        if 'TYPE' in message.keys() and \
                'USER' in message.keys() and \
                'DOOR' in message.keys() and \
                'MESSAGE' in message.keys():
            return True
        else:
            if packing:
                logging.error(" Cannot pack invalid Door Message: {}".format(message))
            else:
                logging.error(" Cannot unpack invalid Door Message: {}".format(message))
            return False


def validateDoorConfig(config):
    """
    Validate door message contains the correct fields.
    """
    if 'NAME' in config.keys() and \
            'IP' in config.keys() and \
            'PORT' in config.keys() and \
            'ID' in config.keys():
        return True
    return False


class DoorEngine:
    """
    Door Engine
    """
    def __init__(self, configs):
        """
        Initialize the Door Engine
        """
        self.doors = {}
        for cfg in configs.values():
            if validateDoorConfig(cfg):
                logging.info(" Loading door: {}".format(cfg['ID']))
                self.doors[cfg['ID']] = Door(cfg)

    def connectUser(self, user, door):
        """
        Connect user to a door.
        """
        print("{}".format(self.doors.keys()))
        print(self.doors[door])
        if self.doors[door]:
            print("DOOR STATUS: {}".format(self.doors[door]))
            print("Connected: {}".format(self.doors[door].connected))
            if self.doors[door].connected:
                self.doors[door].connectUser(user)
                return True
        return False


    def hasDoor(self, door):
        """
        Does the door requested by ID exist?
        """
        if door in self.doors.keys():
            return True
        else:
            return False

    def sendDoorMessage(self, user, door, message):
        """
        Send message to a door.
        """
        if self.doors[door]:
            self.doors[door].sendDoorMessage(
                self.makeUserMessage(user, door, message))

    def processDoors(self):
        """
        Recieve a Door Message.
        """
        rep = deque()
        for door in self.doors.values():
            door.processDoorQueues()

        return False

    def makeUserMessage(self, user, door, message):
        """
        Build a normal message (dictionary).
        """
        msg = {'TYPE': 'USER',
               'USER': user,
               'DOOR': door,
               'MESSAGE': message
               }
        return msg



def getDoorConfigs(cfgfile='doors.ini'):
    """
    Read and return a dictionary of dictionary configs
    """
    def _verifySection(section):
        for option in REQUIRED_OPTIONS:
            if not cfg.has_option(section, option):
                logging.error(" {} configuration is missing {} option in the configuration file.".format(section, option))
                return False
        return True

    cfgs = {}
    cfg = configparser.ConfigParser()
    cfg.read(cfgfile)

    for section in cfg.sections():
        if _verifySection(section):
            cfgs[section] = {}
            for option in REQUIRED_OPTIONS:
                cfgs[section][option] = cfg.get(section, option)
        else:
            logging.error(" {} door not loaded due to error loading the configurations.".format(section))


    return cfgs if len(cfg) else None


if __name__ == '__main__':
   print("Running this as an app is pointless, shutting down.")

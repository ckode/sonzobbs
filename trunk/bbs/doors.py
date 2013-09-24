import json
import zmq
import sys
import time
import logging

from collections import deque


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
        self._state = False
        self._name = config['NAME']
        self._ip = config['IP']
        self._port = config['PORT']
        self._id = config['ID']
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
                print(msg)
            time.sleep(1)

    def processDoorQueues(self):
        """
        Process outgoing door messages
        and return incoming door messages.
        """
        self.sendMessages()
        self.recieveMessages()
        if self._in:
            messages = self._in
            self._in.clear()
            return messages

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
        CONNECT = {'TYPE': 'CONNECT',
                   'USER': user,
                   'DOOR': self._id,
                   'MESSAGE': ""
                   }
        self.sendDoorMessage(CONNECT)

    def sendMessages(self):
        """
        Send all waiting messages to door.
        """
        while self._out:
            msg = self._packDoorMessage(self._out.pop())
            if msg:
                try:
                    self.sock.send(msg.encode('ascii', 'ignore'))
                except:
                    logging.error("Error: Failed sending zmq \
                            message: {}".format(msg))

    def _unpackDoorMessage(self, message):
        """
        Convert door message back to a dictionary.
        """
        msg = {}
        try:
            msg = json.loads(message.decode(encoding='ascii'))
        except:
            logging.error("Error: Unable to unserialize \
                    message: {}".format(msg,))
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
                logging.error("Error: Unable to serializing \
                        message: {}".format(message))
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
                logging.error("Error: Cannot pack invalid \
                        Door Message: {}".format(message))
            else:
                logging.error("Error: Cannot unpack invalid \
                        Door Message: {}".format(message))
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
        for cfg in configs:
            if validateDoorConfig(cfg):
                self.doors[cfg['ID']] = Door(cfg)
            #self.doors[cfg['ID']].run()

    def connectUser(self, user, door):
        """
        Connect user to a door.
        """
        if self.doors[door]:
            self.doors[door].connectUser(user)

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
            ret = door.processDoorQueues()
            if ret:
                rep.extend(ret)
        if rep:
            return rep
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


if __name__ == '__main__':
    cfgs = []
    first = {}
    first['PORT'] = '2222'
    first['NAME'] = 'Test Door'
    first['IP'] = '*'
    first['ID'] = 'TESTDOOR'

    cfgs.append(first)
    x = DoorEngine(cfgs)
    #print(x)

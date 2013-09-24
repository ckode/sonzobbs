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

import time

#=======================================================================
# Looping Call Class
#=======================================================================

class LoopingCall(object):
    """
    Looping Call object.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize looping call.
        
        Example:
        - obj = LoopingCall(arg1, <arg2>, ..., func=<func>)
        """
        self._func = kwargs['func']
        self._looptime = False
        self._runtime = time.time() + self._looptime
        self._args = args

        
    def start(self, looptime):
        """
        Start looping call with loop time interval.
        
        Example:
        - obj.start(value)
        """

        if type(looptime) is type(1) or type(looptime) is type(.2):
            self._looptime = looptime
            self._runtime = time.time() + self._looptime
        else:
            return False
    

    def execute(self):
        """
        Execute looping call.
        
        Example:
        - obj.execute()
        """
        if self._looptime:
            if self._runtime <= time.time():
                self._func(*self._args)
                self._runtime = time.time() + self._looptime
                return  
        return
        
        
#=======================================================================
# CallLater Class
#=======================================================================

class CallLater(object):
    """
    Call Later object.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize calllater class.
        
        Example:
        -  obj = CallLater(arg1, <arg2>, ..., func=<your_function>, delay=<value>)
        """
        self._func = kwargs['func']
        self.runtime = time.time() + kwargs['delay']
        self._args = args
        self._kwargs = kwargs
        
        
    def execute(self):
        """
        Execute the previously initialized callLater.
        
        Example:
        - obj.execute()
        """
        result = self._func(*self._args)
        return
        
#=======================================================================
# Installed function Class
#=======================================================================

class InstallFunction(object):
    """
    Installed Function object.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize InstalledFunction class.
        
        Example:
        - obj = InstallFunction(arg1, <arg2>, ..., func=<func>)
        """
        self._func = kwargs['func']
        self._args = args
        self._kwargs = kwargs
        
    def execute(self):
        """
        Execute preivously installed InstalledFunction.
        
        Example:
        - obj.execute()
        """
        self._func(*self._args)
        return
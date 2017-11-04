"""
Wraps the ihcclient in a more user friendly interface to handle lost connection
"""
# pylint: disable=invalid-name, bare-except
import threading
import time
from ihcsdk.ihcclient import IHCSoapClient, IHCSTATE_READY

class IHCController:
    """
    Implements the notification thread and
    will re-authenticate if needed.
    """
    _mutex = threading.Lock()

    def __init__(self, url: str, username: str, password: str):
        self.client = IHCSoapClient(url)
        self._username = username
        self._password = password
        self._ihcevents = {}
        self._notifythread = threading.Thread(target=self._notify_fn)
        self._notifyrunning = False
        self._project = None

    def Authenticate(self) -> bool:
        """Authenticate and enable the registered notifications"""
        with IHCController._mutex:
            if not self.client.Authenticate(self._username, self._password):
                return False
            for ihcid in self._ihcevents:
                self.client.EnableRuntimeValueNotifications(ihcid)
            return True

    def Disconnect(self):
        """Disconnect by stopping the notification thread
        TODO call disconnect on ihcclient
        """
        self._notifyrunning = False

    def GetRuntimeValue(self, ihcid: int):
        """ Get runtime value with re-authenticate if needed"""
        try:
            return self.client.GetRuntimeValue(ihcid)
        except:
            self.Authenticate()
            return self.client.GetRuntimeValue(ihcid)

    def SetRuntimeValueBool(self, ihcid: int, value: bool) -> bool:
        """ Set bool runtime value with re-authenticate if needed"""
        try:
            return self.client.SetRuntimeValueBool(ihcid, value)
        except:
            self.Authenticate()
            return self.client.SetRuntimeValueBool(ihcid, value)

    def SetRuntimeValueInt(self, ihcid: int, value: int) -> bool:
        """ Set integer runtime value with re-authenticate if needed"""
        try:
            return self.client.SetRuntimeValueInt(ihcid, value)
        except:
            self.Authenticate()
            return self.client.SetRuntimeValueInt(ihcid, value)

    def GetProject(self) -> str:
        """ Get the ihc project and make sure controller is ready before"""
        with IHCController._mutex:
            if self._project is None:
                if self.client.GetState() != IHCSTATE_READY:
                    if self.client.WaitForControllerStateChange(IHCSTATE_READY, 10) != IHCSTATE_READY:
                        return None
                self._project = self.client.GetProject()
        return self._project

    def AddNotifyEvent(self, resourceid: int, callback):
        """ Add a notify callback for a specified resource id"""
        with IHCController._mutex:
            if resourceid in self._ihcevents:
                self._ihcevents[resourceid].append(callback)
            else:
                self._ihcevents[resourceid] = [callback]
                if not self.client.EnableRuntimeValueNotifications(resourceid):
                    return False
            if not self._notifyrunning:
                self._notifythread.start()

            return True

    def _notify_fn(self):
        """The notify thread function."""
        self._notifyrunning = True
        while self._notifyrunning:
            try:
                changes = self.client.WaitForResourceValueChanges()
                for ihcid in changes:
                    value = changes[ihcid]
                    if ihcid in self._ihcevents:
                        for callback in self._ihcevents[ihcid]:
                            callback(ihcid, value)
            except:
                while not self.Authenticate():
                    #wait 10 seconds before we try to authenticate again
                    time.sleep(10)
                    if not self._notifyrunning:
                        break

import threading
from ihcsdk.ihcclient import IHCSoapClient

class IHCController:

    mutex = threading.Lock()

    def __init__( self,url:str, username:str, password: str):
        
        self.client = IHCSoapClient( url)
        self._username = username
        self._password = password
        self.Events = {}
        self.NotifyThread = threading.Thread( target=self._NotifyThread)
        self.NotifyRunning = False
        self._Project = None

    def Authenticate( self) -> bool:
        with IHCController.mutex:
            if not self.client.Authenticate( self._username,self._password): 
                return False
            for id in self.Events:
                self.client.EnableRuntimeValueNotifications( id)
            return True

    def Disconnect( self):
        self.NotifyRunning = False

    def GetRuntimeValue( self,id: int):
        try:
            return self.client.GetRuntimeValue( id)
        except:
            self.Authenticate()
            return self.client.GetRuntimeValue( id)

    def SetRuntimeValueBool( self,id: int, value:bool) -> bool:
        try:
            return self.client.SetRuntimeValueBool( id,value)
        except:
            self.Authenticate()
            return self.client.SetRuntimeValueBool( id,value)

    def SetRuntimeValueInt ( self,id: int, value:int) -> bool:
        try:
            return self.client.SetRuntimeValueInt( id,value)
        except:
            self.Authenticate()
            return self.client.SetRuntimeValueInt( id,value)

    def GetProject( self) -> str:
        with IHCController.mutex:
          if self._Project == None:
              self._Project = self.client.GetProject()
        return self._Project

    def AddNotifyEvent( self,resourceid : int,callback):
        with IHCController.mutex:
            if resourceid in self.Events:
                self.Events[ resourceid].append( callback)
            else:
                self.Events[ resourceid] = [ callback]
                if not self.client.EnableRuntimeValueNotifications( resourceid):
                   return False;
            if not self.NotifyRunning:
                self.NotifyThread.start()

            return True

    def _NotifyThread( self):
        self.NotifyRunning = True
        while self.NotifyRunning:
            try:
                changes = self.client.WaitForResourceValueChanges()
                for id in changes:
                    value = changes[id]
                    if id in self.Events:
                        for fn in self.Events[ id]:
                            fn( id,value)
            except:
                time.sleep( 10)
                self.Authenticate();


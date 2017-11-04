"""
Implements the connection to the ihc controller
"""
# pylint: disable=invalid-name, bare-except
import xml.etree.ElementTree
import zlib
import base64
import requests

IHCSTATE_READY = "text.ctrl.state.ready"

class IHCSoapClient:
    """Implements a limited set of the soap request for the IHC controller"""
    ns = {'SOAP-ENV':"http://schemas.xmlsoap.org/soap/envelope/",
          'ns1':'utcs',
          'ns2':'utcs.values',
          'ns3':'utcs.values'}

    def __init__(self, url: str):
        """Initialize the IIHCSoapClient with a url for the controller"""
        self.url = url
        self.username = ""
        self.password = ""
        self.cookies = None

    def Authenticate(self, username: str, password: str) -> bool:
        """Do an Authentricate request and save the cookie returned to be used
        on the following requests. Return True if the request was successfull"""
        self.username = username
        self.password = password

        auth_payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>
        <authenticate1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
        <password>{password}</password>
        <username>{username}</username>
        <application>treeview</application>
        </authenticate1>
        </s:Body>
        </s:Envelope>"""

        payload = auth_payload.format(password=self.password,
                                      username=self.username).encode('utf-8')

        headers = {"Host": self.url,
                   "Content-Type": "application/soap+xml; charset=UTF-8",
                   "Content-Length": str(len(payload)),
                   "SOAPAction": "authenticate"}

        response = requests.post(url=self.url + "/ws/AuthenticationService",
                                 headers=headers, data=payload)
        if response.status_code != 200:
            return False
        self.cookies = response.cookies
        try:
            xdoc = xml.etree.ElementTree.fromstring(response.text)
        except xml.etree.ElementTree.ParseError:
            return False
        isok = xdoc.find(r'./SOAP-ENV:Body/ns1:authenticate2/ns1:loginWasSuccessful',
                         IHCSoapClient.ns)
        return isok.text == 'true'

    def GetState(self) -> str:
        """Get the controller state"""
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>
        </s:Body>
        </s:Envelope>"""
        response = self._DoSoapAction("/ws/ControllerService", "getState", payload)
        if response.status_code != 200:
            return "error"
        self.cookies = response.cookies
        try:
            xdoc = xml.etree.ElementTree.fromstring(response.text)
        except xml.etree.ElementTree.ParseError:
            return "error"
        node = xdoc.find(r'./SOAP-ENV:Body/ns1:getState1/ns1:state', IHCSoapClient.ns)
        return node.text

    def WaitForControllerStateChange(self, state: str, waitsec) -> str:
        """Wait for controller state change and return state"""
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>
          <ns1:waitForControllerStateChange1 xmlns:ns1=\"utcs\" xsi:type=\"ns1:WSControllerState\">
            <ns1:state xsi:type=\"xsd:string\">{state}</ns1:state>
          </ns1:waitForControllerStateChange1>
          <ns2:waitForControllerStateChange2 xmlns:ns2=\"utcs\" xsi:type=\"xsd:int\">{wait}</ns2:waitForControllerStateChange2>
        </s:Body>
        </s:Envelope>""".format(state=state, wait=waitsec)
        response = self._DoSoapAction("/ws/ControllerService",
                                      "waitForControllerStateChange", payload)
        if response.status_code != 200:
            return "error"
        self.cookies = response.cookies
        try:
            xdoc = xml.etree.ElementTree.fromstring(response.text)
        except xml.etree.ElementTree.ParseError:
            return "error"
        node = xdoc.find(r'./SOAP-ENV:Body/ns1:waitForControllerStateChange3/ns1:state',
                         IHCSoapClient.ns)
        return node.text

    def _DoSoapAction(self, service: str, action: str, payload: str):
        """ Internal function to do the soap request """
        headers = {"Host": self.url,
                   "Content-Type": "text/xml; charset=UTF-8",
                   "Cache-Control": "no-cache",
                   "Content-Length": str(len(payload)),
                   "SOAPAction": action}
        response = requests.post(url=self.url + service, headers=headers,
                                 data=payload, cookies=self.cookies)
        self.cookies = response.cookies
        return response

    def GetProject(self) -> str:
        """Get the ihc project"""
        project_payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
                          <s:Body/></s:Envelope>"""
        payload = project_payload.encode('utf-8')
        response = self._DoSoapAction("/ws/ControllerService", "getIHCProject", payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        base64data = xdoc.find(r'./SOAP-ENV:Body/ns1:getIHCProject1/ns1:data',
                               IHCSoapClient.ns).text
        compresseddata = base64.b64decode(base64data)
        return zlib.decompress(compresseddata, 16+zlib.MAX_WBITS).decode('ISO-8859-1')

    def SetRuntimeValueBool(self, resourceid: int, value: bool) -> bool:
        """Set a boolean runtime value"""
        if value:
            boolvalue = "true"
        else:
            boolvalue = "false"

        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSBooleanValue\" xmlns:a=\"utcs.values\">
            <a:value>{value}</a:value></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format(id=resourceid, value=boolvalue)
        response = self._DoSoapAction("/ws/ResourceInteractionService", "setResourceValue", payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        result = xdoc.find(r'./SOAP-ENV:Body/ns1:setResourceValue2', IHCSoapClient.ns).text
        return result == "true"

    def SetRuntimeValueInt(self, resourceid: int, intvalue: int):
        """Set a integer runtime value"""
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSIntegerValue\" xmlns:a=\"utcs.values\">
            <a:integer>{value}</a:integer></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format(id=resourceid, value=intvalue)
        response = self._DoSoapAction("/ws/ResourceInteractionService", "setResourceValue", payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        result = xdoc.find(r'./SOAP-ENV:Body/ns1:setResourceValue2', IHCSoapClient.ns).text
        return result == "true"

    def SetRuntimeValueFloat(self, resourceid: int, floatvalue: float):
        """Set a flot runtime value"""
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSFloatingPointValue\" xmlns:a=\"utcs.values\">
            <a:floatingPointValue>{value}</a:floatingPointValue></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format(id=resourceid, value=floatvalue)
        response = self._DoSoapAction("/ws/ResourceInteractionService",
                                      "setResourceValue", payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        result = xdoc.find(r'./SOAP-ENV:Body/ns1:setResourceValue2', IHCSoapClient.ns).text
        return result == "true"

    def GetRuntimeValue(self, resourceid: int):
        """Get runtime value of specified resource it
           The returned value will be boolean, integer or float
           Return None if resource cannot be found or on error
        """
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body>
            <getRuntimeValue1 xmlns="utcs">{id}</getRuntimeValue1>
            </soap:Body></soap:Envelope>""".format(id=resourceid)
        response = self._DoSoapAction("/ws/ResourceInteractionService",
                                      "getResourceValue", payload)
        if response.status_code != 200:
            return None
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        boolresult = xdoc.find(r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:value',
                               IHCSoapClient.ns)
        if boolresult != None:
            return boolresult.text == "true"
        intresult = xdoc.find(r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:integer',
                              IHCSoapClient.ns)
        if intresult != None:
            return int(intresult.text)
        floatresult = xdoc.find(
            r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:floatingPointValue',
            IHCSoapClient.ns)
        if floatresult != None:
            return float(floatresult.text)
        return None

    def EnableRuntimeValueNotifications(self, resourceid: int):
        """Enable notification for specified resource id"""
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body>
            <enableRuntimeValueNotifications1 xmlns=\"utcs\" xmlns:a=\"http://www.w3.org/2001/XMLSchema\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <a:arrayItem>{id}</a:arrayItem>
            </enableRuntimeValueNotifications1></s:Body></s:Envelope>""".format(id=resourceid)
        response = self._DoSoapAction("/ws/ResourceInteractionService",
                                      "enableRuntimeValueNotifications",
                                      payload)
        if response.status_code != 200:
            return False
        return True

    def WaitForResourceValueChanges(self, wait: int = 10):
        """
        Long polling for changes and return a dictionary with resource, value for changes
        """
        changes = {}
        payload = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
              xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
              xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
            <s:Body><waitForResourceValueChanges1 xmlns=\"utcs\">{timeout}</waitForResourceValueChanges1>
            </s:Body></s:Envelope>""".format(timeout=wait)
        response = self._DoSoapAction("/ws/ResourceInteractionService",
                                      "waitForResourceValueChanges", payload)
        if response.status_code != 200:
            return changes
        xdoc = xml.etree.ElementTree.fromstring(response.text)
        result = xdoc.findall(r'./SOAP-ENV:Body/ns1:waitForResourceValueChanges2/ns1:arrayItem',
                              IHCSoapClient.ns)
        for item in result:
            ihcid = item.find('ns1:resourceID', IHCSoapClient.ns)
            if ihcid is None:
                continue
            bvalue = item.find(r'./ns1:value/ns2:value', IHCSoapClient.ns)
            if bvalue != None:
                changes[int(ihcid.text)] = bvalue.text == 'true'
                continue
            ivalue = item.find(r'./ns1:value/ns3:integer', IHCSoapClient.ns)
            if ivalue != None:
                changes[int(ihcid.text)] = int(ivalue.text)
            fvalue = item.find(r'./ns1:value/ns2:floatingPointValue', IHCSoapClient.ns)
            if fvalue != None:
                changes[int(ihcid.text)] = float(fvalue.text)
        return changes

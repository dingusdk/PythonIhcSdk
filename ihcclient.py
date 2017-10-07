import requests
import xml.etree.ElementTree
import zlib
import base64
import threading
import time

class IHCSoapClient:
    #Implements a limited set of the soap request for the IHC controller
    ns = { 'SOAP-ENV':"http://schemas.xmlsoap.org/soap/envelope/",
           'ns1':'utcs',
           'ns2':'utcs.values',
           'ns3':'utcs.values'}

    def __init__(self,url : str):
        #Initialize the IIHCSoapClient with a url for the controller
        self.Url = url
        self.Username = ""
        self.Password = ""

    def Authenticate( self,username: str,password: str) -> bool:
        """Do an Authentricate request and save the cookie returned to be used 
        on the following requests. Return True if the request was successfull"""
        self.Username = username
        self.Password = password

        auth_payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
        <s:Body>
        <authenticate1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
        <password>{password}</password>
        <username>{username}</username>
        <application>treeview</application>
        </authenticate1>
        </s:Body>
        </s:Envelope>"""

        payload = auth_payload.format( password=self.Password,username=self.Username).encode( 'utf-8')
    
        headers = {"Host": self.Url,
                "Content-Type": "application/soap+xml; charset=UTF-8",
                "Content-Length": str(len(payload)),
                "SOAPAction": "authenticate"}

        response = requests.post( url=self.Url + "/ws/AuthenticationService",headers=headers,data=payload)
        self.cookies = response.cookies
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        ok = xdoc.find( r'./SOAP-ENV:Body/ns1:authenticate2/ns1:loginWasSuccessful',IHCSoapClient.ns)
        return ok.text == 'true'


    def _DoSoapAction( self,service : str,action : str,payload : str):
        """ Internal function to do the soap request """
        headers = {"Host": self.Url,
                "Content-Type": "application/soap+xml; charset=UTF-8",
                "Content-Length": str(len(payload)),
                "SOAPAction": action}
        response = requests.post( url=self.Url + service,headers=headers,data=payload,cookies=self.cookies)
        self.cookies = response.cookies
        return response

    def GetProject( self) -> str:
        project_payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\"><s:Body/></s:Envelope>"""
        payload = project_payload.encode( 'utf-8')
        response = self._DoSoapAction( "/ws/ControllerService","getIHCProject",payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        base64data = xdoc.find( r'./SOAP-ENV:Body/ns1:getIHCProject1/ns1:data',IHCSoapClient.ns).text
        compresseddata = base64.b64decode( base64data)
        return zlib.decompress( compresseddata,16+zlib.MAX_WBITS).decode( 'ISO-8859-1')

    def SetRuntimeValueBool( self,resourceid : int,value : bool) -> bool:
        if value:
            boolvalue = "true"
        else:
            boolvalue = "false"

        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSBooleanValue\" xmlns:a=\"utcs.values\">
            <a:value>{value}</a:value></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format( id=resourceid,value= boolvalue)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","setResourceValue",payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        result = xdoc.find( r'./SOAP-ENV:Body/ns1:setResourceValue2',IHCSoapClient.ns).text
        return result == "true"

    def SetRuntimeValueInt( self,resourceid : int,intvalue : int):

        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSIntegerValue\" xmlns:a=\"utcs.values\">
            <a:integer>{value}</a:integer></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format( id=resourceid,value= intvalue)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","setResourceValue",payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        result = xdoc.find( r'./SOAP-ENV:Body/ns1:setResourceValue2',IHCSoapClient.ns).text
        return result == "true"

    def SetRuntimeValueFloat( self,resourceid : int,floatvalue: float):
        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body>
            <setResourceValue1 xmlns=\"utcs\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSFloatingPointValue\" xmlns:a=\"utcs.values\">
            <a:floatingPointValue>{value}</a:floatingPointValue></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            </s:Envelope>""".format( id=resourceid,value= floatvalue)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","setResourceValue",payload)
        if response.status_code != 200:
            return False
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        result = xdoc.find( r'./SOAP-ENV:Body/ns1:setResourceValue2',IHCSoapClient.ns).text
        return result == "true"

    def GetRuntimeValue( self,resourceid: int):
        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body>
            <getRuntimeValue1 xmlns="utcs">{id}</getRuntimeValue1>
            </soap:Body></soap:Envelope>""".format( id=resourceid)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","getResourceValue",payload)
        if response.status_code != 200:
            return None
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        boolresult = xdoc.find( r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:value',IHCSoapClient.ns)
        if boolresult != None:
            return boolresult.text == "true"
        intresult = xdoc.find( r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:integer',IHCSoapClient.ns)
        if intresult != None:
            return int( intresult.text)
        floatresult = xdoc.find( r'./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:floatingPointValue',IHCSoapClient.ns)
        if floatresult != None:
            return float( floatresult.text)
        return None
         

    def EnableRuntimeValueNotifications( self,resourceid : int):
        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body>
            <enableRuntimeValueNotifications1 xmlns=\"utcs\" xmlns:a=\"http://www.w3.org/2001/XMLSchema\" xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <a:arrayItem>{id}</a:arrayItem>
            </enableRuntimeValueNotifications1></s:Body></s:Envelope>""".format( id=resourceid)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","enableRuntimeValueNotifications",payload)
        if response.status_code != 200:
            return False
        return True

    def WaitForResourceValueChanges( self,wait : int = 10):
        """
        Long polling for changes and return a dictionary with resource, value for changes
        """
        changes = {}
        payload = """<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <s:Body><waitForResourceValueChanges1 xmlns=\"utcs\">{timeout}</waitForResourceValueChanges1>
            </s:Body></s:Envelope>""".format( timeout=wait)
        response = self._DoSoapAction( "/ws/ResourceInteractionService","waitForResourceValueChanges",payload)
        if response.status_code != 200:
            return changes
        xdoc = xml.etree.ElementTree.fromstring( response.text)
        result = xdoc.findall( r'./SOAP-ENV:Body/ns1:waitForResourceValueChanges2/ns1:arrayItem',IHCSoapClient.ns)
        for item in result:
            id = item.find( 'ns1:resourceID',IHCSoapClient.ns)
            if id == None: continue
            b = item.find( r'./ns1:value/ns2:value',IHCSoapClient.ns)
            if b != None:
                changes[ int(id.text)] = b.text == 'true'
                continue
            i = item.find( r'./ns1:value/ns3:integer',IHCSoapClient.ns)
            if i != None:
                changes[ int(id.text)] = int( i.text)
            f = item.find( r'./ns1:value/ns2:floatingPointValue',IHCSoapClient.ns)
            if f != None:
                changes[ int(id.text)] = float( f.text)
        return changes


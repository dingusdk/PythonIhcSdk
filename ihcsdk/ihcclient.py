"""
Implements the connection to the ihc controller
"""
# pylint: disable=bare-except
import zlib
import base64
from ihcsdk.ihcconnection import IHCConnection

IHCSTATE_READY = "text.ctrl.state.ready"


class IHCSoapClient:
    """Implements a limited set of the soap request for the IHC controller"""

    ihcns = {'SOAP-ENV': "http://schemas.xmlsoap.org/soap/envelope/",
             'ns1': 'utcs',
             'ns2': 'utcs.values',
             'ns3': 'utcs.values'}

    def __init__(self, url: str):
        """Initialize the IIHCSoapClient with a url for the controller"""
        self.url = url
        self.username = ""
        self.password = ""
        self.connection = IHCConnection(url)

    def authenticate(self, username: str, password: str) -> bool:
        """Do an Authentricate request and save the cookie returned to be used
        on the following requests.
        Return True if the request was successfull
        """
        self.username = username
        self.password = password

        auth_payload = """<authenticate1 xmlns=\"utcs\"
                          xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
                          <password>{password}</password>
                          <username>{username}</username>
                          <application>treeview</application>
                          </authenticate1>"""
        payload = auth_payload.format(password=self.password,
                                      username=self.username)

        xdoc = self.connection.soap_action(
            '/ws/AuthenticationService', 'authenticate', payload)
        if xdoc is not False:
            isok = xdoc.find(
                './SOAP-ENV:Body/ns1:authenticate2/ns1:loginWasSuccessful',
                IHCSoapClient.ihcns)
            return isok.text == 'true'
        return False

    def get_state(self) -> str:
        """Get the controller state"""
        xdoc = self.connection.soap_action('/ws/ControllerService',
                                           'getState', "")
        if xdoc is not False:
            return xdoc.find('./SOAP-ENV:Body/ns1:getState1/ns1:state',
                             IHCSoapClient.ihcns).text
        return False

    def wait_for_state_change(self, state: str, waitsec) -> str:
        """Wait for controller state change and return state"""
        payload = """<ns1:waitForControllerStateChange1
                     xmlns:ns1=\"utcs\" xsi:type=\"ns1:WSControllerState\">
                     <ns1:state xsi:type=\"xsd:string\">{state}</ns1:state>
                     </ns1:waitForControllerStateChange1>
                     <ns2:waitForControllerStateChange2
                     xmlns:ns2=\"utcs\" xsi:type=\"xsd:int\">
                     {wait}</ns2:waitForControllerStateChange2>
                     """.format(state=state, wait=waitsec)
        xdoc = self.connection.soap_action('/ws/ControllerService',
                                           'waitForControllerStateChange',
                                           payload)
        if xdoc is not False:
            return xdoc.find(
                './SOAP-ENV:Body/ns1:waitForControllerStateChange3/ns1:state',
                IHCSoapClient.ihcns).text
        return False

    def get_project(self) -> str:
        """Get the ihc project"""
        xdoc = self.connection.soap_action('/ws/ControllerService',
                                           'getIHCProject', "")
        if xdoc is not False:
            base64data = xdoc.find(
                './SOAP-ENV:Body/ns1:getIHCProject1/ns1:data',
                IHCSoapClient.ihcns).text
            if not base64:
                return False
            compresseddata = base64.b64decode(base64data)
            return zlib.decompress(compresseddata,
                                   16+zlib.MAX_WBITS).decode('ISO-8859-1')
        return False

    def set_runtime_value_bool(self, resourceid: int, value: bool) -> bool:
        """Set a boolean runtime value"""
        if value:
            boolvalue = "true"
        else:
            boolvalue = "false"

        payload = """
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSBooleanValue\" xmlns:a=\"utcs.values\">
            <a:value>{value}</a:value></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            """.format(id=resourceid, value=boolvalue)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'setResourceValue', payload)
        if xdoc is not False:
            result = xdoc.find(r'./SOAP-ENV:Body/ns1:setResourceValue2',
                               IHCSoapClient.ihcns).text
            return result == "true"
        return False

    def set_runtime_value_int(self, resourceid: int, intvalue: int):
        """Set a integer runtime value"""
        payload = """
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSIntegerValue\" xmlns:a=\"utcs.values\">
            <a:integer>{value}</a:integer></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            """.format(id=resourceid, value=intvalue)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'setResourceValue', payload)
        if xdoc is not False:
            result = xdoc.find('./SOAP-ENV:Body/ns1:setResourceValue2',
                               IHCSoapClient.ihcns).text
            return result == "true"
        return False

    def set_runtime_value_float(self, resourceid: int, floatvalue: float):
        """Set a flot runtime value"""
        payload = """
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSFloatingPointValue\" xmlns:a=\"utcs.values\">
            <a:floatingPointValue>{value}</a:floatingPointValue></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            """.format(id=resourceid, value=floatvalue)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'setResourceValue', payload)
        if xdoc is not False:
            result = xdoc.find('./SOAP-ENV:Body/ns1:setResourceValue2',
                               IHCSoapClient.ihcns).text
            return result == "true"
        return False

    def get_runtime_value(self, resourceid: int):
        """Get runtime value of specified resource it
           The returned value will be boolean, integer or float
           Return None if resource cannot be found or on error
        """
        payload = """<getRuntimeValue1 xmlns="utcs">{id}</getRuntimeValue1>
                  """.format(id=resourceid)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'getResourceValue',
                                           payload)
        if xdoc is False:
            return False
        boolresult = xdoc.find(
            './SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:value',
            IHCSoapClient.ihcns)
        if boolresult is not None:
            return boolresult.text == "true"
        intresult = xdoc.find(
            './SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value/ns2:integer',
            IHCSoapClient.ihcns)
        if intresult is not None:
            return int(intresult.text)
        floatresult = xdoc.find(
            ('./SOAP-ENV:Body/ns1:getRuntimeValue2/'
             'ns1:value/ns2:floatingPointValue'),
            IHCSoapClient.ihcns)
        if floatresult is not None:
            return float(floatresult.text)
        enumNameResut = xdoc.find(
            ('./SOAP-ENV:Body/ns1:getRuntimeValue2/'
             'ns1:value/ns2:enumName'),
            IHCSoapClient.ihcns)
        if enumNameResut is not None:
            return enumNameResut.text
        return False

    def enable_runtime_notification(self, resourceid: int):
        """Enable notification for specified resource id"""
        return self.enable_runtime_notifications([resourceid])

    def enable_runtime_notifications(self, resourceids):
        """Enable notification for specified resource ids"""
        idsarr = ""
        for ihcid in resourceids:
            idsarr += "<a:arrayItem>{id}</a:arrayItem>".format(id=ihcid)

        payload = """<enableRuntimeValueNotifications1 xmlns=\"utcs\"
                     xmlns:a=\"http://www.w3.org/2001/XMLSchema\"
                     xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
                     {arr}
                     </enableRuntimeValueNotifications1>
                     """.format(arr=idsarr)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'enableRuntimeValueNotifications',
                                           payload)
        return xdoc is not False

    def wait_for_resource_value_changes(self, wait: int=10):
        """
        Long polling for changes and return a dictionary with resource:value
        for changes
        """
        changes = {}
        payload = """<waitForResourceValueChanges1
                     xmlns=\"utcs\">{timeout}</waitForResourceValueChanges1>
                  """.format(timeout=wait)
        xdoc = self.connection.soap_action('/ws/ResourceInteractionService',
                                           'getResourceValue', payload)
        if xdoc is False:
            return False
        result = xdoc.findall(
            './SOAP-ENV:Body/ns1:waitForResourceValueChanges2/ns1:arrayItem',
            IHCSoapClient.ihcns)
        for item in result:
            ihcid = item.find('ns1:resourceID', IHCSoapClient.ihcns)
            if ihcid is None:
                continue
            bvalue = item.find('./ns1:value/ns2:value', IHCSoapClient.ihcns)
            if bvalue is not None:
                changes[int(ihcid.text)] = bvalue.text == 'true'
                continue
            ivalue = item.find('./ns1:value/ns3:integer', IHCSoapClient.ihcns)
            if ivalue is not None:
                changes[int(ihcid.text)] = int(ivalue.text)
            fvalue = item.find('./ns1:value/ns2:floatingPointValue',
                               IHCSoapClient.ihcns)
            if fvalue is not None:
                changes[int(ihcid.text)] = float(fvalue.text)
                continue

            enumName = item.find('./ns1:value/ns2:enumName',
                                 IHCSoapClient.ihcns)
            if enumName is not None:
                changes[int(ihcid.text)] = enumName.text
        return changes

    def get_user_log(self, language='da'):
        """Get the controller state"""
        payload = """<getUserLog1 xmlns="utcs" />
                     <getUserLog2 xmlns="utcs">0</getUserLog2>
                     <getUserLog3 xmlns="utcs">{language}</getUserLog3>
                     """.format(language=language)
        xdoc = self.connection.soap_action('/ws/ConfigurationService',
                                           'getUserLog', payload)
        if xdoc is not False:
            base64data = xdoc.find('./SOAP-ENV:Body/ns1:getUserLog4/ns1:data',
                                   IHCSoapClient.ihcns).text
            if not base64data:
                return False
            return base64.b64decode(base64data).decode('UTF-8')
        return False

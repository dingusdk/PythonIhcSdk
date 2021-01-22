"""
Implements the connection to the ihc controller
"""
# pylint: disable=bare-except
import base64
import datetime
import zlib
from ihcsdk.ihcconnection import IHCConnection
from ihcsdk.ihcsslconnection import IHCSSLConnection

IHCSTATE_READY = "text.ctrl.state.ready"


class IHCSoapClient:
    """Implements a limited set of the soap request for the IHC controller"""

    ihcns = {
        "SOAP-ENV": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns1": "utcs",
        "ns2": "utcs.values",
        "ns3": "utcs.values",
    }

    def __init__(self, url: str):
        """Initialize the IIHCSoapClient with a url for the controller"""
        self.url = url
        self.username = ""
        self.password = ""
        if url.startswith("https://"):
            self.connection = IHCSSLConnection(url)
        else:
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
        payload = auth_payload.format(password=self.password, username=self.username)

        xdoc = self.connection.soap_action(
            "/ws/AuthenticationService", "authenticate", payload
        )
        if xdoc is not False:
            isok = xdoc.find(
                "./SOAP-ENV:Body/ns1:authenticate2/ns1:loginWasSuccessful",
                IHCSoapClient.ihcns,
            )
            return isok.text == "true"
        return False

    def get_state(self) -> str:
        """Get the controller state"""
        xdoc = self.connection.soap_action("/ws/ControllerService", "getState", "")
        if xdoc is not False:
            return xdoc.find(
                "./SOAP-ENV:Body/ns1:getState1/ns1:state", IHCSoapClient.ihcns
            ).text
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
                     """.format(
            state=state, wait=waitsec
        )
        xdoc = self.connection.soap_action(
            "/ws/ControllerService", "waitForControllerStateChange", payload
        )
        if xdoc is not False:
            return xdoc.find(
                "./SOAP-ENV:Body/ns1:waitForControllerStateChange3/ns1:state",
                IHCSoapClient.ihcns,
            ).text
        return False

    def get_project(self) -> str:
        """Get the ihc project"""
        xdoc = self.connection.soap_action("/ws/ControllerService", "getIHCProject", "")
        if xdoc is not False:
            base64data = xdoc.find(
                "./SOAP-ENV:Body/ns1:getIHCProject1/ns1:data", IHCSoapClient.ihcns
            ).text
            if not base64:
                return False
            compresseddata = base64.b64decode(base64data)
            return zlib.decompress(compresseddata, 16 + zlib.MAX_WBITS).decode(
                "ISO-8859-1"
            )
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
            """.format(
            id=resourceid, value=boolvalue
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                r"./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
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
            """.format(
            id=resourceid, value=intvalue
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                "./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
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
            """.format(
            id=resourceid, value=floatvalue
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                "./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
            return result == "true"
        return False

    def set_runtime_value_timer(self, resourceid: int, timer: int):
        """Set a timer runtime value in milliseconds"""
        payload = """
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSTimerValue\" xmlns:a=\"utcs.values\">
            <a:milliseconds>{value}</a:milliseconds></value>
            <typeString/>
            <resourceID>{id}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            """.format(
            id=resourceid, value=timer
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                "./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
            return result == "true"
        return False

    def set_runtime_value_time(
        self, resourceid: int, hours: int, minutes: int, seconds: int
    ):
        """Set a time runtime value in hours:minutes:seconds"""
        payload = f"""
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSTimeValue\" xmlns:a=\"utcs.values\">
            <a:hours>{hours}</a:hours>
            <a:minutes>{minutes}</a:minutes>
            <a:seconds>{seconds}</a:seconds>
            </value>
            <typeString/>
            <resourceID>{resourceid}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            </s:Body>
            """
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                "./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
            return result == "true"
        return False

    def get_time(resource_value):

        hours = int(resource_value.find("./ns2:hours", IHCSoapClient.ihcns).text)
        minutes = int(resource_value.find("./ns2:minutes", IHCSoapClient.ihcns).text)
        seconds = int(resource_value.find("./ns2:seconds", IHCSoapClient.ihcns).text)

        return datetime.time(hours, minutes, seconds)

    def __get_value(resource_value):
        """Get a runtime value from the xml base on the type in the xml"""
        valuetype = resource_value.attrib[
            "{http://www.w3.org/2001/XMLSchema-instance}type"
        ].split(":")[1]
        result = {
            "WSBooleanValue": lambda v: (
                v.find("./ns2:value", IHCSoapClient.ihcns).text == "true"
            ),
            "WSIntegerValue": lambda v: int(
                v.find("./ns2:integer", IHCSoapClient.ihcns).text
            ),
            "WSFloatingPointValue": lambda v: float(
                v.find("./ns2:floatingPointValue", IHCSoapClient.ihcns).text
            ),
            "WSEnumValue": lambda v: v.find("./ns2:enumName", IHCSoapClient.ihcns).text,
            "WSTimerValue": lambda v: int(
                v.find("./ns2:milliseconds", IHCSoapClient.ihcns).text
            ),
            "WSTimeValue": lambda v: IHCSoapClient.get_time(v),
        }[valuetype](resource_value)

        return result

    def get_runtime_value(self, resourceid: int):
        """Get runtime value of specified resource it
        The returned value will be boolean, integer or float
        Return None if resource cannot be found or on error
        """
        payload = """<getRuntimeValue1 xmlns="utcs">{id}</getRuntimeValue1>
                  """.format(
            id=resourceid
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "getResourceValue", payload
        )
        if xdoc is False:
            return None
        value = xdoc.find(
            "./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value", IHCSoapClient.ihcns
        )
        return IHCSoapClient.__get_value(value)

    def get_runtime_values(self, resourceids):
        """Get runtime values of specified resource ids
        Return None if resource cannot be found or on error
        """

        idsarr = ""
        for ihcid in resourceids:
            idsarr += "<arrayItem>{id}</arrayItem>".format(id=ihcid)
        payload = '<getRuntimeValues1 xmlns="utcs">' + idsarr + "</getRuntimeValues1>"
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "getResourceValues", payload
        )
        if xdoc is False:
            return False
        result = xdoc.findall(
            "./SOAP-ENV:Body/ns1:getRuntimeValues2/ns1:arrayItem", IHCSoapClient.ihcns
        )
        changes = {}
        for item in result:
            ihcid = item.find("ns1:resourceID", IHCSoapClient.ihcns)
            if ihcid is None:
                continue
            resourceValue = item.find("./ns1:value", IHCSoapClient.ihcns)
            itemValue = IHCSoapClient.__get_value(resourceValue)
            if itemValue is not None:
                changes[int(ihcid.text)] = itemValue
        return changes

    def cycle_bool_value(self, resourceid: int):
        """Turn a booelan resource On and back Off
        Return None if resource cannot be found or on error
        """
        setBool = (
            "<arrayItem>"
            '<value xsi:type="ns1:WSBooleanValue">'
            "<ns1:value>{value}</ns1:value>"
            "</value>"
            "<typeString></typeString>"
            "<resourceID>{id}</resourceID>"
            "<isValueRuntime>true</isValueRuntime>"
            "</arrayItem>"
        )
        payload = (
            '<setResourceValues1 xmlns="utcs" xmlns:ns1="utcs.values">'
            + setBool.format(value="true", id=resourceid)
            + setBool.format(value="false", id=resourceid)
            + "</setResourceValues1>"
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "SOAPAction: setResourceValues", payload
        )
        if xdoc is False:
            return None
        return True

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
                     """.format(
            arr=idsarr
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "enableRuntimeValueNotifications", payload
        )
        return xdoc is not False

    def wait_for_resource_value_changes(self, wait: int = 10):
        """
        Long polling for changes and return a dictionary with resource:value
        for changes
        """
        changes = {}
        payload = """<waitForResourceValueChanges1
                     xmlns=\"utcs\">{timeout}</waitForResourceValueChanges1>
                  """.format(
            timeout=wait
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "getResourceValue", payload
        )
        if xdoc is False:
            return False
        result = xdoc.findall(
            "./SOAP-ENV:Body/ns1:waitForResourceValueChanges2/ns1:arrayItem",
            IHCSoapClient.ihcns,
        )
        for item in result:
            ihcid = item.find("ns1:resourceID", IHCSoapClient.ihcns)
            if ihcid is None:
                continue

            resource_value = item.find("./ns1:value", IHCSoapClient.ihcns)
            value = IHCSoapClient.__get_value(resource_value)
            if value is not None:
                changes[int(ihcid.text)] = value
        return changes

    def get_user_log(self, language="da"):
        """Get the controller state"""
        payload = """<getUserLog1 xmlns="utcs" />
                     <getUserLog2 xmlns="utcs">0</getUserLog2>
                     <getUserLog3 xmlns="utcs">{language}</getUserLog3>
                     """.format(
            language=language
        )
        xdoc = self.connection.soap_action(
            "/ws/ConfigurationService", "getUserLog", payload
        )
        if xdoc is not False:
            base64data = xdoc.find(
                "./SOAP-ENV:Body/ns1:getUserLog4/ns1:data", IHCSoapClient.ihcns
            ).text
            if not base64data:
                return False
            return base64.b64decode(base64data).decode("UTF-8")
        return False

    def clear_user_log(self):
        """Clear the user log in the controller"""
        xdoc = self.connection.soap_action(
            "/ws/ConfigurationService", "clearUserLog", ""
        )
        return

    def get_system_info(self):
        """Get controller system info"""
        xdoc = self.connection.soap_action(
            "/ws/ConfigurationService", "getSystemInfo", ""
        )
        if xdoc is False:
            return False
        info = {
            "uptime": IHCSoapClient.__extract_sysinfo(xdoc, "uptime"),
            "realtimeclock": IHCSoapClient.__extract_sysinfo(xdoc, "realtimeclock"),
            "serial_number": IHCSoapClient.__extract_sysinfo(xdoc, "serialNumber"),
            "production_date": IHCSoapClient.__extract_sysinfo(xdoc, "productionDate"),
            "brand": IHCSoapClient.__extract_sysinfo(xdoc, "brand"),
            "version": IHCSoapClient.__extract_sysinfo(xdoc, "version"),
            "hw_revision": IHCSoapClient.__extract_sysinfo(xdoc, "hwRevision"),
            "sw_date": IHCSoapClient.__extract_sysinfo(xdoc, "swDate"),
            "dataline_version": IHCSoapClient.__extract_sysinfo(
                xdoc, "datalineVersion"
            ),
            "rf_module_software_version": IHCSoapClient.__extract_sysinfo(
                xdoc, "rfModuleSoftwareVersion"
            ),
            "rf_module_serial_number": IHCSoapClient.__extract_sysinfo(
                xdoc, "rfModuleSerialNumber"
            ),
            "application_is_without_viewer": IHCSoapClient.__extract_sysinfo(
                xdoc, "applicationIsWithoutViewer"
            ),
            "sms_modem_software_version": IHCSoapClient.__extract_sysinfo(
                xdoc, "smsModemSoftwareVersion"
            ),
            "led_dimmer_software_version": IHCSoapClient.__extract_sysinfo(
                xdoc, "ledDimmerSoftwareVersion"
            ),
        }
        return info

    def __extract_sysinfo(xdoc, param) -> str:
        """Internal function to extrach a parameter from system info"""
        element = xdoc.find(
            f"./SOAP-ENV:Body/ns1:getSystemInfo1/ns1:{param}", IHCSoapClient.ihcns
        )
        if element is None:
            return None
        return element.text

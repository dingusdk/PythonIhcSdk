"""Implements the connection to the ihc controller."""

# pylint: disable=bare-except
import base64
import datetime
import io
import xml.etree.ElementTree as ET
import zlib
from typing import Any, ClassVar, Literal

from ihcsdk.ihcconnection import IHCConnection
from ihcsdk.ihcsslconnection import IHCSSLConnection

IHCSTATE_READY = "text.ctrl.state.ready"


class IHCSoapClient:
    """Implements a limited set of the soap request for the IHC controller."""

    ihcns: ClassVar[dict[str, str]] = {
        "SOAP-ENV": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns1": "utcs",
        "ns2": "utcs.values",
        "ns3": "utcs.values",
    }

    def __init__(self, url: str) -> None:
        """Initialize the IIHCSoapClient with a url for the controller."""
        self.url = url
        self.username = ""
        self.password = ""
        if url.startswith("https://"):
            self.connection = IHCSSLConnection(url)
        else:
            self.connection = IHCConnection(url)

    def close(self) -> None:
        """Close the connection."""
        self.connection.close()
        self.connection = None

    def authenticate(self, username: str, password: str) -> bool:
        """
        Do an Authentricate request.

        And save the cookie returned to be used on the following requests.
        Return True if the request was successfull.
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
        """Get the controller state."""
        xdoc = self.connection.soap_action("/ws/ControllerService", "getState", "")
        if xdoc is not False:
            return xdoc.find(
                "./SOAP-ENV:Body/ns1:getState1/ns1:state", IHCSoapClient.ihcns
            ).text
        return False

    def wait_for_state_change(self, state: str, waitsec: int) -> str:
        """Wait for controller state change and return state."""
        payload = f"""<ns1:waitForControllerStateChange1
                     xmlns:ns1=\"utcs\" xsi:type=\"ns1:WSControllerState\">
                     <ns1:state xsi:type=\"xsd:string\">{state}</ns1:state>
                     </ns1:waitForControllerStateChange1>
                     <ns2:waitForControllerStateChange2
                     xmlns:ns2=\"utcs\" xsi:type=\"xsd:int\">
                     {waitsec}</ns2:waitForControllerStateChange2>
                     """
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
        """
        Get the ihc project in single SOAP action.

        You should use the get_project_in_segments to get the project in multiple
        segments. This will stress the IHC controller less.
        """
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

    def get_project_in_segments(self, info: dict[str, Any] | None = None) -> str:
        """
        Get the ihc project per segments.

        Param: info .. reuse existing project info.
        If not provided, the get_project_info() is called internally.
        """
        if info is None:
            info = self.get_project_info()
        if info:
            project_major = info.get("projectMajorRevision", 0)
            project_minor = info.get("projectMinorRevision", 0)
            buffer = io.BytesIO()
            for s in range(self.get_project_number_of_segments()):
                segment = self.get_project_segment(s, project_major, project_minor)
                if segment is False:
                    return False
                buffer.write(segment)
            return zlib.decompress(buffer.getvalue(), 16 + zlib.MAX_WBITS).decode(
                "ISO-8859-1"
            )
        return False

    def get_project_info(self) -> dict[str, Any]:
        """Return dictionary of project info items."""
        xdoc = self.connection.soap_action(
            "/ws/ControllerService", "getProjectInfo", ""
        )
        if xdoc is not False:
            info = {}
            elem = xdoc.find("./SOAP-ENV:Body/ns1:getProjectInfo1", IHCSoapClient.ihcns)
            if elem is not None:
                for e in list(elem):
                    name = e.tag.split("}")[-1]
                    info[name] = IHCSoapClient.__get_value(e)
            return info
        return False

    def get_project_number_of_segments(self) -> int:
        """Return the number of segments needed to fetch the current ihc-project."""
        xdoc = self.connection.soap_action(
            "/ws/ControllerService", "getIHCProjectNumberOfSegments", ""
        )
        if xdoc is not False:
            return int(
                xdoc.find(
                    "./SOAP-ENV:Body/ns1:getIHCProjectNumberOfSegments1",
                    IHCSoapClient.ihcns,
                ).text
            )
        return False

    def get_project_segment(
        self, segment: int, project_major: int, project_minor: int
    ) -> bytes:
        """
        Return a segment of the ihc-project with the given number.

        Returns null if the segment number increases above the number of segments
        available. The segments are offset from 0.
        The project-versions given as parameters are used to indentify the project that
        should be fetched. That is, to make sure that you suddenly don't get segments
        belonging to another project.
        """
        payload = f"""
            <getIHCProjectSegment1 xmlns="utcs">{segment}</getIHCProjectSegment1>
            <getIHCProjectSegment2 xmlns="utcs">{project_major}</getIHCProjectSegment2>
            <getIHCProjectSegment3 xmlns="utcs">{project_minor}</getIHCProjectSegment3>
            """
        xdoc = self.connection.soap_action(
            "/ws/ControllerService", "getIHCProjectSegment", payload
        )
        if xdoc is not False:
            base64data = xdoc.find(
                "./SOAP-ENV:Body/ns1:getIHCProjectSegment4/ns1:data",
                IHCSoapClient.ihcns,
            ).text
            if not base64:
                return False
            return base64.b64decode(base64data)
        return False

    def set_runtime_value_bool(self, resourceid: int, value: bool) -> bool:
        """Set a boolean runtime value."""
        boolvalue = "true" if value else "false"
        payload = f"""
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSBooleanValue\" xmlns:a=\"utcs.values\">
            <a:value>{boolvalue}</a:value></value>
            <typeString/>
            <resourceID>{resourceid}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
            """
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "setResourceValue", payload
        )
        if xdoc is not False:
            result = xdoc.find(
                r"./SOAP-ENV:Body/ns1:setResourceValue2", IHCSoapClient.ihcns
            ).text
            return result == "true"
        return False

    def set_runtime_value_int(self, resourceid: int, intvalue: int) -> bool:
        """Set a integer runtime value."""
        payload = f"""
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSIntegerValue\" xmlns:a=\"utcs.values\">
            <a:integer>{intvalue}</a:integer></value>
            <typeString/>
            <resourceID>{resourceid}</resourceID>
            <isValueRuntime>true</isValueRuntime>
            </setResourceValue1>
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

    def set_runtime_value_float(self, resourceid: int, floatvalue: float) -> bool:
        """Set a flot runtime value."""
        payload = f"""
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSFloatingPointValue\" xmlns:a=\"utcs.values\">
            <a:floatingPointValue>{floatvalue}</a:floatingPointValue></value>
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

    def set_runtime_value_timer(self, resourceid: int, timer: int) -> bool:
        """Set a timer runtime value in milliseconds."""
        payload = f"""
            <setResourceValue1 xmlns=\"utcs\"
            xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
            <value i:type=\"a:WSTimerValue\" xmlns:a=\"utcs.values\">
            <a:milliseconds>{timer}</a:milliseconds></value>
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

    def set_runtime_value_time(
        self, resourceid: int, hours: int, minutes: int, seconds: int
    ) -> bool:
        """Set a time runtime value in hours:minutes:seconds."""
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

    @staticmethod
    def _get_time(resource_value: ET.Element) -> datetime.time:
        hours = int(resource_value.find("./ns2:hours", IHCSoapClient.ihcns).text)
        minutes = int(resource_value.find("./ns2:minutes", IHCSoapClient.ihcns).text)
        seconds = int(resource_value.find("./ns2:seconds", IHCSoapClient.ihcns).text)

        return datetime.time(hours, minutes, seconds)

    @staticmethod
    def _get_datetime(resource_value: ET.Element) -> datetime.datetime:
        year = int(resource_value.find("./ns1:year", IHCSoapClient.ihcns).text)
        month = int(
            resource_value.find("./ns1:monthWithJanuaryAsOne", IHCSoapClient.ihcns).text
        )
        day = int(resource_value.find("./ns1:day", IHCSoapClient.ihcns).text)
        hours = int(resource_value.find("./ns1:hours", IHCSoapClient.ihcns).text)
        minutes = int(resource_value.find("./ns1:minutes", IHCSoapClient.ihcns).text)
        seconds = int(resource_value.find("./ns1:seconds", IHCSoapClient.ihcns).text)
        return datetime.datetime(year, month, day, hours, minutes, seconds)  # noqa: DTZ001

    @staticmethod
    def _get_date(resource_value: ET.Element) -> datetime.datetime:
        year = int(resource_value.find("./ns2:year", IHCSoapClient.ihcns).text)
        if year == 0:
            year = datetime.datetime.today().year  # noqa: DTZ002
        month = int(resource_value.find("./ns2:month", IHCSoapClient.ihcns).text)
        day = int(resource_value.find("./ns2:day", IHCSoapClient.ihcns).text)
        return datetime.datetime(year, month, day)  # noqa: DTZ001

    @staticmethod
    def __get_value(
        resource_value: ET.Element,
    ) -> bool | int | float | str | datetime.datetime | None:
        """Get a runtime value from the xml base on the type in the xml."""
        if resource_value is None:
            return None
        valuetype = resource_value.attrib[
            "{http://www.w3.org/2001/XMLSchema-instance}type"
        ].split(":")[1]
        result = resource_value.text
        match valuetype:
            case "WSBooleanValue":
                result = (
                    resource_value.find("./ns2:value", IHCSoapClient.ihcns).text
                    == "true"
                )
            case "WSIntegerValue":
                result = int(
                    resource_value.find("./ns2:integer", IHCSoapClient.ihcns).text
                )
            case "WSFloatingPointValue":
                result = round(
                    float(
                        resource_value.find(
                            "./ns2:floatingPointValue", IHCSoapClient.ihcns
                        ).text
                    ),
                    2,
                )
            case "WSEnumValue":
                result = resource_value.find("./ns2:enumName", IHCSoapClient.ihcns).text
            case "WSTimerValue":
                return int(
                    resource_value.find("./ns2:milliseconds", IHCSoapClient.ihcns).text
                )
            case "WSTimeValue":
                result = IHCSoapClient._get_time(resource_value)
            case "WSDate":
                result = IHCSoapClient._get_datetime(resource_value)
            case "WSDateValue":
                result = IHCSoapClient._get_date(resource_value)
            case "int":
                result = int(resource_value.text)
        return result

    def get_runtime_value(
        self, resourceid: int
    ) -> bool | int | float | str | datetime.datetime | None:
        """
        Get runtime value of specified resource id.

        The returned value will be boolean, integer or float
        Return None if resource cannot be found or on error
        """
        payload = f"""<getRuntimeValue1 xmlns="utcs">{resourceid}</getRuntimeValue1>
                  """
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "getResourceValue", payload
        )
        if xdoc is False:
            return None
        value = xdoc.find(
            "./SOAP-ENV:Body/ns1:getRuntimeValue2/ns1:value", IHCSoapClient.ihcns
        )
        return IHCSoapClient.__get_value(value)

    def get_runtime_values(
        self, resourceids: list[int]
    ) -> dict[int, Any] | Literal[False]:
        """
        Get runtime values of specified resource ids.

        Return None if resource cannot be found or on error
        """
        idsarr = ""
        for ihcid in resourceids:
            idsarr += f"<arrayItem>{ihcid}</arrayItem>"
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
            resource_value = item.find("./ns1:value", IHCSoapClient.ihcns)
            item_value = IHCSoapClient.__get_value(resource_value)
            if item_value is not None:
                changes[int(ihcid.text)] = item_value
        return changes

    def cycle_bool_value(self, resourceid: int) -> bool | None:
        """
        Turn a booelan resource On and back Off.

        Return None if resource cannot be found or on error
        """
        set_bool = (
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
            + set_bool.format(value="true", id=resourceid)
            + set_bool.format(value="false", id=resourceid)
            + "</setResourceValues1>"
        )
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "SOAPAction: setResourceValues", payload
        )
        if xdoc is False:
            return None
        return True

    def enable_runtime_notification(self, resourceid: int) -> bool:
        """Enable notification for specified resource id."""
        return self.enable_runtime_notifications([resourceid])

    def enable_runtime_notifications(self, resourceids: list[int]) -> bool:
        """Enable notification for specified resource ids."""
        idsarr = ""
        for ihcid in resourceids:
            idsarr += f"<a:arrayItem>{ihcid}</a:arrayItem>"

        payload = f"""<enableRuntimeValueNotifications1 xmlns=\"utcs\"
                     xmlns:a=\"http://www.w3.org/2001/XMLSchema\"
                     xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\">
                     {idsarr}
                     </enableRuntimeValueNotifications1>
                     """
        xdoc = self.connection.soap_action(
            "/ws/ResourceInteractionService", "enableRuntimeValueNotifications", payload
        )
        return xdoc is not False

    def wait_for_resource_value_changes(
        self, wait: int = 10
    ) -> dict[int, str] | Literal[False]:
        """
        Long polling for changes.

        And return a dictionary with resource:value for changes (Only last change)
        """
        change_list = self.wait_for_resource_value_change_list(wait)
        if change_list is False:
            return False
        return dict(change_list)

    def wait_for_resource_value_change_list(
        self, wait: int = 10
    ) -> list[(int, Any)] | Literal[False]:
        """
        Long polling for changes.

        And return a resource id dictionary with a list of all changes since last poll.
        Return a list of tuples with the id,value
        """
        changes = []
        payload = f"""<waitForResourceValueChanges1
                     xmlns=\"utcs\">{wait}</waitForResourceValueChanges1>
                  """
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
                changes.append((int(ihcid.text), value))
        return changes

    def get_user_log(self, language: str = "da") -> str | Literal[False]:
        """Get the controller state."""
        payload = f"""<getUserLog1 xmlns="utcs" />
                     <getUserLog2 xmlns="utcs">0</getUserLog2>
                     <getUserLog3 xmlns="utcs">{language}</getUserLog3>
                     """
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

    def clear_user_log(self) -> None:
        """Clear the user log in the controller."""
        self.connection.soap_action("/ws/ConfigurationService", "clearUserLog", "")

    def get_system_info(self) -> dict[str, str] | bool:
        """Get controller system info."""
        xdoc = self.connection.soap_action(
            "/ws/ConfigurationService", "getSystemInfo", ""
        )
        if xdoc is False:
            return False
        return {
            "uptime": IHCSoapClient._extract_sysinfo(xdoc, "uptime"),
            "realtimeclock": IHCSoapClient._extract_sysinfo(xdoc, "realtimeclock"),
            "serial_number": IHCSoapClient._extract_sysinfo(xdoc, "serialNumber"),
            "production_date": IHCSoapClient._extract_sysinfo(xdoc, "productionDate"),
            "brand": IHCSoapClient._extract_sysinfo(xdoc, "brand"),
            "version": IHCSoapClient._extract_sysinfo(xdoc, "version"),
            "hw_revision": IHCSoapClient._extract_sysinfo(xdoc, "hwRevision"),
            "sw_date": IHCSoapClient._extract_sysinfo(xdoc, "swDate"),
            "dataline_version": IHCSoapClient._extract_sysinfo(xdoc, "datalineVersion"),
            "rf_module_software_version": IHCSoapClient._extract_sysinfo(
                xdoc, "rfModuleSoftwareVersion"
            ),
            "rf_module_serial_number": IHCSoapClient._extract_sysinfo(
                xdoc, "rfModuleSerialNumber"
            ),
            "application_is_without_viewer": IHCSoapClient._extract_sysinfo(
                xdoc, "applicationIsWithoutViewer"
            ),
            "sms_modem_software_version": IHCSoapClient._extract_sysinfo(
                xdoc, "smsModemSoftwareVersion"
            ),
            "led_dimmer_software_version": IHCSoapClient._extract_sysinfo(
                xdoc, "ledDimmerSoftwareVersion"
            ),
        }

    @staticmethod
    def _extract_sysinfo(xdoc: ET.Element, param: str) -> str:
        """Extract a parameter from system info."""
        element = xdoc.find(
            f"./SOAP-ENV:Body/ns1:getSystemInfo1/ns1:{param}", IHCSoapClient.ihcns
        )
        if element is None:
            return None
        return element.text

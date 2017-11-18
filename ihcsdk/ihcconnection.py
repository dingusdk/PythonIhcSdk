"""Implements soap reqeust using the "requests" module"""
# pylint: disable=too-few-public-methods
import xml.etree.ElementTree
import requests

class IHCConnection(object):
    """description of class"""

    soapenvelope = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" 
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>{body}</s:Body></s:Envelope>"""

    def __init__(self, url: str):
        """Initialize the IIHCSoapClient with a url for the controller"""
        self.url = url
        self.cookies = ""
        self.verify = False

    def soap_action(self, service, action, payloadbody):
        """Do a soap request."""
        payload = self.soapenvelope.format(body=payloadbody).encode('utf-8')
        headers = {"Host": self.url,
                   "Content-Type": "text/xml; charset=UTF-8",
                   "Cache-Control": "no-cache",
                   "Content-Length": str(len(payload)),
                   "SOAPAction": action}
        response = requests.post(url=self.url + service, headers=headers,
                                 data=payload, cookies=self.cookies)
        if response.status_code != 200:
            return False
        self.cookies = response.cookies
        try:
            xdoc = xml.etree.ElementTree.fromstring(response.text)
        except xml.etree.ElementTree.ParseError:
            return False
        return xdoc

"""Implements soap reqeust using the "requests" module"""

# pylint: disable=too-few-public-methods
import logging
import requests
import xml.etree.ElementTree

from urllib.parse import urlparse
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

_LOGGER = logging.getLogger(__name__)


class IHCConnection(object):
    """Implements a http connection to the controller"""

    soapenvelope = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\"
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>{body}</s:Body></s:Envelope>"""

    def __init__(self, url: str):
        """Initialize the IHCConnection with a url for the controller"""
        self.url = url
        self.verify = False
        self.last_exception = None
        self.last_response = None
        self.session = requests.Session()
        self.retries = Retry(
            total=3,
            backoff_factor=0.2,
            status_forcelist=[502, 503, 504],
            allowed_methods={"POST"},
        )
        self.session.mount("http://", HTTPAdapter(max_retries=self.retries))

    def cert_verify(self):
        return None

    def soap_action(self, service, action, payloadbody):
        """Do a soap request."""
        payload = self.soapenvelope.format(body=payloadbody).encode("utf-8")
        headers = {
            "Host": urlparse(self.url).netloc,
            "Content-Type": "text/xml; charset=UTF-8",
            "Cache-Control": "no-cache",
            "Content-Length": str(len(payload)),
            "SOAPAction": action,
        }
        try:
            _LOGGER.debug("soap payload %s", payload)
            self.last_exception = None
            response = self.session.post(
                url=self.url + service,
                headers=headers,
                data=payload,
                verify=self.cert_verify(),
            )
            _LOGGER.debug("soap request response status %d", response.status_code)
            if response.status_code != 200:
                self.last_response = response
                return False
            _LOGGER.debug("soap request response %s", response.text)
            xdoc = xml.etree.ElementTree.fromstring(response.text)
            if xdoc is None:
                return False
            return xdoc
        except requests.exceptions.RequestException as exp:
            _LOGGER.error("soap request exception %s", exp)
            self.last_exception = exp
        except xml.etree.ElementTree.ParseError as exp:
            _LOGGER.error("soap request xml parse error %s", exp)
            self.last_exception = exp
            self.last_response = response
        return False

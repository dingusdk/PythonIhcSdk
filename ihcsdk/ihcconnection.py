"""Implements soap reqeust using the "requests" module."""

import logging
import time
import xml.etree.ElementTree as ET
from http import HTTPStatus
from typing import Literal, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

_LOGGER = logging.getLogger(__name__)


class IHCConnection:
    """Implements a http connection to the controller."""

    soapenvelope = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\"
          xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"
          xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
        <s:Body>{body}</s:Body></s:Envelope>"""

    def __init__(self, url: str) -> None:
        """Initialize the IHCConnection with a url for the controller."""
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
        # (connect, read) timeout in seconds for every request. Without it a
        # request can block forever if the network drops mid-request, which
        # leaves the notify thread hanging. The read timeout must be longer
        # than the wait time of the long polls, see soap_action().
        self.timeout: Tuple[float, float] = (10.0, 20.0)
        # default minimum time between calls in seconds (0 will not rate limit)
        self.min_interval: float = 0.0
        self.last_call_time: float = 0
        self.logtiming = False

    def close(self) -> None:
        """Close the connection."""
        self.session.close()
        self.session = None

    def cert_verify(self) -> str | None:
        """Validate the certificate and return the cert file."""
        return None

    def soap_action(
        self,
        service: str,
        action: str,
        payloadbody: str,
        wait: Optional[int] = None,
    ) -> ET.Element | Literal[False]:
        """Do a soap request.

        wait is the time in seconds the controller may hold a long poll
        before answering. It is added to the read timeout so a long poll
        never times out on the client side before it does on the controller.
        """
        timeout = self.timeout
        if wait:
            timeout = (timeout[0], timeout[1] + wait)
        payload = self.soapenvelope.format(body=payloadbody).encode("utf-8")
        headers = {
            "Host": urlparse(self.url).netloc,
            "Content-Type": "text/xml; charset=UTF-8",
            "Cache-Control": "no-cache",
            "Content-Length": str(len(payload)),
            "SOAPAction": action,
        }
        try:
            self.rate_limit()
            _LOGGER.debug("soap payload %s", payload)
            self.last_exception = None
            response = self.session.post(
                url=self.url + service,
                headers=headers,
                data=payload,
                verify=self.cert_verify(),
                timeout=timeout,
            )
            _LOGGER.debug("soap request response status %d", response.status_code)
            if response.status_code != HTTPStatus.OK:
                self.last_response = response
                return False
            _LOGGER.debug("soap request response %s", response.text)
            xdoc = ET.fromstring(response.text)  # noqa: S314
            if xdoc is None:
                return False
        except requests.exceptions.RequestException as exp:
            _LOGGER.exception("soap request exception")
            self.last_exception = exp
        except ET.ParseError as exp:
            _LOGGER.exception("soap request xml parse erro")
            self.last_exception = exp
            self.last_response = response
        else:
            return xdoc
        return False

    def rate_limit(self) -> None:
        """Rate limit the calls to this function."""
        current_time: float = time.time()
        time_since_last_call: float = current_time - self.last_call_time
        if self.logtiming:
            _LOGGER.warning("time since last call %f sec", time_since_last_call)
        # If not enough time has passed, sleep for the remaining time
        if time_since_last_call < self.min_interval:
            sleep_time: float = self.min_interval - time_since_last_call
            _LOGGER.debug("Ratelimiting for %f sec", sleep_time)
            time.sleep(sleep_time)
        # Update the last call time and call the function
        self.last_call_time = time.time()

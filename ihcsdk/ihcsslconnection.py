"""Implements soap reqeust using the "requests" module"""
# pylint: disable=too-few-public-methods
import ssl
import xml.etree.ElementTree
import requests
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter
from ihcsdk.ihcconnection import IHCConnection


class IHCSSLConnection(IHCConnection):
    """description of class"""

    def __init__(self, url: str):
        """Initialize the IIHCSoapClient with a url for the controller"""
        super(IHCSSLConnection, self).__init__(url)
        self.session = requests.Session()
        self.session.mount('https://', TLSv1Adapter())

    def soap_action(self, service, action, payloadbody):
        """Do a soap request"""
        payload = self.soapenvelope.format(body=payloadbody).encode('utf-8')
        headers = {"Host": self.url,
                   "Content-Type": "text/xml; charset=UTF-8",
                   "Cache-Control": "no-cache",
                   "Content-Length": str(len(payload)),
                   "SOAPAction": action}
        try:
            response = self.session.post(
                url=self.url + service, headers=headers, data=payload)
        except Exception as exp:
            return False
        if response.status_code != 200:
            return False
        try:
            xdoc = xml.etree.ElementTree.fromstring(response.text)
            if xdoc is None:
                return False
        except xml.etree.ElementTree.ParseError:
            return False
        return xdoc


class TLSv1Adapter(HTTPAdapter):
    """Force TLSv1"""

    CIPHERS = ('AES256-SHA')

    def init_poolmanager(self, connections, maxsize,
                         block=requests.adapters.DEFAULT_POOLBLOCK,
                         **pool_kwargs):
        """Initialize poolmanager with cipher and Tlsv1"""
        context = create_urllib3_context(ciphers=self.CIPHERS,
                                         ssl_version=ssl.PROTOCOL_TLSv1)
        pool_kwargs['ssl_context'] = context
        return super(TLSv1Adapter, self).init_poolmanager(connections, maxsize,
                                                          block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        """Ensure cipher and Tlsv1"""
        context = create_urllib3_context(ciphers=self.CIPHERS,
                                         ssl_version=ssl.PROTOCOL_TLSv1)
        proxy_kwargs['ssl_context'] = context
        return super(TLSv1Adapter, self).proxy_manager_for(proxy,
                                                           **proxy_kwargs)

"""Implements soap request using the pycurl module"""
# pylint: disable=too-few-public-methods
import xml.etree.ElementTree
from io import BytesIO
from re import match
import pycurl
from ihcsdk.ihcconnection import IHCConnection


class IHCCurlConnection(IHCConnection):
    """description of class"""

    cookies = ""

    @staticmethod
    def _write_header(header: str):
        cookiekmatch = match("^set-cookie: (.*)$", header.decode('utf-8'))
        if cookiekmatch:
            IHCCurlConnection.cookies = cookiekmatch.group(1)

    def soap_action(self, service, action, payloadbody):
        """Do a soap request """
        payload = self.soapenvelope.format(body=payloadbody).encode('utf-8')
        headers = ['SOAPAction: ' + action,
                   'Content-Type: application/soap+xml; charset=UTF-8',
                   'Content-Length: ' + str(len(payload))]

        try:
            curl = pycurl.Curl()
            curl.setopt(pycurl.SSL_CIPHER_LIST, "AES256-SHA")
            curl.setopt(pycurl.SSLVERSION, pycurl.SSLVERSION_TLSv1_0)
    #        self.curl.setopt(pycurl.CAINFO,'ihc.crt')
            curl.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl.setopt(pycurl.SSL_VERIFYHOST, 0)
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.HEADERFUNCTION, IHCCurlConnection._write_header)

            curl.setopt(pycurl.HTTPHEADER, headers)
            inbuffer = BytesIO(payload)
            curl.setopt(pycurl.READDATA, inbuffer)
            buffer = BytesIO()
            curl.setopt(pycurl.WRITEDATA, buffer)
            curl.setopt(pycurl.URL, self.url + service)
            curl.setopt(pycurl.COOKIE, IHCCurlConnection.cookies)
    #        curl.setopt(pycurl.VERBOSE,1)
            curl.perform()
            body = buffer.getvalue().decode('utf-8')
            code = curl.getinfo(pycurl.HTTP_CODE)
            curl.close()
        except Exception as exp:
            return False
        if code != 200:
            return False
        try:
            xdoc = xml.etree.ElementTree.fromstring(body)
            if xdoc is None:
                return False
        except xml.etree.ElementTree.ParseError:
            return False
        return xdoc

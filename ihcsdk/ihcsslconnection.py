"""Implements soap reqeust using the "requests" module"""
# pylint: disable=too-few-public-methods
import os
import requests

from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from requests.adapters import HTTPAdapter

from ihcsdk.ihcconnection import IHCConnection


class IHCSSLConnection(IHCConnection):
    """Implements a https connection to the controller"""

    def __init__(self, url: str):
        """Initialize the IHCSSLConnection with a url for the controller"""
        super(IHCSSLConnection, self).__init__(url)
        self.cert_file = os.path.dirname(__file__) + "/certs/ihc3.crt"
        self.session.mount("https://", CertAdapter(self.get_fingerprint_from_cert()))

    def get_fingerprint_from_cert(self):
        """Get the fingerprint from the certificate"""
        pem = open(self.cert_file, "rb").read()
        cert = load_pem_x509_certificate(pem, default_backend())
        f = cert.fingerprint(hashes.SHA1())
        return "".join("{:02x}".format(x) for x in f)

    def cert_verify(self):
        return self.cert_file


class CertAdapter(requests.adapters.HTTPAdapter):
    """A adapter for a specific certificate"""

    def __init__(self, fingerprint, **kwargs):
        """Constructor. Store the fingerprint for use when creating the poolmanager."""
        self.fingerprint = fingerprint
        super(CertAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        """Create a custom poolmanager"""
        pool_kwargs["assert_fingerprint"] = self.fingerprint
        return super(CertAdapter, self).init_poolmanager(
            connections, maxsize, block, **pool_kwargs
        )

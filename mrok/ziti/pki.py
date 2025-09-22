import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
from cryptography.x509.oid import NameOID

from mrok.ziti.api import ZitiManagementAPI

_ca_certificates = None


async def get_ca_certificates(mgmt_api: ZitiManagementAPI) -> str:
    global _ca_certificates
    if not _ca_certificates:
        cas_pkcs7 = await mgmt_api.fetch_ca_certificates()
        pkcs7_bytes = base64.b64decode(cas_pkcs7)
        pkcs7_certs = load_der_pkcs7_certificates(pkcs7_bytes)
        ca_certificates = []
        for cert in pkcs7_certs:
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            ca_certificates.append(cert_pem.decode("utf-8"))
        _ca_certificates = "\n".join(ca_certificates)
    return _ca_certificates


def generate_key_and_csr(identity_id: str, key_size: int = 4096) -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CH"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SoftwareOne"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Marketplace Platform"),
            x509.NameAttribute(NameOID.COMMON_NAME, identity_id),
        ]
    )
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .sign(private_key, hashes.SHA256())
    )

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

    return key_pem, csr_pem

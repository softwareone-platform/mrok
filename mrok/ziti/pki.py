import base64

from asn1crypto import cms
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from mrok.ziti.api import ZitiManagementAPI

_ca_certificates = None


async def get_ca_certificates(mgmt_api: ZitiManagementAPI) -> str:
    global _ca_certificates
    if not _ca_certificates:
        cas_pkcs7 = await mgmt_api.fetch_ca_certificates()
        pkcs7_bytes = base64.b64decode(cas_pkcs7)

        content_info = cms.ContentInfo.load(pkcs7_bytes)
        certs = content_info["content"]["certificates"]

        ca_certificates = []
        for cert in certs:
            crypt_cert = x509.load_der_x509_certificate(cert.dump())
            pem = crypt_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
            ca_certificates.append(pem)

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

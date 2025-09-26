import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
from pytest_mock import MockerFixture

from mrok.ziti import pki


@pytest.mark.asyncio
async def test_get_ca_certificates(mocker: MockerFixture):
    mocker.patch.object(pki, "_ca_certificates", None)
    mgmt_api = mocker.AsyncMock()
    mgmt_api.fetch_ca_certificates.return_value = (
        "MIIDNAYJKoZIhvcNAQcCoIIDJTCCAyECAQExADALBgkqhkiG9w0BBwGgggMJMIIDBTCCAe2gAwIB\n"
        "AgIUIPs0bOvdiihzrzOM/W5UW2gw+MkwDQYJKoZIhvcNAQELBQAwEjEQMA4GA1UEAwwHVGVzdCBD\n"
        "QTAeFw0yNTA5MjYwOTE0MDBaFw0yNTA5MjcwOTE0MDBaMBIxEDAOBgNVBAMMB1Rlc3QgQ0EwggEi\n"
        "MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDTOPLeCYvA1SqT7t9GqhD0K3/lNl4s0zpdYUxT\n"
        "POHPsR08Vol+87hGLvbKmUAI7+hSU9oBSIDwnuBnpvOoGTH9VYPnN/hxEVEbMmFkKWP+FwZxQn0a\n"
        "Bfb+iqENvwIij8tvq8nmrs3hCWGG1dgIr1ZnR5nWr+GWveCJpHcH0xXaOG2mZscw0VZMaFbc4zan\n"
        "5Us1hHBkYDSDSVwTT4C2GsaxIiwn26IXpjj1bRa1ffr7SdauJ78HNV/DVpCMOG6Kz1K0x6luv0HY\n"
        "OtXQvYkkhy7R5Ir9Li5LIgdaeLYnqKMkZVLO/JcMKTcZAiA7dNL5xSCEIKQmY9asy8n2bBHVks4R\n"
        "AgMBAAGjUzBRMB0GA1UdDgQWBBSznFqdu3fW0gIj9DkR/WYaOYDjFDAfBgNVHSMEGDAWgBSznFqd\n"
        "u3fW0gIj9DkR/WYaOYDjFDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQBATWXe\n"
        "uz+4msC56Vc+rRsR1G7sAATexIm7vy/4Ou2vUmRb5UpsZvrgCRYRC7B1a0o2CwtaC1skgVResa1f\n"
        "Zhrk/b2Pn+Sc27pXxbjE1lA9T0IDUmRvEmPX/uBClOrF29EVeR9BnnBBAi1i2QduL/yLz8rgWMrb\n"
        "pthvNcpms0W9FlggEWm0ee7vhTLpft9eK4iA391IqZVt1N5CWMjk6pwvTc/6tqDUtKtpjgGh0NU4\n"
        "U6ET6dk3bqM4CNuLcj5tyg+bMTuxmViFC0qXRLtAQHSaYEF33aDraf6Uvv0KUywVsxn+4BTPpeuN\n"
        "gUjmhg6bpPvcC8waUDXINblhaDy6Z+gBMQA="
    )
    certs = await pki.get_ca_certificates(mgmt_api)

    assert certs.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_get_ca_certificates_already_fetched(mocker: MockerFixture):
    mocker.patch.object(pki, "_ca_certificates", "-----BEGIN CERTIFICATE-----")
    mgmt_api = mocker.AsyncMock()
    certs = await pki.get_ca_certificates(mgmt_api)
    mgmt_api.fetch_ca_certificates.assert_not_awaited()
    assert certs.startswith("-----BEGIN CERTIFICATE-----")


def test_generate_key_and_csr_subject_and_key_size():
    identity = "test-id"
    key_pem, csr_pem = pki.generate_key_and_csr(identity)

    # parse key
    private_key = serialization.load_pem_private_key(key_pem.encode(), password=None)
    assert private_key.key_size == 4096

    # parse csr
    csr = x509.load_pem_x509_csr(csr_pem.encode())
    subject = csr.subject

    def get(oid):
        return subject.get_attributes_for_oid(oid)[0].value

    assert get(NameOID.COUNTRY_NAME) == "CH"
    assert get(NameOID.ORGANIZATION_NAME) == "SoftwareOne"
    assert get(NameOID.ORGANIZATIONAL_UNIT_NAME) == "Marketplace Platform"
    assert get(NameOID.COMMON_NAME) == identity

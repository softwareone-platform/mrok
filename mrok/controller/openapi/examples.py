EXTENSION_RESPONSE = {
    "id": "5Jm3PpLQ4mdzqXNRszhE0G",
    "name": "ext-1234-5678",
    "extension": {"id": "EXT-1234-5678"},
    "tags": {"account": "ACC-5555-3333", "mrok": "1.0"},
}


INSTANCE_RESPONSE = {
    "id": "h.KUkPOyZ4",
    "name": "ins-1234-5678-0001.ext-1234-5678",
    "extension": {"id": "EXT-1234-5678"},
    "instance": {"id": "INS-1234-5678-0001"},
    "tags": {"account": "ACC-5555-3333", "mrok": "1.0"},
}

INSTANCE_CREATE_RESPONSE = {
    "id": "h.KUkPOyZ4",
    "name": "ins-1234-5678-0001.ext-1234-5678",
    "extension": {"id": "EXT-1234-5678"},
    "instance": {"id": "INS-1234-5678-0001"},
    "identity": {
        "ztAPI": "https://ziti.exts.platform.softwareone.com/edge/client/v1",
        "ztAPIs": None,
        "configTypes": None,
        "id": {
            "key": "pem:-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "cert": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
            "ca": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
        },
        "enableHa": None,
    },
    "tags": {"account": "ACC-5555-3333", "mrok": "1.0"},
}

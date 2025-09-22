[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mrok&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mrok) [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mrok&metric=coverage)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mrok)

# mrok

**mrok** provides the communication channel that allows the Marketplace Platform Extensions to securely expose their web applications to the platform without requiring inbound connectivity.
It uses the [OpenZiti](https://openziti.io) zero-trust network overlay to create encrypted tunnels initiated from the Extension side, enabling operation even behind corporate firewalls.

## Components
- **Controller** – A REST API that simplifies OpenZiti configuration. It lets other platform services create and manage *Extensions* (Ziti services) and *Instances* (Ziti identities).
- **Agent** – Runs alongside an extension in two modes:
  - *Sidecar mode*: proxies traffic between the Ziti network and a local TCP or Unix socket.
  - *Embeddable mode*: integrates with ASGI servers (e.g. Uvicorn) to serve a Python application directly.
- **CLI** – A command-line tool for administrative tasks and for running the agent in either mode.

## Key Features
- Secure, outbound-initiated connectivity for Extension web apps.
- Zero-trust networking with automatic balancing across Extension instances.
- Simple API and CLI for managing services and identities.

## License
[Apache 2.0](LICENSE)

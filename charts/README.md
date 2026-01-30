# mrok Helm Charts

This directory contains Kubernetes Helm charts for deploying the mrok application stack.

## Charts Overview

### 1. mrok-controller

**Description:** Helm chart for deploying the mrok controller component.

**Purpose:** The mrok controller is the central management component that handles orchestration of OpenZiti network.

**Key Configuration Parameters:**
- `image.repository`: Container image repository (e.g., `<registry>/<org>/<image>`)
- `image.tag`: Container image tag (e.g., `<image-tag>`)
- `frontendDomain`: Domain for the frontend service
- `zitiBaseUrlsClient`: Ziti client API endpoint (e.g., `https://<ziti-client-api-host>`)
- `zitiBaseUrlsManagement`: Ziti management API endpoint (e.g., `https://<ziti-mgmt-api-host>`)
- `zitiAuthUsername`: Username for Ziti authentication (default: `admin`)
- `zitiAuthPassword`: Password for Ziti authentication
- `loggingDebug`: Enable debug logging (default: `false`)
- `loggingRich`: Enable rich logging output (default: `false`)
- `controllerAuthBackends`: Authentication backends (default: `['oidc']`)
- `controllerAuthOIDCConfigUrl`: OpenID Connect configuration URL
- `controllerAuthOIDCAudience`: OpenID Connect audience identifier

**Components Deployed:**
- Deployment: Runs the mrok controller service
- ConfigMap: Stores configuration data
- Secret: Stores sensitive credentials
- Service: Exposes the controller application

---

### 2. mrok-frontend

**Description:** Helm chart for deploying the mrok frontend component.

**Purpose:** The mrok frontend is the reverse proxy that allow to consume the extensions web application exposed through the OpenZiti network.

**Key Configuration Parameters:**
- `image.repository`: Container image repository (e.g., `<registry>/<org>/<image>`)
- `image.tag`: Container image tag (e.g., `<image-tag>`)
- `frontendDomain`: Domain for the frontend service
- `loggingDebug`: Enable debug logging (default: `false`)
- `loggingRich`: Enable rich logging output (default: `false`)
- `identityJson`: Identity JSON file for frontend authentication

**Components Deployed:**
- Deployment: Runs the mrok frontend service
- ConfigMap: Stores frontend configuration
- Secret: Stores sensitive data and identity files
- Service: Exposes the frontend application


---

## Common Template Files

Both charts follow a consistent structure with the following template files:

- **`_helpers.tpl`**: Contains reusable template helpers and label definitions
- **`configmap.yaml`**: Kubernetes ConfigMap for storing non-sensitive configuration
- **`deployment.yaml`**: Kubernetes Deployment specification
- **`secret.yaml`**: Kubernetes Secret for storing sensitive data (passwords, API keys, etc.)
- **`service.yaml`**: Kubernetes Service for exposing the application

---

## Installation

### Prerequisites
- Kubernetes cluster (1.19+)
- Helm 3.x

### Install mrok-controller

```bash
helm install mrok-controller ./mrok-controller -f values.yaml
```

### Install mrok-frontend

```bash
helm install mrok-frontend ./mrok-frontend -f values.yaml
```

---

## Configuration

Each chart includes a `values.yaml` file with default and placeholder values. Before deploying:

1. Copy the chart directory to your deployment location
2. Update `values.yaml` with your environment-specific values
3. Use `helm install` or `helm upgrade` to deploy

Example:
```bash
helm upgrade --install mrok-controller ./mrok-controller \
  --set image.repository=myregistry.azurecr.io/mrok \
  --set image.tag=1.0.0 \
  --set frontendDomain=ext.example.com
```

---

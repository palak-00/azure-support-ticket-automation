# Azure App Service Deployment & OIDC Configuration Guide

This document provides step-by-step instructions for deploying the **Azure Support Ticket Automation** container to **Azure App Service (Linux)** using zero-secret **OpenID Connect (OIDC)** authentication with GitHub Actions.

---

## 1. Architectural Overview

```
+--------------------------------------------------------------------------------+
|                                GitHub Actions CI/CD                            |
|                                                                                |
|  1. Request OIDC Token (id-token: write)                                       |
|  2. Exchange GitHub JWT with Microsoft Entra ID                                |
+---------------------------------------+----------------------------------------+
                                        |
                                        v
+--------------------------------------------------------------------------------+
|                             Microsoft Entra ID (Azure AD)                      |
|                                                                                |
|  Validates Federated Credential Subject:                                       |
|  "repo:<github-org>/<github-repo>:environment:production"                      |
|  Issues Short-Lived Access Token (No permanent client secrets stored!)         |
+---------------------------------------+----------------------------------------+
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
+---------------------------------------+ +--------------------------------------+
|       Azure Container Registry (ACR)   | |         Azure App Service            |
|                                       | |       (Linux Web App Container)      |
|  - Authenticate via OIDC              | |  - Pulls image from ACR              |
|  - Build & Push container image       | |  - WEBSITES_PORT = 8000              |
|  - Role: AcrPush                      | |  - Probes /health every 30s          |
+---------------------------------------+ +--------------------------------------+
```

---

## 2. Microsoft Entra ID (Azure AD) OIDC Setup

### Step 1: Create an App Registration
Using the Azure CLI:
```bash
# 1. Create App Registration
APP_NAME="sp-github-support-ticket-deploy"
AZURE_CLIENT_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)

# 2. Create Service Principal
az ad sp create --id "$AZURE_CLIENT_ID"

# 3. Retrieve Tenant & Subscription IDs
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

### Step 2: Configure Federated Identity Credentials for GitHub Actions
Federated credentials establish a cryptographic trust relationship between GitHub's OIDC Identity Provider (`token.actions.githubusercontent.com`) and your Azure App Registration:

```bash
# For Main Branch Deployments:
az ad app federated-credential create \
  --id "$AZURE_CLIENT_ID" \
  --parameters '{
    "name": "gh-actions-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_GITHUB_ORG>/<YOUR_GITHUB_REPO>:ref:refs/heads/main",
    "description": "Deploy to Azure from main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For Environment Deployments (e.g. production):
az ad app federated-credential create \
  --id "$AZURE_CLIENT_ID" \
  --parameters '{
    "name": "gh-actions-production-env",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_GITHUB_ORG>/<YOUR_GITHUB_REPO>:environment:production",
    "description": "Deploy to Azure production environment",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

---

## 3. Azure Role Assignments (Least Privilege)

Grant the service principal required permissions scoped to your Resource Group:

```bash
RESOURCE_GROUP="rg-support-ticket-automation"
APP_SERVICE_NAME="app-support-ticket-prod"
ACR_NAME="acrsupportticketprod"

# Get Service Principal Object ID
SP_OBJECT_ID=$(az ad sp show --id "$AZURE_CLIENT_ID" --query id -o tsv)

# 1. Contributor role on the App Service Web App
az role assignment create \
  --assignee "$SP_OBJECT_ID" \
  --role "Contributor" \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_SERVICE_NAME"

# 2. AcrPush role on Azure Container Registry
az role assignment create \
  --assignee "$SP_OBJECT_ID" \
  --role "AcrPush" \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME"
```

---

## 4. Azure App Service Configuration

Configure the Web App with container runtime settings:

```bash
# 1. Create Linux App Service Plan (B1 basic or higher recommended for custom containers)
az appservice plan create \
  --name "plan-support-tickets" \
  --resource-group "$RESOURCE_GROUP" \
  --is-linux \
  --sku B1

# 2. Create the Web App with an initial placeholder image
az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "plan-support-tickets" \
  --name "$APP_SERVICE_NAME" \
  --deployment-container-image-name "$ACR_NAME.azurecr.io/support-ticket-api:latest"

# 3. Configure App Service Port & Health Check
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --settings \
    WEBSITES_PORT=8000 \
    PORT=8000 \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    DATABASE_URL="sqlite:///./tickets.db"

# 4. Enable Health Probes
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --generic-configurations '{"healthCheckPath": "/health"}'
```

### Critical Azure App Settings Reference:
| Setting Name | Value | Purpose |
|---|---|---|
| `WEBSITES_PORT` | `8000` | Tells Azure front-end load balancer which internal container port to forward traffic to. |
| `PORT` | `8000` | Injected into the container runtime entrypoint (`uvicorn --port ${PORT:-8000}`). |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `false` | Disables SMB volume mounting for faster container boot performance. |
| `healthCheckPath` | `/health` | Configures Azure App Service automatic instance repair probe. |

---

## 5. GitHub Repository Secrets Configuration

Navigate to **GitHub Repository** -> **Settings** -> **Secrets and variables** -> **Actions** and add the following:

### Repository Secrets:
| Secret Name | Example / Description |
|---|---|
| `AZURE_CLIENT_ID` | Application (client) ID of the Entra ID App Registration |
| `AZURE_TENANT_ID` | Directory (tenant) ID of your Azure account |
| `AZURE_SUBSCRIPTION_ID` | Target Azure Subscription ID |
| `AZURE_REGISTRY_SERVER` | `<acrname>.azurecr.io` |
| `AZURE_REGISTRY_NAME` | `<acrname>` |
| `AZURE_APP_NAME` | `app-support-ticket-prod` |
| `AZURE_RESOURCE_GROUP` | `rg-support-ticket-automation` |

> [!IMPORTANT]
> **No Client Secrets or Passwords Committed**:
> Notice that no secret keys or passwords are saved or committed. The workflow securely utilizes GitHub OIDC JWT federation to authenticate with Azure on-demand.

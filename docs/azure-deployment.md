# Azure Deployment Guide

## Prerequisites

- Azure CLI installed (`az --version`)
- Azure subscription
- Docker (for local testing)
- Logged in to Azure (`az login`)

## Quick Deploy

### Option 1: Bash Script (Recommended for first deployment)

```bash
chmod +x deploy-azure.sh
./deploy-azure.sh
```

This creates:
- Resource Group
- Azure Container Registry (ACR)
- Container Apps Environment
- Container App with public ingress

### Option 2: Bicep (Infrastructure as Code)

```bash
# Build image locally first
docker build -t agentic-orchestrator:latest .

# Deploy infrastructure
az deployment group create \
  --resource-group rg-agentic-team \
  --template-file infrastructure/main.bicep \
  --parameters \
    containerImage='acragenticteam.azurecr.io/agentic-orchestrator:latest' \
    azureOpenAIKey='your-key' \
    azureOpenAIEndpoint='https://your-resource.openai.azure.com/'
```

### Option 3: GitHub Actions (CI/CD)

1. Create Azure Service Principal:
   ```bash
   az ad sp create-for-rbac \
     --name "github-agentic-team" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/rg-agentic-team \
     --sdk-auth
   ```

2. Add output JSON to GitHub Secrets as `AZURE_CREDENTIALS`

3. Push to `main` branch → automatic deployment

## Configure Secrets

```bash
chmod +x configure-secrets.sh
# Edit file with your actual keys
./configure-secrets.sh
```

Or manually via Portal:
1. Go to Container App → Settings → Secrets
2. Add secrets: `azure-openai-key`, `azure-openai-endpoint`
3. Update Environment Variables to reference secrets

## Verify Deployment

```bash
# Get app URL
az containerapp show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --query properties.configuration.ingress.fqdn -o tsv

# Test health endpoint
curl https://your-app-url.azurecontainerapps.io/health

# Create an agent
curl -X POST https://your-app-url.azurecontainerapps.io/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "role": "echo",
    "mcp_server": "echo"
  }'
```

## Scaling Configuration

Container Apps auto-scales based on HTTP requests:
- Min replicas: 1
- Max replicas: 5
- Scale trigger: 10 concurrent requests per replica

Adjust in deployment script or via Portal.

## Monitoring

- **Logs:** Container App → Monitoring → Log stream
- **Metrics:** Container App → Monitoring → Metrics
- **Application Insights:** Enable in Container Apps Environment for advanced telemetry

## Cost Estimation

- **Container Apps:** ~$0.000012/vCPU-second + $0.000002/GiB-second
- **Container Registry (Basic):** ~$5/month
- **Estimated monthly cost:** ~$15-30 for low traffic

## Cleanup

```bash
az group delete --name rg-agentic-team --yes --no-wait
```

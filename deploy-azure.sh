#!/bin/bash
set -e

# Configuration
RESOURCE_GROUP="rg-agentic-team"
LOCATION="eastus"
ACR_NAME="acragenticteam"
CONTAINER_APP_ENV="env-agentic-team"
CONTAINER_APP_NAME="app-agentic-orchestrator"
IMAGE_NAME="agentic-orchestrator"
IMAGE_TAG="latest"

echo "=== Azure Container Apps Deployment ==="

# 1. Create Resource Group
echo "Creating resource group..."
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 2. Create Azure Container Registry
echo "Creating container registry..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# 3. Build and push image to ACR
echo "Building and pushing Docker image..."
az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:$IMAGE_TAG \
  --file Dockerfile \
  .

# 4. Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# 5. Create Container Apps Environment
echo "Creating Container Apps environment..."
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# 6. Deploy Container App
echo "Deploying container app..."
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 5

# 7. Get application URL
APP_URL=$(az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "=== Deployment Complete ==="
echo "Application URL: https://$APP_URL"
echo "Health check: https://$APP_URL/health"

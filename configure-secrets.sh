#!/bin/bash
set -e

# Configuration
RESOURCE_GROUP="rg-agentic-team"
CONTAINER_APP_NAME="app-agentic-orchestrator"

echo "=== Adding secrets to Container App ==="

# Add Azure OpenAI secrets
az containerapp secret set \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    azure-openai-key="YOUR_AZURE_OPENAI_KEY" \
    azure-openai-endpoint="YOUR_AZURE_OPENAI_ENDPOINT"

# Update app with environment variables from secrets
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "AZURE_OPENAI_KEY=secretref:azure-openai-key" \
    "AZURE_OPENAI_ENDPOINT=secretref:azure-openai-endpoint"

echo "Secrets configured successfully!"

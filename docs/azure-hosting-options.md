# Azure Hosting - Kompletny Przewodnik dla Aplikacji Python

## Przegląd opcji hostowania na Azure

### 🎯 Porównanie metod

| Metoda | Złożoność | Koszt/m | Skalowalność | Idealny dla |
|--------|-----------|---------|--------------|-------------|
| **Azure Container Apps** | ⭐⭐ | ~$15-30 | ⭐⭐⭐⭐⭐ | **REKOMENDOWANE** - Microservices, API |
| **Azure App Service** | ⭐ | ~$50+ | ⭐⭐⭐⭐ | Proste web apps, mało customizacji |
| **Azure Functions** | ⭐⭐ | ~$0-20 | ⭐⭐⭐ | Event-driven, krótkie zadania |
| **Azure Kubernetes (AKS)** | ⭐⭐⭐⭐⭐ | ~$150+ | ⭐⭐⭐⭐⭐ | Enterprise, duże zespoły |
| **Azure VM** | ⭐⭐⭐ | ~$30+ | ⭐⭐ | Pełna kontrola, legacy apps |

---

## ✅ Opcja 1: Azure Container Apps (REKOMENDOWANE dla Twojego projektu)

### Dlaczego Container Apps?

✅ **Serverless** - płacisz tylko za użycie  
✅ **Auto-scaling** - automatyczne skalowanie 0→N instancji  
✅ **Docker-based** - pełna kontrola nad środowiskiem  
✅ **HTTP/gRPC ingress** - built-in load balancer  
✅ **Secrets management** - Azure Key Vault integration  
✅ **Monitoring** - Application Insights out-of-the-box  

### Quick Start (5 minut)

```bash
# 1. Login
az login

# 2. Ustaw subscription
az account set --subscription "Twoja-Subskrypcja"

# 3. Deploy jednym skryptem
chmod +x deploy-azure.sh
./deploy-azure.sh
```

### Co się dzieje pod spodem?

```bash
#!/bin/bash
# deploy-azure.sh

# 1. Tworzy Resource Group
az group create \
  --name rg-agentic-team \
  --location eastus

# 2. Tworzy Container Registry (miejsce na obrazy Docker)
az acr create \
  --resource-group rg-agentic-team \
  --name acragenticteam \
  --sku Basic

# 3. Buduje i pushuje obraz Dockera
az acr build \
  --registry acragenticteam \
  --image agentic-orchestrator:latest \
  .

# 4. Tworzy Container Apps Environment (infrastruktura)
az containerapp env create \
  --name env-agentic-team \
  --resource-group rg-agentic-team \
  --location eastus

# 5. Deploy aplikacji
az containerapp create \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --environment env-agentic-team \
  --image acragenticteam.azurecr.io/agentic-orchestrator:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 5
```

### Dostęp do aplikacji

Po deploy Azure zwraca URL:
```
Application URL: https://app-agentic-orchestrator.niceocean-12345.eastus.azurecontainerapps.io
```

Test:
```bash
curl https://app-agentic-orchestrator.niceocean-12345.eastus.azurecontainerapps.io/health
```

### Dodanie secretów (Azure OpenAI, Redis, etc.)

```bash
# Dodaj secrets
az containerapp secret set \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --secrets \
    azure-openai-key="sk-..." \
    redis-password="secret123"

# Użyj w env vars
az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --set-env-vars \
    "AZURE_OPENAI_KEY=secretref:azure-openai-key" \
    "REDIS_PASSWORD=secretref:redis-password"
```

### Skalowanie

```bash
# Auto-scale na podstawie ruchu HTTP
az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --min-replicas 1 \
  --max-replicas 10 \
  --scale-rule-name http-scale \
  --scale-rule-type http \
  --scale-rule-http-concurrency 10
```

### Koszty (przykład)

- **0 requestów**: ~$0 (scale to zero)
- **1000 req/dzień**: ~$15/miesiąc
- **10000 req/dzień**: ~$30/miesiąc
- **100k req/dzień**: ~$100/miesiąc

Kalkulacja: [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)

---

## ⚡ Opcja 2: Azure App Service

### Kiedy używać?

- Prosta FastAPI/Flask app bez Dockera
- Chcesz deployment z GitHub bez config
- Mało customizacji środowiska

### Deploy bez Dockera

```bash
# 1. Utwórz App Service Plan
az appservice plan create \
  --name plan-agentic \
  --resource-group rg-agentic-team \
  --sku B1 \
  --is-linux

# 2. Utwórz Web App
az webapp create \
  --name agentic-orchestrator \
  --resource-group rg-agentic-team \
  --plan plan-agentic \
  --runtime "PYTHON|3.12"

# 3. Deploy z GitHub (automatyczny CI/CD)
az webapp deployment source config \
  --name agentic-orchestrator \
  --resource-group rg-agentic-team \
  --repo-url https://github.com/Blu3xray/AgenticTeam \
  --branch main \
  --manual-integration
```

### Startup Command

Azure App Service potrzebuje znać jak uruchomić app:

```bash
# Ustaw startup command
az webapp config set \
  --name agentic-orchestrator \
  --resource-group rg-agentic-team \
  --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000"
```

Dodaj do `requirements.txt`:
```
gunicorn==21.2.0
```

### Environment Variables

```bash
az webapp config appsettings set \
  --name agentic-orchestrator \
  --resource-group rg-agentic-team \
  --settings \
    AZURE_OPENAI_KEY="sk-..." \
    ENVIRONMENT="production"
```

### Wady vs Container Apps

❌ Mniej kontroli nad środowiskiem  
❌ Nie ma scale-to-zero (zawsze płacisz)  
❌ Wolniejszy cold start  
❌ Limit 230s timeout (App Service)  

### Koszty

- **B1 (Basic)**: ~$50/miesiąc (zawsze działa)
- **P1V2 (Production)**: ~$150/miesiąc

---

## 🔥 Opcja 3: Azure Functions (Serverless)

### Kiedy używać?

- Event-driven architecture (webhooks, queue processing)
- Sporadyczny ruch
- Bardzo niskie koszty

### Struktur projektu dla Functions

```
AgenticFunctions/
├── host.json
├── local.settings.json
├── requirements.txt
└── HttpTrigger/
    ├── __init__.py
    └── function.json
```

**HttpTrigger/__init__.py**:
```python
import azure.functions as func
import logging
from app.main import app  # Twoja FastAPI app

async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    """Azure Function wrapper dla FastAPI."""
    logging.info('Python HTTP trigger function processed a request.')
    
    # Proxy request do FastAPI
    # (wymaga adaptera - patrz: asgi-azure-functions)
    
    return func.HttpResponse("Hello from Azure Functions!")
```

### Deploy

```bash
# 1. Zainstaluj Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# 2. Utwórz Function App
az functionapp create \
  --name agentic-functions \
  --resource-group rg-agentic-team \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --storage-account agenticstorage

# 3. Deploy
func azure functionapp publish agentic-functions
```

### Wady dla FastAPI

⚠️ **Nie jest idealny dla long-running API**  
⚠️ Timeout 5-10 minut max  
⚠️ Cold start delay (~5-30s pierwszego requestu)  
⚠️ Wymaga adaptera dla ASGI (FastAPI)  

### Koszty

- **Consumption Plan**: ~$0-10/miesiąc (1M requestów free)
- Idealny dla webhooków, background jobs

---

## 🚀 Opcja 4: Deployment z GitHub Actions (CI/CD)

### Setup once, deploy forever

**1. Utwórz Service Principal**

```bash
az ad sp create-for-rbac \
  --name "github-agentic-deploy" \
  --role contributor \
  --scopes /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/rg-agentic-team \
  --sdk-auth
```

Zapisz output jako GitHub Secret: `AZURE_CREDENTIALS`

**2. GitHub Workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Build and push to ACR
        run: |
          az acr build \
            --registry acragenticteam \
            --image agentic-orchestrator:${{ github.sha }} \
            --image agentic-orchestrator:latest \
            .
      
      - name: Deploy to Container App
        run: |
          az containerapp update \
            --name app-agentic-orchestrator \
            --resource-group rg-agentic-team \
            --image acragenticteam.azurecr.io/agentic-orchestrator:${{ github.sha }}
```

**3. Push → Auto Deploy**

```bash
git add .
git commit -m "Update API"
git push origin main
# 🎉 Automatyczny deployment na Azure!
```

---

## 🏗️ Production Setup (Kompletna infrastruktura)

### Co potrzebujesz w produkcji:

```
┌─────────────────────────────────────────┐
│   Azure Container Apps Environment      │
│                                         │
│  ┌──────────────────┐                  │
│  │ Orchestrator App │ (2-10 replicas)  │
│  │ Port 8000        │                  │
│  └──────────────────┘                  │
│           │                             │
│           ├─→ Azure PostgreSQL          │
│           │   (agent state)             │
│           │                             │
│           ├─→ Azure Cache for Redis     │
│           │   (message bus)             │
│           │                             │
│           └─→ Azure OpenAI              │
│               (LLM)                     │
└─────────────────────────────────────────┘
         │
         ↓
   Application Insights
   (monitoring & logs)
```

### Bicep Infrastructure-as-Code

**infrastructure/main.bicep**:

```bicep
param location string = 'eastus'
param appName string = 'agentic-orchestrator'

// Container Apps Environment
resource env 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'env-${appName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

// PostgreSQL
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: 'pg-${appName}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: 'pgadmin'
    administratorLoginPassword: 'SecureP@ssw0rd!'
    storage: {
      storageSizeGB: 32
    }
  }
}

// Redis Cache
resource redis 'Microsoft.Cache/redis@2023-04-01' = {
  name: 'redis-${appName}'
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0  // 250MB
    }
    enableNonSslPort: false
  }
}

// Container App
resource app 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'app-${appName}'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
      secrets: [
        {
          name: 'postgres-connection'
          value: 'postgresql+asyncpg://pgadmin:SecureP@ssw0rd!@${postgres.properties.fullyQualifiedDomainName}/postgres'
        }
        {
          name: 'redis-connection'
          value: '${redis.properties.hostName}:6380,password=${redis.listKeys().primaryKey},ssl=True'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'orchestrator'
          image: 'acragenticteam.azurecr.io/agentic-orchestrator:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'postgres-connection'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-connection'
            }
            {
              name: 'MESSAGE_BUS_TYPE'
              value: 'redis'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output appUrl string = app.properties.configuration.ingress.fqdn
```

**Deploy całości:**

```bash
az deployment group create \
  --resource-group rg-agentic-team \
  --template-file infrastructure/main.bicep \
  --parameters appName=agentic-orchestrator
```

---

## 📊 Monitoring & Debugging

### Application Insights

```bash
# Enable Application Insights
az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --enable-app-insights
```

### Live Logs

```bash
# Stream logs z Azure
az containerapp logs show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --follow

# Logs z konkretnego czasu
az containerapp logs show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --since 1h
```

### Metrics

```bash
# CPU/Memory usage
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/rg-agentic-team/providers/Microsoft.App/containerApps/app-agentic-orchestrator \
  --metric "CpuUsage,MemoryUsage"
```

### Portal Azure

1. Otwórz [portal.azure.com](https://portal.azure.com)
2. Resource Groups → rg-agentic-team
3. app-agentic-orchestrator
4. Monitoring → Metrics / Logs / Alerts

---

## 💰 Koszty - Realistyczne przykłady

### Startup (małe MVP)

```
Container Apps (1 replica, 0.5 vCPU):  $15/m
PostgreSQL Basic (B1ms):              $12/m
Redis Basic (250MB):                  $16/m
Azure OpenAI (GPT-4, 100k tokens):    $3/m
────────────────────────────────────────────
TOTAL:                                ~$46/m
```

### Skalowanie (średni ruch)

```
Container Apps (2-5 replicas avg):    $50/m
PostgreSQL General Purpose (GP_Gen5_2): $85/m
Redis Standard (1GB):                 $75/m
Azure OpenAI (GPT-4, 1M tokens):      $30/m
Application Insights:                 $10/m
────────────────────────────────────────────
TOTAL:                               ~$250/m
```

### Enterprise

```
AKS cluster (3 nodes):               $300/m
PostgreSQL High Availability:        $500/m
Redis Premium (10GB):                $600/m
Azure OpenAI (GPT-4, 10M tokens):    $300/m
Application Insights Premium:         $50/m
────────────────────────────────────────────
TOTAL:                             ~$1750/m
```

---

## 🎯 Rekomendacja dla Twojego projektu

### Faza 1: Development/Testing
**Azure Container Apps** (bez dodatkowych usług)
- Koszt: ~$15-30/m
- Setup: 5 minut
- Skalowanie: Auto

### Faza 2: Production MVP
**Container Apps + PostgreSQL + Redis**
- Koszt: ~$50-100/m
- Full persistence
- Multi-instance ready

### Faza 3: Scale-up
**AKS lub Container Apps Premium**
- Koszt: $300-1000/m
- Enterprise features
- Advanced networking

---

## 🚀 Szybki Start (10 minut do działającej app na Azure)

```bash
# 1. Login
az login

# 2. Deploy
git clone https://github.com/Blu3xray/AgenticTeam.git
cd AgenticTeam
chmod +x deploy-azure.sh
./deploy-azure.sh

# 3. Czekaj ~5 minut

# 4. Test
curl https://twoj-url.azurecontainerapps.io/health

# 5. Gotowe! 🎉
```

## 📚 Dodatkowe zasoby

- [Azure Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)
- [Azure App Service Python](https://learn.microsoft.com/azure/app-service/quickstart-python)
- [FastAPI on Azure](https://learn.microsoft.com/azure/developer/python/tutorial-deploy-python-web-app-azure-container-apps-01)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)

---

**Potrzebujesz pomocy?** Sprawdź:
- `docs/azure-deployment.md` - szczegóły deployment
- `deploy-azure.sh` - gotowy skrypt
- `.github/workflows/deploy.yml` - CI/CD setup

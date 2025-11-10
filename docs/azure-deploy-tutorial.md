# Deploy na Azure - Praktyczny Tutorial Krok po Kroku

Ten przewodnik pokaże Ci dokładnie jak wdrożyć **AgenticTeam** na Azure od zera do działającej aplikacji.

## 🎯 Co otrzymasz

✅ Działająca aplikacja na publicznym URL  
✅ HTTPS automatycznie  
✅ Auto-scaling (1-10 instancji)  
✅ Monitoring i logi  
✅ Sekretne zmienne (Azure OpenAI keys)  

## ⏱️ Czas: ~15 minut

---

## Krok 1: Przygotowanie (5 minut)

### 1.1 Zainstaluj Azure CLI

**Ubuntu/Debian:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**macOS:**
```bash
brew install azure-cli
```

**Windows:**
Pobierz installer: https://aka.ms/installazurecliwindows

### 1.2 Zaloguj się

```bash
az login
```

Otworzy się przeglądarka → zaloguj się swoim kontem Microsoft/Azure.

### 1.3 Sprawdź subskrypcję

```bash
# Zobacz dostępne subskrypcje
az account list --output table

# Ustaw aktywną (jeśli masz >1)
az account set --subscription "Nazwa-Twojej-Subskrypcji"
```

### 1.4 Zarejestruj providery (jednorazowo)

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
```

---

## Krok 2: Deployment Aplikacji (5 minut)

### Opcja A: Automatyczny deploy (REKOMENDOWANE)

```bash
cd /home/blu3xray/AgenticTeam

# Uruchom skrypt deployment
./deploy-azure.sh
```

**Co się dzieje:**
```
[1/6] Creating Resource Group...          ✓ (10s)
[2/6] Creating Container Registry...      ✓ (60s)
[3/6] Building Docker image...            ✓ (120s)
[4/6] Creating Container Apps Env...      ✓ (30s)
[5/6] Deploying application...            ✓ (45s)
[6/6] Configuring ingress...              ✓ (15s)

🎉 Deployment complete!
Application URL: https://app-agentic-orchestrator.niceocean-abc123.eastus.azurecontainerapps.io
```

### Opcja B: Ręczny deploy (dla zrozumienia)

```bash
# 1. Zmienne (dostosuj!)
RG="rg-agentic-team"
LOCATION="eastus"
ACR_NAME="acragenticteam"
APP_NAME="app-agentic-orchestrator"
ENV_NAME="env-agentic-team"

# 2. Resource Group
az group create --name $RG --location $LOCATION

# 3. Container Registry
az acr create \
  --resource-group $RG \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# 4. Build & Push obrazu
az acr build \
  --registry $ACR_NAME \
  --image agentic-orchestrator:latest \
  --file Dockerfile \
  .

# 5. Container Apps Environment
az containerapp env create \
  --name $ENV_NAME \
  --resource-group $RG \
  --location $LOCATION

# 6. Deploy aplikacji
ACR_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USER=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASS=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --environment $ENV_NAME \
  --image "${ACR_SERVER}/agentic-orchestrator:latest" \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USER \
  --registry-password $ACR_PASS \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 5

# 7. Pobierz URL
APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "✅ App URL: https://$APP_URL"
```

---

## Krok 3: Weryfikacja (2 minuty)

### 3.1 Test Health Endpoint

```bash
# Podstawowy health check
curl https://TWÓJ-URL.azurecontainerapps.io/health

# Powinno zwrócić:
{"status":"ok"}
```

### 3.2 Test API Docs

Otwórz w przeglądarce:
```
https://TWÓJ-URL.azurecontainerapps.io/docs
```

Zobaczysz interaktywną dokumentację Swagger UI! 🎉

### 3.3 Test Chat Endpoint

```bash
curl -X POST https://TWÓJ-URL.azurecontainerapps.io/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new echo agent",
    "session_id": "test-session"
  }'
```

**Odpowiedź:**
```json
{
  "response": "Created echo agent: abc-123...",
  "action": "create_agent",
  "details": {
    "agent_id": "abc-123...",
    "name": "agent-1",
    "role": "echo"
  },
  "session_id": "test-session"
}
```

---

## Krok 4: Konfiguracja Secrets (3 minuty)

### 4.1 Dodaj Azure OpenAI Keys

```bash
RG="rg-agentic-team"
APP_NAME="app-agentic-orchestrator"

# Dodaj secret
az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RG \
  --secrets \
    azure-openai-key="TWÓJ-AZURE-OPENAI-KEY" \
    azure-openai-endpoint="https://twoj-resource.openai.azure.com/"

# Użyj w environment variables
az containerapp update \
  --name $APP_NAME \
  --resource-group $RG \
  --set-env-vars \
    "AZURE_OPENAI_KEY=secretref:azure-openai-key" \
    "AZURE_OPENAI_ENDPOINT=secretref:azure-openai-endpoint" \
    "AZURE_OPENAI_DEPLOYMENT=gpt-4"
```

### 4.2 Restart aplikacji

```bash
az containerapp revision copy \
  --name $APP_NAME \
  --resource-group $RG
```

### 4.3 Test z prawdziwym LLM

```bash
curl -X POST https://TWÓJ-URL.azurecontainerapps.io/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create an LLM agent and ask it to explain what orchestrators do",
    "session_id": "production-test"
  }'
```

Teraz powinnaś dostać prawdziwą odpowiedź z GPT-4! 🚀

---

## Krok 5: Monitoring & Logi

### 5.1 Live Logs (w terminalu)

```bash
az containerapp logs show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --follow
```

**Output:**
```
2025-11-10T14:32:01Z [App] Starting up...
2025-11-10T14:32:02Z [App] Startup complete
2025-11-10T14:32:15Z INFO: 127.0.0.1 - "POST /chat HTTP/1.1" 200 OK
```

### 5.2 Azure Portal (GUI)

1. Otwórz https://portal.azure.com
2. Znajdź **Resource Groups** → **rg-agentic-team**
3. Kliknij **app-agentic-orchestrator**
4. Menu po lewej:
   - **Monitoring** → **Metrics** - wykresy CPU/RAM
   - **Monitoring** → **Logs** - wyszukiwanie logów
   - **Revisions and replicas** - aktywne instancje

### 5.3 Enable Application Insights (opcjonalne)

```bash
az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --enable-app-insights
```

Daje Ci:
- 📊 Performance metrics
- 🔍 Distributed tracing
- 🐛 Exception tracking
- 📈 Custom dashboards

---

## Krok 6: CI/CD z GitHub (opcjonalne, ale mega wygodne)

### 6.1 Utwórz Service Principal

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az ad sp create-for-rbac \
  --name "github-agentic-deploy" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-agentic-team \
  --sdk-auth
```

**Skopiuj cały JSON output!**

### 6.2 Dodaj GitHub Secret

1. Idź do https://github.com/Blu3xray/AgenticTeam
2. Settings → Secrets and variables → Actions
3. New repository secret:
   - Name: `AZURE_CREDENTIALS`
   - Value: **wklej JSON z poprzedniego kroku**

### 6.3 Sprawdź workflow

Workflow już istnieje w `.github/workflows/deploy.yml`!

### 6.4 Przetestuj

```bash
# Zróbmy jakąś zmianę
echo "# Auto-deploy test" >> README.md
git add README.md
git commit -m "Test auto-deployment"
git push origin main
```

**Sprawdź:**
1. GitHub → Actions tab
2. Zobaczysz "Deploy to Azure Container Apps" running
3. Po ~5 minutach - automatyczny deployment! 🎉

Od teraz każdy `git push` automatycznie wdraża na Azure!

---

## Troubleshooting

### Problem: "RegistrationStatus 'Registered' not found"

```bash
# Poczekaj 2-3 minuty po registracji providerów
az provider show --namespace Microsoft.App --query registrationState
```

### Problem: "Container app creation failed"

```bash
# Sprawdź logi deployment
az deployment group list \
  --resource-group rg-agentic-team \
  --query "[0].properties.error"

# Często pomaga usunięcie i ponowne utworzenie
az containerapp delete --name app-agentic-orchestrator --resource-group rg-agentic-team --yes
# Potem deploy ponownie
```

### Problem: "404 Not Found" na URL

```bash
# Sprawdź status aplikacji
az containerapp show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --query "properties.provisioningState"

# Poczekaj aż będzie "Succeeded"
```

### Problem: Aplikacja nie startuje

```bash
# Zobacz logi z błędami
az containerapp logs show \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --tail 100

# Często to brak dependencies - sprawdź Dockerfile
```

### Problem: "No healthy revision available"

```bash
# Sprawdź health probe
az containerapp revision list \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --query "[].{Name:name, Active:properties.active, Health:properties.healthState}"

# Fix: Upewnij się że /health endpoint działa
curl http://localhost:8000/health  # Test lokalnie
```

---

## Czyszczenie (gdy skończysz testowanie)

### Usuń wszystko

```bash
# Usuwa cały Resource Group i wszystkie zasoby
az group delete --name rg-agentic-team --yes --no-wait
```

**Koszty zatrzymane:** od tej chwili nie płacisz już nic! 💸

### Usuń tylko aplikację (zostaw Registry)

```bash
# Tylko Container App
az containerapp delete \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --yes
```

---

## Następne kroki

### 1. Dodaj Database (PostgreSQL)

```bash
# Utwórz PostgreSQL
az postgres flexible-server create \
  --name pg-agentic-team \
  --resource-group rg-agentic-team \
  --location eastus \
  --admin-user pgadmin \
  --admin-password 'SecureP@ssw0rd!' \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32

# Dodaj connection string jako secret
DB_CONNECTION="postgresql+asyncpg://pgadmin:SecureP@ssw0rd!@pg-agentic-team.postgres.database.azure.com/postgres"

az containerapp secret set \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --secrets database-url="$DB_CONNECTION"

az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --set-env-vars "DATABASE_URL=secretref:database-url"
```

### 2. Dodaj Redis

```bash
# Azure Cache for Redis
az redis create \
  --name redis-agentic-team \
  --resource-group rg-agentic-team \
  --location eastus \
  --sku Basic \
  --vm-size c0

# Pobierz connection string
REDIS_KEY=$(az redis list-keys --name redis-agentic-team --resource-group rg-agentic-team --query primaryKey -o tsv)
REDIS_HOST=$(az redis show --name redis-agentic-team --resource-group rg-agentic-team --query hostName -o tsv)
REDIS_CONN="redis://:$REDIS_KEY@$REDIS_HOST:6380?ssl=true"

# Dodaj do app
az containerapp secret set \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --secrets redis-url="$REDIS_CONN"

az containerapp update \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --set-env-vars \
    "REDIS_URL=secretref:redis-url" \
    "MESSAGE_BUS_TYPE=redis"
```

### 3. Custom Domain

```bash
# Dodaj własną domenę
az containerapp hostname add \
  --name app-agentic-orchestrator \
  --resource-group rg-agentic-team \
  --hostname api.twojastrona.com

# Azure poda Ci CNAME do skonfigurowania w DNS
```

---

## Koszty - Realny breakdown

### Minimalna konfiguracja (testing)

```
Container Apps (1 instance, 0.5 vCPU):     $15/m
Container Registry (Basic):                 $5/m
──────────────────────────────────────────────
TOTAL:                                    ~$20/m
```

### Production setup

```
Container Apps (2-5 instances):           $50/m
PostgreSQL (B1ms, 32GB):                  $12/m
Redis Basic (250MB):                      $16/m
Container Registry (Basic):                $5/m
Application Insights:                     $10/m
──────────────────────────────────────────────
TOTAL:                                   ~$93/m
```

### Enterprise

```
Container Apps (5-10 instances):         $150/m
PostgreSQL (GP_Gen5_2, HA):              $170/m
Redis Standard (1GB):                     $75/m
Container Registry (Standard):            $20/m
Application Insights Premium:             $50/m
──────────────────────────────────────────────
TOTAL:                                  ~$465/m
```

**Pro tip:** Włącz [Azure Cost Alerts](https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis) żeby nie mieć niespodzianek!

---

## Podsumowanie

✅ **5 minut:** Podstawowy deployment  
✅ **15 minut:** Full production setup z secrets  
✅ **30 minut:** CI/CD + Database + Redis  

**Twoja aplikacja jest teraz:**
- 🌍 Publicznie dostępna (HTTPS)
- 📈 Auto-scalująca (1-10 replicas)
- 🔒 Bezpieczna (secrets w Azure)
- 📊 Monitorowana (logs + metrics)
- 🚀 Auto-deployowana (GitHub push → Azure)

**Koszty:** ~$20-100/miesiąc w zależności od ruchu

Potrzebujesz pomocy? Sprawdź:
- `docs/azure-hosting-options.md` - wszystkie opcje deployment
- `docs/azure-deployment.md` - szczegóły techniczne
- Azure Portal - wizualne zarządzanie

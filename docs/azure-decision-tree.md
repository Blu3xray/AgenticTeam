# Azure Deployment - Diagram Decyzyjny

## Którą metodę wybrać?

```
                    Chcę wdrożyć aplikację na Azure
                                |
                                v
                    ┌───────────────────────────┐
                    │  Masz doświadczenie z     │
                    │  Kubernetes/Docker?       │
                    └───────────────────────────┘
                           /              \
                      TAK /                \ NIE
                         /                  \
                        v                    v
        ┌──────────────────────┐   ┌──────────────────────┐
        │  Duży projekt?       │   │  Prosta FastAPI app? │
        │  (>10 services)      │   │  Jeden service       │
        └──────────────────────┘   └──────────────────────┘
               /        \                  /        \
          TAK /          \ NIE        TAK /          \ NIE
             /            \               /            \
            v              v             v              v
    ┌──────────┐   ┌──────────────┐  ┌────────────┐  ┌──────────────────┐
    │   AKS    │   │  Container   │  │ App Service│  │ Container Apps   │
    │          │   │     Apps     │  │            │  │                  │
    └──────────┘   └──────────────┘  └────────────┘  └──────────────────┘
         │                │               │                    │
         v                v               v                    v
    $300+/m          $20-100/m        $50+/m              $15-50/m
    Najlepsze        REKOMENDOWANE    Najprostsze         Najlepszy stosunek
    dla enterprise   dla większości   dla prostych apps   cena/możliwości
```

---

## 🎯 Rekomendacje dla konkretnych przypadków

### Twój projekt (AgenticTeam) → **Azure Container Apps**

**Dlaczego?**
- ✅ Moderate complexity (orchestrator + agents)
- ✅ Potrzebujesz Docker dla dependencies
- ✅ Auto-scaling ważne (zmienne obciążenie)
- ✅ Niski koszt na start ($15-30/m)
- ✅ Łatwy setup (5 minut)

**Kiedy zmienić na AKS?**
- Gdy masz >10 różnych services
- Gdy potrzebujesz advanced networking
- Gdy zespół ma doświadczenie z K8s

---

## Szczegółowe drzewo decyzyjne

```
START: Chcę wdrożyć aplikację Python na Azure
│
├─ Pytanie 1: Czy używasz Dockera?
│  │
│  ├─ NIE → App Service (Web Apps for Python)
│  │        • Najprostsze
│  │        • requirements.txt + kod
│  │        • git push = deploy
│  │        • Koszt: $50+/m
│  │        • Setup: 2 minuty
│  │
│  └─ TAK → Pytanie 2: Ile services?
│           │
│           ├─ 1 service → Container Apps
│           │             • Docker-based
│           │             • Auto-scaling
│           │             • Koszt: $15-50/m
│           │             • Setup: 5 minut
│           │
│           ├─ 2-5 services → Container Apps + Docker Compose
│           │                 • Multi-container support
│           │                 • Shared network
│           │                 • Koszt: $50-150/m
│           │                 • Setup: 15 minut
│           │
│           └─ >5 services → Pytanie 3: Budżet?
│                           │
│                           ├─ <$200/m → Container Apps (z revisions)
│                           │            • Managed Kubernetes-like
│                           │            • Mniej kontroli
│                           │
│                           └─ >$200/m → AKS (Azure Kubernetes Service)
│                                        • Pełna kontrola
│                                        • Helm charts
│                                        • DevOps team needed

SPECJALNE PRZYPADKI:

Event-driven (webhooks, queues)?
└─> Azure Functions
    • Pay-per-execution
    • Timeout: 10 min max
    • Koszt: $0-20/m
    • Setup: 10 minut

Background jobs (cron, processing)?
└─> Azure Container Instances + Logic Apps
    • Scheduled runs
    • No always-on costs
    • Koszt: $5-30/m

ML/AI workloads (heavy compute)?
└─> Azure ML Compute lub GPU VMs
    • GPU acceleration
    • Jupyter notebooks
    • Koszt: $100-1000/m
```

---

## Macierz porównawcza

| Feature | Container Apps | App Service | Functions | AKS | VM |
|---------|---------------|-------------|-----------|-----|-----|
| **Setup time** | 5 min | 2 min | 10 min | 60 min | 30 min |
| **Docker required** | Yes | No | No | Yes | Optional |
| **Auto-scaling** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Scale to zero** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Cold start** | 1-5s | 0s | 5-30s | 0s | 0s |
| **Max timeout** | ∞ | ∞ | 10 min | ∞ | ∞ |
| **Min cost/month** | $0 | $50 | $0 | $150 | $30 |
| **Learning curve** | Low | Very Low | Medium | High | Medium |
| **Best for** | Microservices | Simple apps | Events | Enterprise | Legacy |

---

## Przykłady użycia

### 1. Startup MVP (Twój przypadek)

**Scenario:** FastAPI app, 100-1000 users, tight budget

**Wybór:** Container Apps
```bash
Cost: $15-30/month
Scaling: 1-5 replicas
Deployment: ./deploy-azure.sh
CI/CD: GitHub Actions (free)
```

### 2. Production SaaS

**Scenario:** 10k+ users, multiple services, database

**Wybór:** Container Apps + managed services
```bash
Container Apps (API):        $100/m
PostgreSQL (database):        $85/m
Redis Cache:                  $75/m
Application Insights:         $30/m
────────────────────────────────────
TOTAL:                      ~$290/m
```

### 3. Enterprise Application

**Scenario:** 100k+ users, compliance, multi-region

**Wybór:** AKS + Azure DevOps
```bash
AKS Cluster (3 nodes):       $300/m
PostgreSQL HA:               $500/m
Redis Premium:               $600/m
Application Gateway:         $200/m
Azure Monitor:               $100/m
────────────────────────────────────
TOTAL:                     ~$1700/m
```

### 4. Side Project / Hobby

**Scenario:** Personal project, minimal cost

**Wybór:** Functions (Consumption Plan)
```bash
Cost: $0-10/month (1M executions free)
Limitations: 10 min timeout, cold starts
Best for: APIs with <1000 req/day
```

---

## Flow Chart: "Która opcja dla mnie?"

```
┌─────────────────────────────────────────────┐
│ START: Potrzebuję hostować Python app      │
└─────────────────────────────────────────────┘
                    │
                    v
        ┌───────────────────────┐
        │ Budżet miesięczny?    │
        └───────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        v           v           v
    <$30/m     $30-200/m    >$200/m
        │           │           │
        v           v           v
    Functions  Container     AKS
    lub         Apps        lub
    App Service            Dedicated
    (B1)
```

**Decyzja na podstawie metryk:**

```python
def recommend_hosting(monthly_budget, requests_per_day, team_size):
    """
    Rekomendacja Azure hosting.
    
    Args:
        monthly_budget: Budżet w USD
        requests_per_day: Ruch dziennie
        team_size: Liczba developerów
    """
    
    if monthly_budget < 30:
        if requests_per_day < 1000:
            return "Azure Functions (Consumption)"
        else:
            return "App Service B1"
    
    elif monthly_budget < 200:
        if team_size == 1:
            return "Container Apps (Basic)"
        else:
            return "Container Apps + CI/CD"
    
    else:  # >$200/m
        if team_size > 3:
            return "AKS (Kubernetes)"
        else:
            return "Container Apps (Premium)"

# Przykład dla Twojego projektu
recommend = recommend_hosting(
    monthly_budget=50,      # $50/m
    requests_per_day=5000,  # 5k req/day
    team_size=1             # solo developer
)
print(recommend)  # "Container Apps (Basic)"
```

---

## TL;DR - Szybkie odpowiedzi

**Q: Najprostszy deployment?**  
A: App Service z GitHub integration (2 minuty)

**Q: Najtańszy deployment?**  
A: Functions Consumption Plan ($0-10/m)

**Q: Najlepszy stosunek cena/możliwości?**  
A: **Container Apps** ($15-50/m) ← REKOMENDOWANE

**Q: Najbardziej skalowalny?**  
A: AKS ($150+/m) lub Container Apps ($50+/m)

**Q: Dla aplikacji z Dockerem?**  
A: **Container Apps** (łatwe) lub AKS (zaawansowane)

**Q: Bez Dockera, pure Python?**  
A: App Service Web Apps

**Q: Event-driven (webhooks)?**  
A: Azure Functions

**Q: Long-running background jobs?**  
A: Container Instances lub VM

---

## Następne kroki

### 1. Dla AgenticTeam (Twój projekt)

```bash
# Deploy na Container Apps (REKOMENDOWANE)
cd AgenticTeam
./deploy-azure.sh

# Przewodnik krok-po-kroku:
docs/azure-deploy-tutorial.md
```

### 2. Porównanie wszystkich opcji

```bash
# Szczegóły każdej metody:
docs/azure-hosting-options.md
```

### 3. Production setup

```bash
# Database + Redis + CI/CD:
docs/azure-deployment.md
```

---

## Ostateczna rekomendacja dla AgenticTeam

### Faza 1: MVP/Testing (pierwsze 3 miesiące)

**Azure Container Apps (Basic)**
```
Setup: 5 minut
Koszt: ~$20/miesiąc
Features:
  ✅ Auto-scaling (1-5 replicas)
  ✅ HTTPS automatic
  ✅ Logs & monitoring
  ✅ Deployment via script

Command: ./deploy-azure.sh
```

### Faza 2: Production (po walidacji)

**Container Apps + Managed Services**
```
Setup: 30 minut
Koszt: ~$100/miesiąc
Features:
  ✅ PostgreSQL database
  ✅ Redis cache
  ✅ Application Insights
  ✅ GitHub Actions CI/CD
  ✅ Custom domain

Guide: docs/azure-deployment.md
```

### Faza 3: Scale-up (gdy rośniesz)

**Rozważ AKS gdy:**
- >10 różnych services
- >50k users/day
- Compliance requirements (HIPAA, SOC2)
- DevOps team (3+ people)

```
Setup: 2-4 godziny
Koszt: ~$500+/miesiąc
```

---

**Pytania? Sprawdź:**
- [Azure Deploy Tutorial](azure-deploy-tutorial.md) - praktyczny przewodnik
- [Azure Hosting Options](azure-hosting-options.md) - szczegóły techniczne
- [Azure Portal](https://portal.azure.com) - GUI management

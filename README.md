# Nemotron Chat API

_Marcos Filipe Capella_ - <https://marcoscapella.com.br> - LinkedIn: <https://www.linkedin.com/in/capella-marcosfilipe/>

---

Este é um projeto pessoal para interagir com o modelo de linguagem Nemotron da NVIDIA preferencialmente nativamente em GPU local, ou via API oficial da NVIDIA como fallback.

Esta aplicação é pensada como microsserviço para ser integrada em outras aplicações, como chatbots, assistentes virtuais, ou qualquer sistema que se beneficie de capacidades avançadas de processamento de linguagem natural.

**Arquitetura:** Sistema assíncrono baseado em filas (RabbitMQ) com workers dedicados para GPU e API, usando Redis para cache e gerenciamento de jobs.

Aceito contribuições e sugestões para melhorias! Entre em contato comigo via LinkedIn ou e-mail > <marcoscapella@outlook.com>. Estou sempre atento a novas ideias e colaborações.

---

## 🚀 Início Rápido

### 1. Pré-requisitos

- **Python 3.10+**
- **Docker Desktop** (para Redis e RabbitMQ)
- **NVIDIA API Key** (gratuita em <https://build.nvidia.com>)

### 2. Setup em 4 Passos

```powershell
# 1. Clonar e entrar no diretório
cd nemotron-chat-microservice

# 2. Criar ambiente virtual e instalar dependências
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env
# Edite .env e adicione sua NVIDIA_API_KEY

# 4. Iniciar infraestrutura (Redis + RabbitMQ)
docker-compose up -d
```

### 3. Executar a Aplicação (3 terminais)

**Terminal 1 - API:**

```powershell
.venv\Scripts\Activate.ps1
python app/main.py
```

**Terminal 2 - Worker API:**

```powershell
.venv\Scripts\Activate.ps1
python app/run_api_worker.py
```

**Terminal 3 (Opcional) - Worker GPU:**

```powershell
.venv\Scripts\Activate.ps1
python app/run_gpu_worker.py  # Apenas se tiver GPU NVIDIA
```

### 4. Testar

```powershell
# Abrir Swagger UI
start http://localhost:8000/docs

# Ou executar teste automatizado
python test_flow.py
```

---

## 📚 Documentação Completa

- **[Guia de Desenvolvimento e Debug](DEV_GUIDE.md)** - Setup detalhado, debug com VS Code, troubleshooting
- **[Swagger UI](http://localhost:8000/docs)** - Documentação interativa da API
- **[RabbitMQ Management](http://localhost:15672)** - Monitorar filas (user: guest, pass: guest)

---

## 🎯 Arquitetura

```
┌─────────────┐
│   FastAPI   │ ← Recebe requisições HTTP
└──────┬──────┘
       │
       ├─→ POST /chat/auto  → Roteia para GPU ou API
       ├─→ POST /chat/gpu   → Força GPU queue
       └─→ POST /chat/api   → Força API queue
       │
       ↓
┌──────────────────────────────────────┐
│         RabbitMQ Queues              │
│  ┌─────────────┐  ┌─────────────┐   │
│  │  GPU Queue  │  │  API Queue  │   │
│  └──────┬──────┘  └──────┬──────┘   │
└─────────┼─────────────────┼──────────┘
          │                 │
    ┌─────▼──────┐   ┌─────▼──────┐
    │GPU Worker  │   │ API Worker │
    │(Local GPU) │   │(NVIDIA API)│
    └─────┬──────┘   └─────┬──────┘
          │                │
          └────────┬───────┘
                   ↓
            ┌──────────────┐
            │    Redis     │ ← Armazena status dos jobs
            └──────────────┘
```

**Fluxo:**

1. Cliente envia POST para `/chat/auto`, `/chat/gpu` ou `/chat/api`
2. API retorna `job_id` imediatamente (status: PENDING)
3. Mensagem é publicada na fila apropriada (GPU ou API)
4. Worker consome mensagem e processa (status: PROCESSING)
5. Resultado é salvo no Redis (status: COMPLETED ou FAILED)
6. Cliente consulta GET `/chat/status/{job_id}` para obter resultado

---

## Requisitos Mínimos

- Python 3.10+
- 2GB RAM
- API Key da NVIDIA (gratuita em <https://build.nvidia.com>)

### Dica para desenvolvimento/debug

Para depuração mais rápida, prefira ambientes virtuais criados com `python -m venv .venv` ao invés de conda. O venv inicializa mais rápido e consome menos recursos.

## Endpoints disponíveis

- `POST /chat/auto`: Interage com o modelo Nemotron preferencialmente em GPU local, ou via API oficial da NVIDIA como fallback (assíncrono)
- `POST /chat/gpu`: Interage com o modelo Nemotron exclusivamente em GPU local (assíncrono)
- `POST /chat/api`: Interage com o modelo Nemotron exclusivamente via API oficial da NVIDIA (assíncrono)
- `GET /chat/status/{job_id}`: Consulta o status e resultado de um job
- `GET /chat/info`: Fornece informações sobre os modos disponíveis (GPU local e API oficial da NVIDIA)

Swagger UI disponível em `/docs` para testes interativos.

## Formato das requisições

As requisições para os endpoints de chat (`/chat/auto`, `/chat/gpu`, `/chat/api`) devem ser feitas no formato JSON com a seguinte estrutura mínima:

```json
{
  "message": "Sua mensagem aqui"
}
```

Outros campos opcionais podem ser incluídos conforme necessário, como contexto adicional ou parâmetros de configuração. Como no exemplo completo abaixo:

```json
{
  "message": "Olá, como você está?",
  "max_tokens": 256,
  "temperature": 0.7,
  "use_reasoning": true
}
```

### Resposta Assíncrona (imediata)

A API retorna imediatamente com um job_id:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "idempotency_key": "..."
}
```

### Consultar Status do Job

Use o endpoint `/chat/status/{job_id}`:

**Processando:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2026-02-02T10:30:00Z",
  "result": null
}
```

**Completado:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2026-02-02T10:30:00Z",
  "result": {
    "response": "Resposta do modelo aqui",
    "mode": "api",
    "latency_ms": 1250.5
  }
}
```

**Falha:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "created_at": "2026-02-02T10:30:00Z",
  "error": "Descrição do erro"
}
```

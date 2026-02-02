# Nemotron Chat API

_Marcos Filipe Capella_ - <https://marcoscapella.com.br> - LinkedIn: <https://www.linkedin.com/in/capella-marcosfilipe/>

---

Este é um projeto pessoal para interagir com o modelo de linguagem Nemotron da NVIDIA preferencialmente nativamente em GPU local, ou via API oficial da NVIDIA como fallback.

Esta aplicação é pensada como microsserviço para ser integrada em outras aplicações, como chatbots, assistentes virtuais, ou qualquer sistema que se beneficie de capacidades avançadas de processamento de linguagem natural.

**Arquitetura:** Sistema assíncrono baseado em filas (RabbitMQ) com workers dedicados para GPU e API, usando Redis para cache e gerenciamento de jobs.

Aceito contribuições e sugestões para melhorias! Entre em contato comigo via LinkedIn ou e-mail > <marcoscapella@outlook.com>. Estou sempre atento a novas ideias e colaborações.

---

## 🎯 Arquitetura

```text
┌─────────────┐
│   FastAPI   │ ← Recebe requisições HTTP
└──────┬──────┘
       │
       └─→ POST /chat?mode={auto|gpu|api}
           │
           ├─→ mode=auto  → Roteia para GPU ou API
           ├─→ mode=gpu   → Força GPU queue
           └─→ mode=api   → Força API queue
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

1. Cliente envia POST para `/chat?mode={auto|gpu|api}`
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

## Endpoints disponíveis

- `POST /chat?mode={auto|gpu|api}`: Interage com o modelo Nemotron com modo configurável via query parameter (assíncrono)
  - `mode=auto` (default): Roteia para GPU local preferencialmente, ou API da NVIDIA como fallback
  - `mode=gpu`: Força execução exclusiva em GPU local
  - `mode=api`: Força execução exclusiva via API oficial da NVIDIA
- `GET /chat/status/{job_id}`: Consulta o status e resultado de um job
- `GET /chat/info`: Fornece informações sobre os modos disponíveis (GPU local e API oficial da NVIDIA)

Swagger UI disponível em `/docs` para testes interativos.

## Formato das requisições

As requisições para o endpoint de chat (`POST /chat`) devem ser feitas no formato JSON com a seguinte estrutura mínima:

```json
{
  "message": "Sua mensagem aqui"
}
```

Outros campos opcionais podem ser incluídos conforme necessário. Exemplo completo:

```json
{
  "message": "Olá, como você está?",
  "max_tokens": 256,
  "temperature": 0.7,
  "use_reasoning": true,
  "idempotency_key": "uuid-gerado-pelo-cliente"
}
```

**Modo de Execução via Query Parameter:**

```bash
# AUTO (default) - Prefere GPU, fallback para API
POST /chat
POST /chat?mode=auto

# GPU - Força GPU local (retorna 503 se indisponível)
POST /chat?mode=gpu

# API - Força NVIDIA API (sempre disponível, suporta reasoning)
POST /chat?mode=api
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

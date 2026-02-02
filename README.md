# Nemotron Chat API

*Marcos Filipe Capella* - <https://marcoscapella.com.br> - LinkedIn: <https://www.linkedin.com/in/capella-marcosfilipe/>

---

Este é um projeto pessoal para interagir com o modelo de linguagem Nemotron da NVIDIA preferencialmente nativamente em GPU local, ou via API oficial da NVIDIA como fallback.

Esta aplicação é pensada como microsserviço para ser integrada em outras aplicações, como chatbots, assistentes virtuais, ou qualquer sistema que se beneficie de capacidades avançadas de processamento de linguagem natural.

Os endpoints estão disponíveis para uso automático (GPU-first com fallback para API) ou para uso manual em cada modo. Um endpoint adicional fornece informações sobre os modos disponíveis.

Aceito contribuições e sugestões para melhorias! Entre em contato comigo via LinkedIn ou e-mail > <marcoscapella@outlook.com>. Estou sempre atento a novas ideias e colaborações.

---

## Requisitos Mínimos

- Python 3.10+
- 2GB RAM
- API Key da NVIDIA (gratuita em <https://build.nvidia.com>)

### Dica para desenvolvimento/debug

Para depuração mais rápida, prefira ambientes virtuais criados com `python -m venv .venv` ao invés de conda. O venv inicializa mais rápido e consome menos recursos.

## Endpoints disponíveis

- `POST /chat/auto`: Interage com o modelo Nemotron preferencialmente em GPU local, ou via API oficial da NVIDIA como fallback.
- `POST /chat/gpu`: Interage com o modelo Nemotron exclusivamente em GPU local.
- `POST /chat/api`: Interage com o modelo Nemotron exclusivamente via API oficial da NVIDIA.
- `GET /modes`: Fornece informações sobre os modos disponíveis (GPU local e API oficial da NVIDIA).

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
  "use_reasoning": true,
  "stream": false
}
```

A resposta será retornada no formato JSON com a seguinte estrutura:

```json
{
  "response": "Resposta do modelo aqui",
  "mode": "Modo utilizado (gpu ou api)"
}
```

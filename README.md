# FISCO.IA

**Ferramenta Inteligente de Suporte ao Contencioso de Execução Fiscal**

[![CI](https://github.com/AltF4bio/fisco-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/AltF4bio/fisco-ia/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-17-4169E1?logo=postgresql&logoColor=white)
![Cobertura](https://img.shields.io/badge/cobertura-93%25-brightgreen)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

> ### About
> FISCO.IA is an academic prototype (Information Systems capstone, UNIPAR 2026) of a web
> system that helps state attorneys analyze **tax enforcement lawsuits** with **multi-model
> generative AI** (OpenAI, Anthropic and Google Gemini behind a single provider interface).
> Built with **Django 5.2, PostgreSQL, HTMX and Bootstrap**, it features PDF text extraction
> with a quality score, domain scope checking, map-reduce for long documents, an interactive
> clarification mode with structured JSON questions, a consolidated case table fed by
> structured extraction, encrypted API keys, a read-only metadata-only audit log and a
> deterministic mock provider for keyless demos. Compliance with Brazilian AI governance rules
> for the Judiciary (CNJ Resolutions 332/2020 and 615/2025) and data protection law (LGPD) is
> enforced as system behavior: human-in-the-loop, mandatory AI disclaimers, traceability and
> data minimization. 124 automated tests, 93% coverage, CI on GitHub Actions.

> [!IMPORTANT]
> **Protótipo acadêmico — TCC de Sistemas de Informação, UNIPAR 2026.**
> Não é um sistema oficial da Procuradoria-Geral do Estado do Paraná (PGE-PR) nem do Governo
> do Paraná, e não utiliza sua identidade visual. Todos os dados de exemplo (empresas, CNPJs,
> processos, CDAs, valores e protocolos) são **fictícios**.

---

## Sumário

- [Contexto e problema](#contexto-e-problema)
- [Telas](#telas)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Stack](#stack)
- [Como executar](#como-executar)
- [Modo demonstração × chaves reais](#modo-demonstração--chaves-reais)
- [Testes e qualidade](#testes-e-qualidade)
- [Conformidade normativa](#conformidade-normativa)
- [Requisitos do TCC → código](#requisitos-do-tcc--código)
- [Limitações e próximos passos](#limitações-e-próximos-passos)
- [Autor](#autor)

## Contexto e problema

As execuções fiscais concentram parcela expressiva do acervo do Judiciário e da carga de
trabalho das procuradorias estaduais. Cada processo pode reunir centenas de movimentações:
citações, tentativas de penhora, embargos, exceções de pré-executividade, decisões, recursos,
suspensões e apropriações de valores. Para decidir o próximo passo, o procurador precisa
reconstruir esse histórico — tarefa repetitiva, demorada e sujeita a omissões.

Ao mesmo tempo, há um **fosso tecnológico** entre as procuradorias e as ferramentas de IA
generativa disponíveis no mercado, e a adoção dessas ferramentas no setor público exige
cuidados específicos: confidencialidade, rastreabilidade, revisão humana e conformidade com
as resoluções do CNJ e com a LGPD. A PGE-PR vem investindo na modernização tecnológica de sua
atuação, e este trabalho investiga a **viabilidade técnica e jurídica** de uma ferramenta de
apoio nesse contexto.

O FISCO.IA é o produto prático do TCC: um sistema web em que o procurador envia o PDF com as
movimentações do processo e escolhe um **agente** (um prompt especializado vinculado a um
provedor e modelo de IA) para obter resumos cronológicos, sínteses de decisões, rastreamento
de penhoras e apropriações, mapeamento de teses de defesa e diagnóstico da situação
processual — sempre como **apoio**, nunca como decisão.

## Telas

| Login | Painel do procurador |
|---|---|
| ![Login](docs/screenshots/01-login.png) | ![Painel](docs/screenshots/02-painel-procurador.png) |

| Perguntas de esclarecimento (modo interativo) | Resultado da análise |
|---|---|
| ![Perguntas](docs/screenshots/04-perguntas-esclarecimento.png) | ![Resultado](docs/screenshots/05-resultado-analise.png) |

| Alerta de baixa qualidade de extração | Recusa de documento fora do escopo |
|---|---|
| ![Qualidade](docs/screenshots/06-alerta-qualidade.png) | ![Recusa](docs/screenshots/07-recusa-escopo.png) |

**Empresa e tabela consolidada de execuções** (filtros, totais, destaque de ação imediata,
revisão humana e exportação em CSV/PDF):

![Tabela consolidada](docs/screenshots/08-empresa-tabela-consolidada.png)

| Provedores de IA (chaves mascaradas) | Agentes |
|---|---|
| ![Provedores](docs/screenshots/10-provedores.png) | ![Agentes](docs/screenshots/11-agentes.png) |

| Log de auditoria (somente leitura) | Usuários e perfis |
|---|---|
| ![Auditoria](docs/screenshots/14-auditoria.png) | ![Usuários](docs/screenshots/13-usuarios.png) |

As capturas são geradas automaticamente por [`scripts/capturar_telas.py`](scripts/capturar_telas.py),
que percorre o fluxo completo com Playwright e falha se algum passo não funcionar.

## Funcionalidades

**Autenticação e perfis** — login nativo do Django; nenhuma página é acessível sem
autenticação. Perfis independentes: *Administrador* (usuários, provedores, agentes,
auditoria) e *Procurador* (análises, empresas, execuções). Permissões aplicadas nas views e
nos menus.

**Provedores de IA** — chaves de OpenAI, Anthropic e Google cifradas com Fernet e exibidas
apenas mascaradas (`sk-...a1b2`); botão *Testar conexão*; cadastro dos modelos disponíveis
por provedor (nenhum nome de modelo fixado no código); lembrete sobre contratação com vedação
de uso dos dados para treinamento.

**Agentes** — nome, descrição, prompt, provedor/modelo, modo interativo e status. O comando
`seed_agentes` cadastra os cinco agentes do TCC e um agente interno de extração estruturada:

| Agente | Entrega |
|---|---|
| Resumo cronológico | Linha do tempo: movimentação, data e descrição sintética |
| Síntese de decisões | Decisões interlocutórias, sentenças e acórdãos com fundamentos |
| Penhora e apropriação de bens | Bens penhorados e apropriações pelo Estado, com protocolo SEFA |
| Fundamentos jurídicos das partes | Teses de embargos, exceções e recursos |
| Diagnóstico da situação processual | Estado atual do processo em um parágrafo |

Todos os prompts exigem resposta **apenas com base nos autos**, citação de movimentação/folha
e declaração explícita quando a informação **não constar** do documento.

**Análise de autos**
1. Extração do texto (pdfplumber, com pypdf como alternativa), marcando cada folha.
2. **Índice de qualidade** (densidade de texto, caracteres válidos, páginas vazias) com alerta
   abaixo de um limiar configurável.
3. **Verificação de escopo**: heurística por termos (execução fiscal, Lei 6.830/80, CDA,
   Fazenda Pública…) combinada com checagem rápida pelo modelo; documentos de outra natureza
   são recusados.
4. **Modo interativo**: o modelo devolve perguntas estruturadas (JSON validado) sobre lacunas
   — trechos ilegíveis, documentos não juntados, contradições — e as respostas do procurador
   são incorporadas à análise final.
5. **Map-reduce** quando os autos excedem o contexto do modelo: análises parciais por bloco,
   consolidadas ao final (com redução hierárquica).
6. Resultado formatado (Markdown sanitizado), aviso institucional e exportação em **PDF**.

**Empresas e tabela consolidada** — CRUD de empresas com validação de CNPJ (numérico e
**alfanumérico**, IN RFB 2.229/2024). Para cada PDF enviado, o agente interno extrai dados em
JSON validado e faz *upsert* pelo número do processo: CDAs, valor executado, bens penhorados,
apropriações com protocolo SEFA, teses de defesa, situação e data de atualização. A tabela tem
ordenação, filtros (HTMX), totais, destaque de **ação imediata**, revisão manual (campos
revisados prevalecem sobre novas extrações) e exportação em **CSV** e **PDF**.

**Auditoria** — registro de login, análises, perguntas, recusas, exportações e cadastros,
contendo **somente metadados** (usuário, ação, processo, agente, provedor/modelo, data/hora,
resultado). O log é somente-leitura também no nível do modelo de dados.

## Arquitetura

```mermaid
flowchart TB
    subgraph APRESENTACAO["Apresentação"]
        T["Templates Django + Bootstrap 5 + HTMX"]
    end
    subgraph APLICACAO["Aplicação (apps/*/services)"]
        C["contas<br/>autenticação e perfis"]
        P["provedores<br/>configuração"]
        AG["agentes<br/>cadastro e seed"]
        AN["analises<br/>extração · escopo · map-reduce · interativo · PDF"]
        E["empresas<br/>tabela consolidada"]
        AU["auditoria<br/>log somente-leitura"]
    end
    subgraph INTEGRACAO["Integração (apps/provedores/llm)"]
        I["LLMProvider.generate() → LLMResult<br/>get_provider(nome)"]
        O["OpenAIProvider"]
        A["AnthropicProvider"]
        G["GeminiProvider"]
        M["MockProvider"]
    end
    subgraph DADOS["Dados"]
        DB[("PostgreSQL<br/>usuários · provedores · agentes<br/>empresas · execuções · auditoria")]
        S[("Sessão em cache com expiração<br/>resultados das análises")]
    end
    T --> APLICACAO
    APLICACAO --> I
    I --> O & A & G & M
    APLICACAO --> DB
    AN --> S
```

Trocar o modelo de um agente é uma alteração de **cadastro**: os módulos de aplicação chamam
`provedores.services.gerar(modelo, ...)`, e só a fábrica conhece as implementações concretas.

### Fluxo de análise

```mermaid
flowchart TD
    U["Procurador envia o PDF e escolhe o agente"] --> X["Extração do texto<br/>+ índice de qualidade"]
    X --> ESC{"É execução fiscal?<br/>heurística + modelo"}
    ESC -- não --> R["Recusa com mensagem explicativa<br/>(auditada)"]
    ESC -- sim --> INT{"Agente em<br/>modo interativo?"}
    INT -- sim --> Q["Modelo identifica lacunas<br/>e devolve perguntas (JSON)"]
    Q --> HAS{"Há perguntas?"}
    HAS -- sim --> RESP["Procurador responde na tela<br/>(texto em arquivo temporário)"]
    RESP --> CTX
    HAS -- não --> CTX
    INT -- não --> CTX{"Cabe no contexto<br/>do modelo?"}
    CTX -- sim --> UNICA["Análise em chamada única"]
    CTX -- não --> MAP["Map: análise parcial por bloco"] --> RED["Reduce: consolidação"]
    UNICA --> RES["Resultado na sessão + aviso de IA"]
    RED --> RES
    RES --> DESC["Texto dos autos descartado"]
    RES --> PDF["Exportação em PDF"]
```

O modelo de dados (diagrama ER) e as decisões técnicas estão em
[`docs/arquitetura.md`](docs/arquitetura.md).

## Stack

| Camada | Tecnologias |
|---|---|
| Back-end | Python 3.12, Django 5.2, django-environ, gunicorn, whitenoise |
| Banco | PostgreSQL 17 (psycopg 3) |
| Front-end | Templates Django, Bootstrap 5.3, Bootstrap Icons, HTMX 2 (servidos localmente) |
| IA | SDKs oficiais `openai`, `anthropic`, `google-genai` |
| PDF | pdfplumber / pypdf (leitura), reportlab (geração) |
| Segurança | cryptography (Fernet), nh3 (sanitização do HTML gerado) |
| Qualidade | pytest, pytest-django, pytest-cov, Ruff, Playwright, GitHub Actions |
| Infra | Docker, docker compose |

## Como executar

### Com Docker (recomendado)

```bash
git clone https://github.com/AltF4bio/fisco-ia.git
cd fisco-ia
docker compose up --build
```

Acesse <http://localhost:8000>. Na primeira execução o contêiner aplica as migrações e roda
`seed_demo`, que cria:

| Usuário | Perfil | Senha |
|---|---|---|
| `admin.demo` | Administrador | `Fisco.Demo-2026` |
| `procurador.demo` | Procurador | `Fisco.Demo-2026` |

Se `SECRET_KEY` e `FISCO_ENCRYPTION_KEY` não forem informadas, o contêiner as gera uma única vez
e as guarda no volume `webdata` (nunca na imagem ou no repositório). Os PDFs fictícios para
teste estão em [`exemplos/`](exemplos/).

### Localmente, sem Docker (para depurar no VS Code)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env  — depois preencha as chaves
docker compose up -d db           # ou um PostgreSQL local em localhost:5432
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

No VS Code, a configuração **Django: runserver** (`.vscode/launch.json`) inicia o servidor com
depurador; as extensões recomendadas aparecem ao abrir a pasta.

### Variáveis de ambiente

Todas estão documentadas em [`.env.example`](.env.example).

| Variável | Descrição | Padrão |
|---|---|---|
| `SECRET_KEY` | Chave do Django | — (obrigatória) |
| `DEBUG` | Modo de depuração | `False` |
| `DATABASE_URL` | Conexão PostgreSQL | `postgres://fisco:fisco@localhost:5432/fisco` |
| `FISCO_ENCRYPTION_KEY` | Chave mestra Fernet das chaves de API | — (obrigatória) |
| `FISCO_MODO_DEMO` | Atende todas as chamadas com o MockProvider | `False` (`True` no compose) |
| `FISCO_LIMIAR_QUALIDADE` | Limiar (0–1) do alerta de qualidade da extração | `0.6` |
| `FISCO_PDF_MAX_MB` | Tamanho máximo do PDF | `30` |
| `FISCO_SESSAO_MINUTOS` | Duração da sessão (e dos resultados) | `120` |
| `FISCO_LLM_TIMEOUT` | Tempo máximo de resposta do provedor (s) | `180` |
| `FISCO_TEMP_DIR` / `FISCO_SESSION_CACHE_DIR` | Diretórios temporários | pasta temporária do sistema |

#### Gerando a `FISCO_ENCRYPTION_KEY`

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guarde-a fora do repositório. Se ela for perdida ou trocada, as chaves de API cadastradas não
poderão ser decifradas e precisarão ser informadas novamente na tela de provedores.

## Modo demonstração × chaves reais

| | Modo demonstração | Chaves reais |
|---|---|---|
| Configuração | `FISCO_MODO_DEMO=True` | `FISCO_MODO_DEMO=False` |
| Respostas | MockProvider: determinísticas, montadas a partir do próprio texto dos autos | Modelo vinculado ao agente |
| Custo e rede | Nenhuma chamada externa | Consumo da API de cada provedor |
| Uso | Banca, testes, CI, portfólio | Avaliação real com procuradores |

Para usar provedores reais: defina `FISCO_MODO_DEMO=False`, entre como administrador, informe
a chave em **Provedores → Configurar**, ative o provedor, use **Testar conexão** e vincule os
agentes ao modelo desejado em **Agentes** (ou rode `python manage.py seed_agentes --modelo
<identificador>`). Os modelos iniciais (`gpt-6.1-sol`, `claude-sonnet-5-5`, `gemini-3.8-flash`
e outros) foram conferidos na documentação oficial em outubro de 2026 e podem ser editados
pela interface.

## Testes e qualidade

```bash
ruff check . && ruff format --check .
pytest --cov
```

- **124 testes** e **93% de cobertura**, com os provedores de IA sempre simulados: permissões por
  perfil, criptografia, troca de provedor e mapeamento de cada SDK, verificação de escopo,
  alerta de qualidade, modo interativo, map-reduce, upsert com revisão humana, conteúdo do log
  (garante que nenhum trecho dos autos é gravado), sanitização do HTML gerado e exportação em
  PDF/CSV.
- Os PDFs fictícios de [`exemplos/`](exemplos/) (gerados por
  [`scripts/gerar_pdfs_ficticios.py`](scripts/gerar_pdfs_ficticios.py)) também percorrem o
  fluxo real nos testes.
- O **CI** (GitHub Actions) sobe um PostgreSQL de serviço, roda Ruff, verifica migrações
  pendentes, executa a suíte com cobertura e constrói a imagem Docker — usando apenas o
  MockProvider.
- Validação ponta a ponta no sistema em execução: `pip install -r requirements-docs.txt`,
  `python -m playwright install chromium` e `python scripts/capturar_telas.py`.

## Conformidade normativa

O TCC fundamenta o sistema nas Resoluções CNJ nº 332/2020 e nº 615/2025 (uso de inteligência
artificial no Poder Judiciário, aplicadas aqui por analogia à advocacia pública) e na LGPD
(Lei nº 13.709/2018). Cada princípio virou comportamento verificável:

| Princípio | Como o sistema cumpre |
|---|---|
| **Supervisão humana** (*human-in-the-loop*) | O sistema analisa, sintetiza e organiza; não decide, não peticiona e não gera manifestação processual. Não há protocolo ou envio automático. Os prompts vedam decisão e redação de peças. A revisão do procurador prevalece sobre a extração automática na tabela consolidada. |
| **Transparência** | Aviso institucional em toda saída de IA: tela, PDF exportado (corpo e rodapé de todas as páginas), tabela consolidada e CSV. A tela de resultado mostra provedor, modelo, data/hora, usuário e se houve map-reduce ou esclarecimentos. |
| **Rastreabilidade e auditabilidade** | Log de auditoria de login, análise, perguntas, recusa por escopo, exportação e cadastros de agente, provedor, empresa e usuário. Somente leitura (bloqueado no modelo de dados e na interface) e consultável com filtros pelo administrador. |
| **Finalidade e necessidade (LGPD)** | O PDF é lido do upload e descartado. O texto extraído só existe em arquivo temporário entre as perguntas e a análise final, e é apagado em seguida (ou por expiração). Resultados ficam apenas na sessão, em cache com expiração, nunca no banco nem em `MEDIA_ROOT`. A tabela guarda apenas os campos especificados, e o log guarda apenas metadados. |
| **Segurança** | Chaves de API cifradas (Fernet) e nunca exibidas por inteiro. Controle de acesso por perfil. HTML gerado por IA sanitizado contra XSS. Usuários são desativados, não excluídos, para preservar a trilha de auditoria. |
| **Confidencialidade junto aos provedores** | Lembrete na tela de provedores: o uso institucional exige contratação que vede o uso dos dados para treinamento. Chamadas à OpenAI usam `store=False`. |
| **Escopo e proporcionalidade** | Somente execuções fiscais são processadas; outros documentos são recusados e a recusa é auditada. |
| **Qualidade dos dados** | O índice de qualidade da extração alerta sobre PDFs digitalizados sem OCR, manuscritos ou corrompidos, e o modo interativo trata lacunas antes de concluir. |

## Requisitos do TCC → código

| Requisito | Onde está |
|---|---|
| 3.1 Autenticação e perfis | [`apps/contas/perfis.py`](apps/contas/perfis.py), [`apps/core/permissoes.py`](apps/core/permissoes.py), `LoginRequiredMiddleware` em [`config/settings.py`](config/settings.py) |
| 3.2 Provedores e chaves cifradas | [`apps/provedores/cripto.py`](apps/provedores/cripto.py), [`apps/provedores/models.py`](apps/provedores/models.py), [`apps/provedores/views.py`](apps/provedores/views.py) |
| Camada de integração | [`apps/provedores/llm/`](apps/provedores/llm/) (`base.py`, `factory.py`, provedores e `mock_provider.py`), [`apps/provedores/services.py`](apps/provedores/services.py) |
| 3.3 Agentes e `seed_agentes` | [`apps/agentes/prompts.py`](apps/agentes/prompts.py), [`apps/agentes/services.py`](apps/agentes/services.py), [`seed_agentes.py`](apps/agentes/management/commands/seed_agentes.py) |
| 3.4 Extração e índice de qualidade | [`apps/analises/services/extracao.py`](apps/analises/services/extracao.py), [`qualidade.py`](apps/analises/services/qualidade.py) |
| 3.4 Verificação de escopo | [`apps/analises/services/escopo.py`](apps/analises/services/escopo.py) |
| 3.4 Map-reduce | [`apps/analises/services/blocos.py`](apps/analises/services/blocos.py), [`executor.py`](apps/analises/services/executor.py) |
| 3.4 Modo interativo | [`apps/analises/services/interativo.py`](apps/analises/services/interativo.py), [`fluxo.py`](apps/analises/services/fluxo.py) |
| 3.5 Empresas e CNPJ | [`apps/empresas/cnpj.py`](apps/empresas/cnpj.py), [`apps/empresas/views.py`](apps/empresas/views.py) |
| 3.6 Tabela consolidada | [`apps/empresas/services/consolidacao.py`](apps/empresas/services/consolidacao.py), [`tabela.py`](apps/empresas/services/tabela.py) |
| 3.7 Exportação em PDF | [`apps/core/pdf.py`](apps/core/pdf.py), [`apps/analises/services/exportacao.py`](apps/analises/services/exportacao.py) |
| 3.7 Auditoria | [`apps/auditoria/models.py`](apps/auditoria/models.py), [`services/__init__.py`](apps/auditoria/services/__init__.py), [`views.py`](apps/auditoria/views.py) |
| LGPD: descarte e sessão | [`apps/analises/services/sessao.py`](apps/analises/services/sessao.py), `CACHES`/`SESSION_ENGINE` em [`config/settings.py`](config/settings.py) |
| Aviso institucional | `AVISO_IA` em [`config/settings.py`](config/settings.py), [`templates/includes/aviso_ia.html`](templates/includes/aviso_ia.html) |
| `seed_demo` e PDFs fictícios | [`seed_demo.py`](apps/core/management/commands/seed_demo.py), [`scripts/gerar_pdfs_ficticios.py`](scripts/gerar_pdfs_ficticios.py), [`exemplos/`](exemplos/) |
| Testes | `apps/*/tests/`, [`conftest.py`](conftest.py) |

## Limitações e próximos passos

**Limitações conhecidas**
- **Não há avaliação com usuários reais.** A qualidade das análises com modelos reais ainda
  precisa ser medida com procuradores e autos reais (anonimizados).
- **Sem OCR.** PDFs digitalizados geram apenas o alerta de baixa qualidade, sem reconhecimento
  do texto.
- **Processamento síncrono.** A análise roda dentro da requisição HTTP, com timeout ampliado no
  gunicorn. Autos muito extensos com modelos reais podem demorar.
- **Estimativa de tokens aproximada** (caracteres ÷ 3,5) para decidir o map-reduce, em vez de
  contadores oficiais de cada provedor.
- **O MockProvider usa heurísticas simples.** Ele demonstra o fluxo, mas não substitui um modelo
  de linguagem.
- **Resultados apenas na sessão.** Por desenho (LGPD), fechar o navegador descarta as análises.
  Para analisar com outro agente, é preciso reenviar o PDF.

**Próximos passos**
- Avaliação qualitativa com procuradores (precisão, utilidade, tempo economizado).
- OCR (ex.: Tesseract) para autos digitalizados.
- Fila assíncrona (Celery/RQ) com acompanhamento do progresso.
- Integração institucional: login único corporativo, implantação em infraestrutura da
  procuradoria e contratos com cláusulas de não treinamento e confidencialidade.
- Contagem exata de tokens por provedor e cache de prompts.

## Estrutura do projeto

```
apps/
  agentes/      cadastro de agentes, prompts do TCC e seed_agentes
  analises/     fluxo de análise (services: extração, qualidade, escopo, blocos, executor, interativo, sessão, exportação)
  auditoria/    log de auditoria somente-leitura
  contas/       login, perfis e gestão de usuários
  core/         layout, painel, permissões, PDF, Markdown seguro, seed_demo
  empresas/     empresas, CNPJ e tabela consolidada (services: consolidação, tabela)
  provedores/   provedores, modelos, criptografia e camada de integração (llm/)
config/         settings, settings_test, urls
docs/           arquitetura e capturas de tela
exemplos/       PDFs fictícios para demonstração
scripts/        geração de PDFs fictícios e capturas de tela (Playwright)
templates/      templates Django
```

## Autor

**Fábio Luís Franco Filho** — TCC de Sistemas de Informação, UNIPAR (2026)
GitHub: [@AltF4bio](https://github.com/AltF4bio)

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

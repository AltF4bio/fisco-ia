# Arquitetura do FISCO.IA

Este documento complementa o [README](../README.md) com o modelo de dados, a organização em
camadas e as decisões técnicas do protótipo.

## Camadas

| Camada | Responsabilidade | Onde |
|---|---|---|
| Apresentação | Templates Django, Bootstrap 5 e HTMX; views finas que só validam a entrada e delegam | `templates/`, `apps/*/views.py` |
| Aplicação | Regras de negócio dos sete módulos | `apps/*/services/`, `apps/*/services.py` |
| Integração | Contrato único com os provedores de IA | `apps/provedores/llm/` |
| Dados | PostgreSQL (dados persistentes) e cache com expiração (sessões) | `apps/*/models.py`, `config/settings.py` |

### Camada de integração

```mermaid
classDiagram
    class LLMProvider {
        <<abstract>>
        +nome: str
        +generate(system_prompt, user_content, model, **opts) LLMResult
        +testar_conexao() str
    }
    class LLMResult {
        +texto: str
        +provedor: str
        +modelo: str
        +tokens_entrada: int
        +tokens_saida: int
    }
    LLMProvider <|-- OpenAIProvider : Responses API
    LLMProvider <|-- AnthropicProvider : Messages API
    LLMProvider <|-- GeminiProvider : generate_content
    LLMProvider <|-- MockProvider : determinístico
    LLMProvider ..> LLMResult
    class factory {
        +get_provider(nome, api_key, timeout) LLMProvider
    }
    factory ..> LLMProvider
```

- Os erros de cada SDK são traduzidos para uma hierarquia própria (`LLMAutenticacaoError`,
  `LLMConexaoError`, `LLMLimiteError`, `LLMRecusaError`), com mensagens seguras para o usuário.
- A opção `tarefa` (`escopo`, `perguntas`, `analise`, `parcial`, `consolidacao`, `extracao`) é
  ignorada pelos provedores reais, cujo comportamento vem do prompt. O MockProvider a usa para
  escolher a resposta de exemplo.
- `provedores.services.gerar(modelo, ...)` é o único ponto de entrada usado pelos módulos de
  aplicação. Em modo demonstração, todas as chamadas vão para o MockProvider.

## Modelo de dados

```mermaid
erDiagram
    USER ||--o{ LOG_AUDITORIA : "registra"
    USER }o--o{ GROUP : "perfil"
    USER ||--o{ EMPRESA : "cadastra"
    PROVEDOR_IA ||--o{ MODELO_IA : "oferece"
    MODELO_IA ||--o{ AGENTE : "executa"
    EMPRESA ||--o{ EXECUCAO_FISCAL : "possui"

    USER {
        int id PK
        string username
        string first_name
        bool is_active
    }
    GROUP {
        int id PK
        string name "Administrador | Procurador"
    }
    PROVEDOR_IA {
        int id PK
        string tipo UK "openai | anthropic | gemini | mock"
        bool ativo
        text chave_cifrada "Fernet"
        string chave_mascarada "sk-...a1b2"
        datetime ultimo_teste_em
        bool ultimo_teste_ok
        string ultimo_teste_mensagem
    }
    MODELO_IA {
        int id PK
        int provedor_id FK
        string identificador "id do modelo na API"
        string nome_exibicao
        int limite_contexto_tokens
        int max_saida_tokens
        bool ativo
    }
    AGENTE {
        int id PK
        string nome
        string slug UK
        text descricao
        text prompt
        int modelo_id FK
        bool modo_interativo
        bool ativo
        bool interno "extrator estruturado"
    }
    EMPRESA {
        int id PK
        string razao_social
        string cnpj UK "numérico ou alfanumérico"
        text observacoes
        int criado_por_id FK
    }
    EXECUCAO_FISCAL {
        int id PK
        int empresa_id FK
        string numero_processo UK "chave do upsert"
        json cdas
        decimal valor_executado
        json bens_penhorados
        json apropriacoes "descricao + protocolo_sefa"
        json teses_defesa
        string situacao
        string situacao_detalhe
        bool acao_imediata
        bool revisado_manualmente
        json campos_revisados
        datetime ultima_atualizacao
    }
    LOG_AUDITORIA {
        int id PK
        datetime criado_em
        int usuario_id FK
        string usuario_nome
        string acao
        string resultado "sucesso | erro | recusado"
        string numero_processo
        string agente
        string provedor
        string modelo
        string objeto
        string detalhe
        string ip
    }
```

Não existe tabela de análises. O conteúdo dos autos e o texto das análises não são
persistidos no banco (veja a próxima seção).

## Decisões técnicas

### Ciclo de vida dos dados processuais (LGPD)

| Dado | Onde fica | Por quanto tempo |
|---|---|---|
| PDF enviado | Memória ou arquivo temporário do próprio Django durante a requisição | Até o fim da requisição |
| Texto extraído (análise direta) | Memória | Até o fim da requisição |
| Texto extraído (modo interativo) | Arquivo em `FISCO_TEMP_DIR`, com nome UUID | Até a análise final ou o cancelamento; arquivos órfãos são removidos por expiração (`limpar_temporarios`) |
| Resultado da análise | Sessão do usuário, em cache de arquivos com expiração (`SESSION_ENGINE=cache`) | Duração da sessão (`FISCO_SESSAO_MINUTOS`) ou fechamento do navegador |
| Dados da tabela consolidada | PostgreSQL | Permanente (apenas os campos especificados) |
| Log de auditoria | PostgreSQL | Permanente, somente metadados |

### Verificação de escopo

1. Heurística por expressões regulares (execução fiscal, Lei 6.830/80, CDA, Certidão de Dívida
   Ativa, Fazenda Pública, dívida ativa). Sem nenhum termo, o documento é recusado sem
   chamar o modelo.
2. Checagem rápida pelo modelo com uma amostra de até 12 mil caracteres e resposta em JSON.
3. Se o JSON não puder ser interpretado, vale a heurística (mínimo de dois termos).

### Map-reduce

- Orçamento de entrada = `limite_contexto × 0,9 − max_saida − tokens do prompt`.
- O texto é dividido preservando folhas inteiras (`--- [fl. N] ---`); uma folha maior que o
  orçamento é fatiada.
- **Map:** cada bloco recebe o prompt do agente e uma instrução de análise parcial.
- **Reduce:** as parciais são consolidadas. Se não couberem juntas, a consolidação é feita
  hierarquicamente, em grupos.
- O modelo de demonstração tem contexto de 8 mil tokens para que o PDF de exemplo extenso
  acione o map-reduce.

### Modo interativo

O modelo recebe o prompt de esclarecimento e as instruções do agente, e devolve
`{"perguntas": [{"id", "pergunta", "referencia"}]}`. A resposta é validada: no máximo 5
perguntas, tamanho limitado e itens malformados descartados. JSON inválido equivale a "sem
perguntas", e a análise segue normalmente. As respostas do procurador entram no conteúdo
enviado ao modelo sob o título `ESCLARECIMENTOS DO PROCURADOR`.

### Tabela consolidada

- O agente interno `extracao-estruturada` devolve JSON, que é validado e normalizado
  (`DadosExecucao`): datas e valores em formato brasileiro, situação restrita aos códigos
  válidos e listas deduplicadas e limitadas.
- O upsert usa `select_for_update` pelo número do processo. Um processo vinculado a outra
  empresa não é sobrescrito.
- Campos alterados pelo procurador entram em `campos_revisados` e são preservados nas
  próximas extrações.

### Segurança

- `LoginRequiredMiddleware`: toda view exige login, exceto login e verificação de saúde.
- Mixins `AdministradorMixin` e `ProcuradorMixin` devolvem 403. Os menus usam as mesmas
  funções de perfil.
- Chave mestra Fernet lida do ambiente. No Docker, quando ausente, é gerada uma única vez no
  volume `webdata`.
- O Markdown gerado pelos modelos é convertido e sanitizado com `nh3`: tags restritas, sem
  atributos e sem URLs.
- O log de auditoria bloqueia `save()` de registros existentes, `delete()`, `update()` e
  `delete()` em massa.

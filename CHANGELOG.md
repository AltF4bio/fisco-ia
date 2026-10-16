# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o versionamento segue o
[SemVer](https://semver.org/lang/pt-BR/).

## [1.1.0] — 2026-10-16

Validação de ponta a ponta com um modelo de IA generativa real (Google Gemini 3.6 Flash) em um
processo real de execução fiscal, de acesso público: os cinco agentes, a extração estruturada,
a exportação em PDF e a auditoria funcionaram. As correções abaixo resultam de defeitos que só
apareceram com o provedor real.

### Corrigido
- O cliente oficial do Gemini (`google-genai`) se fechava ao ser descartado, antes de a
  requisição ser enviada; o teste de conexão falhava sem mensagem e as análises teriam falhado.
  O cliente agora permanece aberto durante toda a chamada.
- Falhas passageiras do provedor (sobrecarga HTTP 503 e cota por minuto HTTP 429)
  interrompiam a operação na primeira tentativa. Agora há até cinco tentativas automáticas, com
  espera crescente que cobre a janela de cota por minuto.
- A extração estruturada para a tabela consolidada enviava os autos inteiros, mesmo acima do
  contexto ou da cota do modelo. Agora os autos extensos são divididos em blocos e os
  resultados são combinados (listas unidas; número e valor do início; situação do bloco mais
  recente).
- Falhas inesperadas de um provedor geravam erro interno sem mensagem na tela; agora são
  convertidas em mensagens compreensíveis.
- O `seed_demo`, executado a cada inicialização do contêiner, revinculava os agentes ao modelo
  de demonstração, desfazendo a escolha do administrador.

### Alterado
- Mensagens específicas para modelo indisponível na chave (HTTP 404), sobrecarga do serviço e
  cota esgotada.
- O log do servidor passa a registrar, para cada chamada, a tarefa, o modelo e o tamanho
  estimado do envio, além do motivo das recusas do provedor (somente metadados, nunca o
  conteúdo dos autos).
- README com a seção "Validação com IA real", limitações atualizadas e 132 testes (93% de
  cobertura).

## [1.0.0] — 2026-10-06

Primeira versão do protótipo apresentado no TCC.

### Adicionado
- Autenticação nativa com perfis Administrador e Procurador, permissões nas views e nos menus.
- Gestão de usuários pelo administrador (criação, edição, redefinição de senha, desativação).
- Configuração de provedores (OpenAI, Anthropic, Google Gemini) com chaves cifradas (Fernet),
  exibição mascarada, teste de conexão e cadastro de modelos.
- Camada de integração `LLMProvider` com OpenAIProvider, AnthropicProvider, GeminiProvider,
  MockProvider e fábrica `get_provider`.
- Cadastro de agentes e comando `seed_agentes` com os cinco agentes do TCC e o extrator interno.
- Análise de autos: extração de texto com índice de qualidade, verificação de escopo de
  execução fiscal, map-reduce para autos extensos, modo interativo de esclarecimento e
  exportação em PDF.
- Empresas com validação de CNPJ numérico e alfanumérico.
- Tabela consolidada de execuções alimentada por extração estruturada, com upsert pelo número
  do processo, revisão humana prevalente, filtros, ordenação, totais, destaque de ação imediata
  e exportação em CSV e PDF.
- Log de auditoria somente-leitura, apenas com metadados, e consulta com filtros.
- Descarte dos autos após a análise e resultados mantidos apenas na sessão (LGPD).
- Comandos `seed_demo` e `limpar_temporarios`; PDFs fictícios de demonstração.
- Docker e docker compose, CI no GitHub Actions, 124 testes (93% de cobertura) e percurso
  ponta a ponta com Playwright.

[1.1.0]: https://github.com/AltF4bio/fisco-ia/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/AltF4bio/fisco-ia/releases/tag/v1.0.0

# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o versionamento segue o
[SemVer](https://semver.org/lang/pt-BR/).

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

[1.0.0]: https://github.com/AltF4bio/fisco-ia/releases/tag/v1.0.0

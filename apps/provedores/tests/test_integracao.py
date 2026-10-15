"""Camada de integração: fábrica, troca de provedor e mapeamento de cada SDK.

Nenhum teste chama APIs reais: os clientes dos SDKs são substituídos por dublês.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import httpx2 as httpx
import openai
import pytest

from apps.provedores import services
from apps.provedores.llm import (
    LLMAutenticacaoError,
    LLMError,
    LLMRecusaError,
    Tarefa,
    get_provider,
)
from apps.provedores.llm.anthropic_provider import AnthropicProvider
from apps.provedores.llm.gemini_provider import GeminiProvider
from apps.provedores.llm.mock_provider import MockProvider
from apps.provedores.llm.openai_provider import OpenAIProvider
from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor


@pytest.mark.parametrize(
    ("nome", "classe"),
    [
        ("openai", OpenAIProvider),
        ("anthropic", AnthropicProvider),
        ("gemini", GeminiProvider),
        ("mock", MockProvider),
    ],
)
def test_fabrica_instancia_cada_provedor(nome, classe):
    provedor = get_provider(nome, api_key="k")
    assert isinstance(provedor, classe)
    assert provedor.api_key == "k"


def test_fabrica_rejeita_provedor_desconhecido():
    with pytest.raises(ValueError):
        get_provider("inexistente")


# --- mapeamento dos SDKs ------------------------------------------------------


def test_openai_usa_responses_api(monkeypatch):
    cliente = MagicMock()
    cliente.responses.create.return_value = SimpleNamespace(
        output_text="resposta", usage=SimpleNamespace(input_tokens=10, output_tokens=5)
    )
    provedor = OpenAIProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    resultado = provedor.generate("sistema", "autos", "gpt-x", json=True, max_tokens=100)
    kwargs = cliente.responses.create.call_args.kwargs
    assert kwargs["instructions"] == "sistema"
    assert kwargs["input"] == "autos"
    assert kwargs["model"] == "gpt-x"
    assert kwargs["max_output_tokens"] == 100
    assert kwargs["store"] is False
    assert kwargs["text"] == {"format": {"type": "json_object"}}
    assert resultado.texto == "resposta" and resultado.tokens_entrada == 10


def test_openai_traduz_erro_de_autenticacao(monkeypatch):
    requisicao = httpx.Request("POST", "https://api.openai.com/v1/responses")
    erro = openai.AuthenticationError(
        "inválida", response=httpx.Response(401, request=requisicao), body=None
    )
    cliente = MagicMock()
    cliente.responses.create.side_effect = erro
    provedor = OpenAIProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    with pytest.raises(LLMAutenticacaoError):
        provedor.generate("s", "u", "gpt-x")


def test_anthropic_usa_messages_api(monkeypatch):
    cliente = MagicMock()
    cliente.messages.create.return_value = SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="text", text="olá "),
            SimpleNamespace(type="text", text="mundo"),
        ],
        usage=SimpleNamespace(input_tokens=7, output_tokens=3),
    )
    provedor = AnthropicProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    resultado = provedor.generate("sistema", "autos", "claude-x", max_tokens=50)
    kwargs = cliente.messages.create.call_args.kwargs
    assert kwargs["system"] == "sistema"
    assert kwargs["messages"] == [{"role": "user", "content": "autos"}]
    assert kwargs["max_tokens"] == 50
    assert "temperature" not in kwargs
    assert resultado.texto == "olá mundo"


def test_anthropic_trata_recusa(monkeypatch):
    cliente = MagicMock()
    cliente.messages.create.return_value = SimpleNamespace(
        stop_reason="refusal", content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=0)
    )
    provedor = AnthropicProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    with pytest.raises(LLMRecusaError):
        provedor.generate("s", "u", "claude-x")


def test_anthropic_traduz_erro_de_conexao(monkeypatch):
    cliente = MagicMock()
    cliente.messages.create.side_effect = anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    provedor = AnthropicProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    with pytest.raises(LLMError):
        provedor.generate("s", "u", "claude-x")


def test_gemini_usa_generate_content(monkeypatch):
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente  # usado em bloco with
    cliente.models.generate_content.return_value = SimpleNamespace(
        text='{"ok": true}',
        usage_metadata=SimpleNamespace(prompt_token_count=4, candidates_token_count=2),
    )
    provedor = GeminiProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    resultado = provedor.generate("sistema", "autos", "gemini-x", json=True)
    kwargs = cliente.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-x"
    assert kwargs["contents"] == "autos"
    assert kwargs["config"].system_instruction == "sistema"
    assert kwargs["config"].response_mime_type == "application/json"
    assert resultado.tokens_saida == 2


# --- serviços: roteamento e troca de provedor ---------------------------------


@pytest.fixture
def provedores_configurados(db):
    for tipo in (TipoProvedor.OPENAI, TipoProvedor.ANTHROPIC):
        provedor = ProvedorIA.objects.get(tipo=tipo)
        provedor.definir_chave(f"chave-{tipo}-123456")
        provedor.ativo = True
        provedor.save()


def test_troca_de_modelo_muda_o_provedor_sem_alterar_o_chamador(
    settings, provedores_configurados, monkeypatch
):
    settings.FISCO_MODO_DEMO = False
    chamadas = []

    def falso_generate(self, system_prompt, user_content, model, **opts):
        chamadas.append((self.nome, model, self.api_key))
        return services.LLMResult(texto="ok", provedor=self.nome, modelo=model)

    monkeypatch.setattr(OpenAIProvider, "generate", falso_generate)
    monkeypatch.setattr(AnthropicProvider, "generate", falso_generate)

    for identificador in ("gpt-6.1-sol", "claude-sonnet-5-5"):
        modelo = ModeloIA.objects.get(identificador=identificador)
        services.gerar(modelo, "sistema", "autos")

    assert chamadas == [
        ("openai", "gpt-6.1-sol", "chave-openai-123456"),
        ("anthropic", "claude-sonnet-5-5", "chave-anthropic-123456"),
    ]


def test_modo_demo_usa_sempre_o_mock(settings, provedores_configurados):
    settings.FISCO_MODO_DEMO = True
    modelo = ModeloIA.objects.get(identificador="claude-sonnet-5-5")
    assert isinstance(services.provedor_para(modelo), MockProvider)


def test_provedor_inativo_gera_erro(settings, db):
    settings.FISCO_MODO_DEMO = False
    modelo = ModeloIA.objects.get(identificador="gpt-6.1-sol")
    with pytest.raises(LLMError):
        services.gerar(modelo, "s", "u")


def test_somente_provedores_ativos_e_configurados_ficam_disponiveis(provedores_configurados):
    tipos = set(ModeloIA.objects.disponiveis().values_list("provedor__tipo", flat=True))
    assert tipos == {"openai", "anthropic"}
    mock = ProvedorIA.objects.get(tipo=TipoProvedor.MOCK)
    mock.ativo = True
    mock.save()
    assert "mock" in set(ModeloIA.objects.disponiveis().values_list("provedor__tipo", flat=True))


# --- MockProvider ---------------------------------------------------------------

AUTOS = """EXECUÇÃO FISCAL nº 0001234-56.2021.8.16.0004 — Lei 6.830/80
Exequente: ESTADO DO PARANÁ (Fazenda Pública). CDA nº 20210001234-5.
Valor da causa: R$ 150.000,00
Mov. 1 - 10/02/2021 - Distribuída a petição inicial de execução fiscal.
Mov. 2 - 15/03/2021 - Penhora de veículo via RENAJUD.
Mov. 3 - 20/05/2021 - Embargos à execução alegando prescrição. Documento não juntado.
Mov. 4 - 01/06/2021 - Apropriação de valores pelo Estado, protocolo SEFA nº 2021/778899.
"""


def test_mock_e_deterministico_e_usa_o_texto():
    mock = MockProvider()
    a = mock.generate("s", AUTOS, "mock-fisco", tarefa=Tarefa.ANALISE, agente="resumo-cronologico")
    b = mock.generate("s", AUTOS, "mock-fisco", tarefa=Tarefa.ANALISE, agente="resumo-cronologico")
    assert a == b
    assert "| 2 | 15/03/2021 |" in a.texto


def test_mock_extracao_estruturada():
    dados = json.loads(MockProvider().generate("s", AUTOS, "m", tarefa=Tarefa.EXTRACAO).texto)
    assert dados["numero_processo"] == "0001234-56.2021.8.16.0004"
    assert dados["cdas"] == ["20210001234-5"]
    assert dados["valor_executado"] == "150000.00"
    assert dados["apropriacoes"][0]["protocolo_sefa"] == "2021/778899"
    assert "Prescrição" in dados["teses_defesa"]


def test_mock_perguntas_e_escopo():
    perguntas = json.loads(MockProvider().generate("s", AUTOS, "m", tarefa=Tarefa.PERGUNTAS).texto)
    assert len(perguntas["perguntas"]) == 1
    escopo = json.loads(MockProvider().generate("s", AUTOS, "m", tarefa=Tarefa.ESCOPO).texto)
    assert escopo["execucao_fiscal"] is True


# --- regressões ---------------------------------------------------------------------


class _ClienteQueFechaAoSerDescartado:
    """Imita o google-genai: o cliente se fecha no __del__, e os recursos (models)
    não mantêm referência ao objeto Client."""

    def __init__(self, **kwargs):
        estado = {"fechado": False}
        self._estado = estado

        def verificar():
            if estado["fechado"]:
                raise RuntimeError("Cannot send a request, as the client has been closed.")

        def listar():
            verificar()
            yield from ("modelo-a", "modelo-b")

        def gerar(**kw):
            verificar()
            return SimpleNamespace(text="ok", usage_metadata=None)

        self.models = SimpleNamespace(list=listar, generate_content=gerar)

    def close(self):
        self._estado["fechado"] = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()


def test_gemini_mantem_o_cliente_aberto_durante_a_chamada(monkeypatch):
    from apps.provedores.llm import gemini_provider

    monkeypatch.setattr(gemini_provider.genai, "Client", _ClienteQueFechaAoSerDescartado)
    provedor = GeminiProvider(api_key="k")
    assert "2 modelos" in provedor.testar_conexao()
    assert provedor.generate("s", "u", "gemini-x").texto == "ok"


def test_falha_inesperada_do_sdk_vira_mensagem_e_e_registrada(db, monkeypatch):
    gemini = ProvedorIA.objects.get(tipo=TipoProvedor.GEMINI)
    gemini.definir_chave("chave-gemini-123456")
    gemini.save()

    def explode(self):
        raise RuntimeError("falha interna do SDK")

    monkeypatch.setattr(GeminiProvider, "testar_conexao", explode)
    sucesso, mensagem = services.testar_conexao(gemini)
    assert not sucesso
    assert "Falha inesperada" in mensagem and "RuntimeError" in mensagem
    gemini.refresh_from_db()
    assert gemini.ultimo_teste_ok is False


def test_gemini_repete_automaticamente_falhas_passageiras():
    opcoes = GeminiProvider(api_key="k")._cliente()._api_client._http_options.retry_options
    assert opcoes.attempts >= 3
    assert {429, 503} <= set(opcoes.http_status_codes)


def test_gemini_sobrecarregado_gera_mensagem_clara(monkeypatch):
    from google.genai import errors as gerrors

    from apps.provedores.llm import LLMConexaoError

    erro = gerrors.ServerError(503, {"error": {"code": 503, "message": "overloaded"}})
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.models.generate_content.side_effect = erro
    provedor = GeminiProvider(api_key="k")
    monkeypatch.setattr(provedor, "_cliente", lambda: cliente)
    with pytest.raises(LLMConexaoError, match="temporariamente indisponível"):
        provedor.generate("s", "u", "gemini-x")

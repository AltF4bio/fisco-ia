"""Fixtures compartilhadas pela suíte de testes."""

import io

import pytest
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.contas.perfis import ADMINISTRADOR, PROCURADOR

SENHA = "Senha-de-teste-123"

# Autos fictícios usados nos testes (dados inventados).
MOVIMENTACOES = [
    "Mov. 1 - 10/02/2021 - Distribuída a execução fiscal com base na CDA nº 20210001234-5.",
    "Mov. 2 - 15/03/2021 - Despacho: cite-se a executada nos termos da Lei 6.830/80.",
    "Mov. 3 - 20/05/2021 - Penhora de veículo via RENAJUD, placa fictícia AAA-0000.",
    "Mov. 4 - 02/08/2021 - Embargos à execução alegando prescrição e nulidade da CDA.",
    "Mov. 5 - 10/09/2021 - Juntada de procuração. Documento não juntado aos autos.",
    "Mov. 6 - 01/06/2022 - Sentença: julgo improcedentes os embargos.",
    "Mov. 7 - 15/07/2022 - Apropriação de valores pelo Estado, protocolo SEFA nº 2022/445566.",
    "Mov. 8 - 01/09/2022 - Intime-se a Fazenda Pública para manifestação em 30 dias.",
]
CABECALHO = [
    "PODER JUDICIÁRIO DO ESTADO DO PARANÁ — VARA DE EXECUÇÕES FISCAIS ESTADUAIS",
    "EXECUÇÃO FISCAL nº 0001234-56.2021.8.16.0004",
    "Exequente: ESTADO DO PARANÁ (Fazenda Pública). Executada: EMPRESA FICTÍCIA LTDA.",
    "Certidão de Dívida Ativa — CDA nº 20210001234-5. Valor da causa: R$ 150.000,00",
]
TEXTO_NAO_FISCAL = [
    "CONTRATO DE LOCAÇÃO RESIDENCIAL",
    "Locador: Fulano de Tal. Locatário: Beltrano de Tal.",
    "Cláusula 1ª — O imóvel destina-se exclusivamente a fins residenciais.",
    "Cláusula 2ª — O aluguel mensal é de R$ 2.000,00, com vencimento no dia 5.",
]


def fazer_pdf(paginas: list[list[str]]) -> bytes:
    """Gera um PDF simples em memória (uma lista de linhas por página)."""
    buffer = io.BytesIO()
    documento = canvas.Canvas(buffer, pagesize=A4)
    for linhas in paginas:
        y = 800
        for linha in linhas:
            documento.drawString(40, y, linha)
            y -= 16
        documento.showPage()
    documento.save()
    return buffer.getvalue()


def como_upload(conteudo: bytes, nome: str = "autos.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


def _criar_usuario(username: str, perfil: str | None) -> User:
    usuario = User.objects.create_user(
        username=username, password=SENHA, first_name=username.title()
    )
    if perfil:
        usuario.groups.add(Group.objects.get(name=perfil))
    return usuario


@pytest.fixture(autouse=True)
def _diretorios_temporarios(settings, tmp_path):
    """Isola os arquivos temporários de cada teste."""
    settings.FISCO_TEMP_DIR = str(tmp_path / "autos")
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def admin_user(db) -> User:
    return _criar_usuario("admin.teste", ADMINISTRADOR)


@pytest.fixture
def procurador(db) -> User:
    return _criar_usuario("procurador.teste", PROCURADOR)


@pytest.fixture
def cliente_admin(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def cliente_procurador(client, procurador):
    client.force_login(procurador)
    return client


@pytest.fixture
def agentes(db):
    """Agentes do TCC vinculados ao modelo de demonstração (MockProvider ativo)."""
    from apps.agentes.models import Agente
    from apps.agentes.services import semear_agentes
    from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor

    ProvedorIA.objects.filter(tipo=TipoProvedor.MOCK).update(ativo=True)
    semear_agentes(ModeloIA.objects.get(identificador="mock-fisco"))
    return {agente.slug: agente for agente in Agente.objects.all()}


@pytest.fixture
def pdf_execucao() -> bytes:
    return fazer_pdf([CABECALHO + MOVIMENTACOES[:4], MOVIMENTACOES[4:]])


@pytest.fixture
def pdf_nao_fiscal() -> bytes:
    return fazer_pdf([TEXTO_NAO_FISCAL])

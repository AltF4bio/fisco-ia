import os
import time
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command

from apps.agentes.models import Agente
from apps.analises.services import sessao
from apps.contas.perfis import eh_administrador, eh_procurador
from apps.empresas.models import Empresa
from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor


@pytest.mark.django_db
def test_seed_demo_prepara_a_demonstracao():
    call_command("seed_demo")
    call_command("seed_demo")  # idempotente
    assert eh_administrador(User.objects.get(username="admin.demo"))
    procurador = User.objects.get(username="procurador.demo")
    assert eh_procurador(procurador)
    assert procurador.check_password("Fisco.Demo-2026")
    assert ProvedorIA.objects.get(tipo=TipoProvedor.MOCK).disponivel
    assert Agente.objects.selecionaveis().count() == 5
    assert set(Agente.objects.values_list("modelo__identificador", flat=True)) == {"mock-fisco"}
    assert Empresa.objects.get().cnpj_formatado == "45.723.174/0001-10"


@pytest.mark.django_db
def test_seed_demo_preserva_modelo_escolhido_pelo_administrador():
    call_command("seed_demo")
    agente = Agente.objects.get(slug="resumo-cronologico")
    agente.modelo = ModeloIA.objects.get(identificador="gemini-3.8-flash")
    agente.save()
    call_command("seed_demo")  # reinício do contêiner
    agente.refresh_from_db()
    assert agente.modelo.identificador == "gemini-3.8-flash"


def test_limpar_temporarios_remove_apenas_expirados():
    antigo = sessao.guardar_texto_temporario("autos antigos")
    recente = sessao.guardar_texto_temporario("autos recentes")
    caminho_antigo = Path(settings.FISCO_TEMP_DIR) / f"{antigo}.txt"
    passado = time.time() - 3 * 3600
    os.utime(caminho_antigo, (passado, passado))

    call_command("limpar_temporarios", idade=3600)

    assert not caminho_antigo.exists()
    assert sessao.ler_texto_temporario(recente) == "autos recentes"


def test_token_invalido_nao_acessa_arquivos_fora_do_diretorio():
    assert sessao.ler_texto_temporario("../../etc/passwd") is None

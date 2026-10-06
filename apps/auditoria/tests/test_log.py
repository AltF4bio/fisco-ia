import pytest

from apps.auditoria.models import Acao, LogAuditoria, LogSomenteLeituraError
from apps.auditoria.services import registrar


@pytest.mark.django_db
def test_log_nao_pode_ser_alterado_nem_excluido(procurador):
    log = registrar(Acao.ANALISE, usuario=procurador, numero_processo="0001234-56.2020.8.16.0001")
    log.detalhe = "alterado"
    with pytest.raises(LogSomenteLeituraError):
        log.save()
    with pytest.raises(LogSomenteLeituraError):
        log.delete()
    with pytest.raises(LogSomenteLeituraError):
        LogAuditoria.objects.all().delete()
    with pytest.raises(LogSomenteLeituraError):
        LogAuditoria.objects.update(detalhe="x")


@pytest.mark.django_db
def test_registrar_trunca_campos_de_metadados(procurador):
    log = registrar(Acao.ANALISE, usuario=procurador, detalhe="x" * 1000, objeto="y" * 1000)
    assert len(log.detalhe) == 255
    assert len(log.objeto) == 200
    assert log.usuario_nome == procurador.username

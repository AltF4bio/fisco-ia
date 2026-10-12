"""Prepara o sistema para demonstração imediata (dados fictícios)."""

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from apps.agentes.services import semear_agentes
from apps.contas.perfis import ADMINISTRADOR, PROCURADOR
from apps.empresas.models import Empresa
from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor

SENHA_PADRAO = "Fisco.Demo-2026"

USUARIOS = [
    ("admin.demo", "Ana", "Administradora (demo)", ADMINISTRADOR),
    ("procurador.demo", "Paulo", "Procurador (demo)", PROCURADOR),
]

EMPRESA_DEMO = {
    "cnpj": "45723174000110",
    "razao_social": "Metalúrgica Horizonte Fictícia Ltda.",
    "observacoes": "Empresa fictícia criada para demonstração do protótipo. "
    "Use os PDFs da pasta exemplos/ para alimentar a tabela consolidada.",
}


class Command(BaseCommand):
    help = (
        "Cria administrador e procurador de demonstração, uma empresa fictícia e ativa o "
        "MockProvider vinculando a ele os agentes do TCC."
    )

    def add_arguments(self, parser):
        parser.add_argument("--senha", default=SENHA_PADRAO, help="Senha dos usuários de demo.")

    def handle(self, *args, senha: str, **options):
        for username, nome, sobrenome, perfil in USUARIOS:
            usuario, criado = User.objects.get_or_create(
                username=username, defaults={"first_name": nome, "last_name": sobrenome}
            )
            if criado:
                usuario.set_password(senha)
                usuario.save()
            usuario.groups.set([Group.objects.get(name=perfil)])
            situacao = "criado" if criado else "já existia (senha mantida)"
            self.stdout.write(f"  Usuário {username} [{perfil}] — {situacao}")

        mock = ProvedorIA.objects.get(tipo=TipoProvedor.MOCK)
        mock.ativo = True
        mock.save()
        modelo_demo = ModeloIA.objects.get(provedor=mock, identificador="mock-fisco")
        # Agentes já existentes mantêm o modelo escolhido pelo administrador; só os
        # criados agora são vinculados ao modelo de demonstração.
        criados = [
            agente
            for agente, criado in semear_agentes()
            if criado and agente.modelo_id != modelo_demo.pk
        ]
        for agente in criados:
            agente.modelo = modelo_demo
            agente.save(update_fields=["modelo"])
        self.stdout.write(
            f"  MockProvider ativo; {len(criados)} agente(s) novo(s) vinculado(s) à demonstração."
        )

        empresa, _ = Empresa.objects.get_or_create(cnpj=EMPRESA_DEMO["cnpj"], defaults=EMPRESA_DEMO)
        self.stdout.write(f"  Empresa fictícia: {empresa} ({empresa.cnpj_formatado})")

        if not settings.FISCO_MODO_DEMO:
            self.stdout.write(
                self.style.WARNING(
                    "  Atenção: FISCO_MODO_DEMO=False. Os agentes usam o modelo de demonstração, "
                    "mas defina FISCO_MODO_DEMO=True para garantir que nenhuma chamada real ocorra."
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demonstração pronta. Acesse com admin.demo ou procurador.demo (senha: {senha})."
            )
        )

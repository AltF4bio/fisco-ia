from django.core.management.base import BaseCommand, CommandError

from apps.agentes.services import semear_agentes
from apps.provedores.models import ModeloIA


class Command(BaseCommand):
    help = "Cadastra os cinco agentes previstos no TCC e o agente interno de extração."

    def add_arguments(self, parser):
        parser.add_argument(
            "--modelo",
            help="Identificador do modelo a vincular (ex.: claude-sonnet-5-5). "
            "Padrão: primeiro modelo disponível de um provedor ativo.",
        )
        parser.add_argument(
            "--atualizar-prompts",
            action="store_true",
            help="Sobrescreve nome, descrição e prompt de agentes já existentes.",
        )

    def handle(self, *args, modelo=None, atualizar_prompts=False, **options):
        modelo_obj = None
        if modelo:
            modelo_obj = ModeloIA.objects.filter(identificador=modelo).first()
            if modelo_obj is None:
                raise CommandError(f"Modelo {modelo!r} não está cadastrado.")
        for agente, criado in semear_agentes(modelo_obj, atualizar_prompts=atualizar_prompts):
            situacao = "criado" if criado else "mantido/atualizado"
            self.stdout.write(f"  {agente.nome} ({agente.modelo}) — {situacao}")
        self.stdout.write(self.style.SUCCESS("Agentes cadastrados."))

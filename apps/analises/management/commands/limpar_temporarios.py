from django.core.management.base import BaseCommand

from apps.analises.services.sessao import limpar_temporarios_expirados


class Command(BaseCommand):
    help = (
        "Remove textos de autos temporários expirados (análises interativas abandonadas). "
        "Pode ser agendado periodicamente; a limpeza também ocorre a cada nova análise."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--idade",
            type=int,
            default=None,
            help="Idade mínima, em segundos, dos arquivos removidos (padrão: duração da sessão).",
        )

    def handle(self, *args, idade=None, **options):
        removidos = limpar_temporarios_expirados(idade)
        self.stdout.write(self.style.SUCCESS(f"{removidos} arquivo(s) temporário(s) removido(s)."))

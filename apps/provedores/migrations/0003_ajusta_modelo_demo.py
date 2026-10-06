"""Ajusta o modelo de demonstração: contexto de 8.000 tokens e saída de 2.000.

O contexto continua pequeno de propósito, para que PDFs de exemplo maiores
acionem a divisão em blocos (map-reduce) na demonstração.
"""

from django.db import migrations


def ajustar(apps, schema_editor):
    apps.get_model("provedores", "ModeloIA").objects.filter(
        provedor__tipo="mock", identificador="mock-fisco"
    ).update(limite_contexto_tokens=8_000, max_saida_tokens=2_000)


class Migration(migrations.Migration):
    dependencies = [("provedores", "0002_dados_iniciais")]

    operations = [migrations.RunPython(ajustar, migrations.RunPython.noop)]

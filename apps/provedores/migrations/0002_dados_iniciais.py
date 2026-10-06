"""Cadastro inicial de provedores e modelos.

Identificadores conferidos na documentação oficial de cada provedor em outubro de
2026. O administrador pode cadastrar, editar ou desativar modelos pela interface;
nenhum identificador de modelo é fixado no código da aplicação.
"""

from django.db import migrations

PROVEDORES = ("openai", "anthropic", "gemini", "mock")

# (provedor, identificador, nome de exibição, contexto em tokens, saída máxima)
MODELOS = [
    ("openai", "gpt-6.1-sol", "GPT-6.1 Sol", 1_050_000, 16_000),
    ("openai", "gpt-6-luna", "GPT-6 Luna", 1_050_000, 16_000),
    ("openai", "gpt-6-astra", "GPT-6 Astra", 1_050_000, 16_000),
    ("anthropic", "claude-opus-5-5", "Claude Opus 5.5", 1_000_000, 16_000),
    ("anthropic", "claude-sonnet-5-5", "Claude Sonnet 5.5", 1_000_000, 16_000),
    ("anthropic", "claude-haiku-4-5", "Claude Haiku 4.5", 200_000, 16_000),
    ("gemini", "gemini-3.8-flash", "Gemini 3.8 Flash", 1_048_576, 16_000),
    ("gemini", "gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite", 1_048_576, 16_000),
    # Contexto propositalmente pequeno para demonstrar a divisão em blocos (map-reduce).
    ("mock", "mock-fisco", "Modelo de demonstração", 6_000, 4_000),
]


def popular(apps, schema_editor):
    ProvedorIA = apps.get_model("provedores", "ProvedorIA")
    ModeloIA = apps.get_model("provedores", "ModeloIA")
    provedores = {tipo: ProvedorIA.objects.get_or_create(tipo=tipo)[0] for tipo in PROVEDORES}
    for tipo, identificador, nome, contexto, saida in MODELOS:
        ModeloIA.objects.get_or_create(
            provedor=provedores[tipo],
            identificador=identificador,
            defaults={
                "nome_exibicao": nome,
                "limite_contexto_tokens": contexto,
                "max_saida_tokens": saida,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("provedores", "0001_provedores_e_modelos")]

    operations = [migrations.RunPython(popular, migrations.RunPython.noop)]

"""Prompts internos do fluxo de análise (complementam o prompt de cada agente)."""

VERIFICACAO_ESCOPO = """Você classifica documentos jurídicos. Responda se o documento a seguir é
(ou integra) um processo de EXECUÇÃO FISCAL — cobrança judicial da Dívida Ativa da Fazenda
Pública regida pela Lei nº 6.830/1980, normalmente fundada em Certidão de Dívida Ativa
(CDA). Embargos à execução fiscal, exceções de pré-executividade e recursos dentro desse
processo também contam como execução fiscal. Ações cíveis comuns, trabalhistas, criminais,
de família, contratos, notas fiscais avulsas e outros documentos NÃO são execução fiscal.

Devolva somente um objeto JSON no formato:
{"execucao_fiscal": true ou false, "justificativa": "uma frase curta"}"""

ESCLARECIMENTO = """Antes de concluir a análise solicitada (instruções do agente abaixo), examine
os autos e identifique LACUNAS ou AMBIGUIDADES que impeçam uma análise segura, por exemplo:
movimentações ou trechos ilegíveis; referência a documentos que não foram juntados;
informações contraditórias (datas, valores, partes); atos citados sem conteúdo nos autos.

Formule no máximo 5 perguntas específicas ao procurador, cada uma indicando a movimentação
ou folha de referência. Não pergunte nada que possa ser respondido pela leitura dos autos.
Se não houver lacunas relevantes, devolva a lista vazia.

Devolva somente um objeto JSON no formato:
{"perguntas": [{"id": "p1", "pergunta": "texto da pergunta", "referencia": "Mov. 12"}]}

INSTRUÇÕES DO AGENTE (para contexto):
"""

ANALISE_PARCIAL = """

ATENÇÃO: você está recebendo apenas o BLOCO {indice} de {total} dos autos (o documento foi
dividido por exceder o limite de contexto do modelo). Analise somente este bloco, seguindo
as instruções acima, e preserve números de movimentação, folhas e datas. Não conclua sobre
o processo como um todo: sua análise parcial será consolidada com as dos demais blocos."""

CONSOLIDACAO = """

ATENÇÃO: você está recebendo ANÁLISES PARCIAIS de blocos consecutivos dos mesmos autos.
Consolide-as em uma única análise final, seguindo as instruções e o formato acima:
elimine repetições, ordene as informações, preserve as citações de movimentações e folhas
e resolva sobreposições entre blocos. Não acrescente fatos que não estejam nas análises
parciais."""

CABECALHO_AUTOS = "AUTOS DO PROCESSO (texto extraído do PDF; cada folha inicia com [fl. N]):\n\n"
CABECALHO_ESCLARECIMENTOS = "\n\nESCLARECIMENTOS DO PROCURADOR\n"

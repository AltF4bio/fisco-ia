"""Instruções complementares do agente interno de extração estruturada."""

EXTRACAO_PARCIAL = """

ATENÇÃO: os autos foram divididos por excederem o limite do modelo, e você está recebendo apenas o BLOCO {indice} de {total}. Extraia somente os dados que constam deste bloco e use "", [] ou null para o que não constar dele. Os campos "situacao", "situacao_detalhe" e "acao_imediata" devem refletir a movimentação mais recente presente neste bloco. Os resultados de todos os blocos serão combinados pelo sistema."""

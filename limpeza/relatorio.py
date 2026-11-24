"""Grava a base limpa (CSV) e o relatório do que foi feito (Markdown e CSV)."""
import csv
from collections import Counter

from limpeza.pipeline import CORRIGIDO, DESCARTADO, DUVIDA

TITULOS = {
    CORRIGIDO: "Corrigido (o valor foi arrumado e entrou na base)",
    DESCARTADO: "Descartado (não entrou na base; havia versão melhor ou era cópia)",
    DUVIDA: "Em dúvida (precisa de decisão humana; ver perguntas em docs/DIAGNOSTICO.md)",
}


def _gravar_csv(caminho, colunas, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)


def gravar(resultado, pasta_saida):
    pasta_saida.mkdir(parents=True, exist_ok=True)
    _gravar_csv(pasta_saida / "precatorios.csv",
                ["numero_processo", "ente_devedor", "valor_face", "apresentado_em",
                 "prazo_pagamento", "total_pago", "origem", "situacao"],
                resultado.precatorios)
    _gravar_csv(pasta_saida / "pagamentos.csv",
                ["evento_id", "numero_processo", "tipo", "valor", "pago_em",
                 "atualizado_em", "alerta"],
                resultado.pagamentos)
    _gravar_csv(pasta_saida / "ocorrencias.csv",
                ["categoria", "arquivo", "registro", "motivo"],
                [vars(o) for o in resultado.ocorrencias])
    (pasta_saida / "relatorio.md").write_text(texto_relatorio(resultado), encoding="utf-8")


def texto_relatorio(resultado):
    contagem = Counter(o.categoria for o in resultado.ocorrencias)
    em_duvida = [p for p in resultado.precatorios if p["situacao"] == "duvida"]
    linhas = [
        "# Relatório de limpeza",
        "",
        f"- Precatórios na base: {len(resultado.precatorios)} "
        f"({len(resultado.precatorios) - len(em_duvida)} ok, {len(em_duvida)} com dúvida)",
        f"- Pagamentos e estornos aceitos: {len(resultado.pagamentos)}",
        f"- Ocorrências: {contagem[CORRIGIDO]} corrigidas, "
        f"{contagem[DESCARTADO]} descartadas, {contagem[DUVIDA]} em dúvida",
        "",
    ]
    for categoria in (DUVIDA, DESCARTADO, CORRIGIDO):
        itens = [o for o in resultado.ocorrencias if o.categoria == categoria]
        linhas += [f"## {TITULOS[categoria]}", ""]
        linhas += ["| Arquivo | Registro | Motivo |", "|---|---|---|"]
        linhas += [f"| {o.arquivo} | {o.registro} | {o.motivo} |" for o in itens]
        linhas.append("")
    linhas += ["## Totais pagos (pagamentos menos estornos)", "",
              "| Processo | Valor de face | Total pago | Situação |", "|---|---|---|---|"]
    linhas += [f"| {p['numero_processo']} | {p['valor_face']} | {p['total_pago']} | {p['situacao']} |"
               for p in resultado.precatorios]
    return "\n".join(linhas) + "\n"

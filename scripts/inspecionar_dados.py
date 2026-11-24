"""
Leitura inicial dos dados do arquivo CSV.

Serve para conferir cada fato citado em docs/DIAGNOSTICO.md.

"""

import json
from collections import Counter
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "data"

def inspecionar_tribunal():
    bruto = (DADOS / "tribunal.csv").read_bytes()
    print("== tribunal.csv ==")
    try:
        bruto.decode("utf-8")
        print("codificação: UTF-8 válido")
    except UnicodeDecodeError as erro:
        print("codificação: NÃO é UTF-8 ->", erro)
    print("termina com CRLF:", b"\r\n" in bruto)
    print("separador ';' na 1ª linha:", b";" in bruto.splitlines()[0])
    print("linhas:", bruto.decode("latin-1").splitlines())


def inspecionar_pagamentos():
    eventos = json.loads((DADOS / "pagamentos.json").read_text(encoding="utf-8"))
    print("\n== pagamentos.json ==")
    print("eventos:", len(eventos))
    print("tipos:", Counter(e["tipo"] for e in eventos))
    print("tipos de 'valor':", Counter(type(e["valor"]).__name__ for e in eventos))
    ids = Counter(e["evento_id"] for e in eventos)
    print("evento_id repetido:", {i: n for i, n in ids.items() if n > 1})
    datas = sorted(e["data_pagamento"] for e in eventos)
    print("data_pagamento (texto):", datas[0], "...", datas[-1])
    print("processos fora do padrão CNJ com máscara:",
          [e["processo"] for e in eventos if len(e["processo"]) != 25])
    print("valores <= 0 ou nulos:",
          [(e["evento_id"], e["valor"]) for e in eventos
           if not isinstance(e["valor"], (int, float)) or e["valor"] <= 0])


def inspecionar_hub_e_apresentacoes():
    print("\n== hub.csv e apresentacoes.json ==")
    print((DADOS / "hub.csv").read_text(encoding="utf-8"))
    for item in json.loads((DADOS / "apresentacoes.json").read_text(encoding="utf-8")):
        print(item)


if __name__ == "__main__":
    inspecionar_tribunal()
    inspecionar_pagamentos()
    inspecionar_hub_e_apresentacoes()

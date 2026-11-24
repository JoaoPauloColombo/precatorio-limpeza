"""Uso: python -m limpeza [pasta_dados] [pasta_saida]"""
import sys
from pathlib import Path

from limpeza.pipeline import limpar
from limpeza.relatorio import gravar

RAIZ = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    dados = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "dados"
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "saida"
    resultado = limpar(dados)
    gravar(resultado, saida)
    duvidas = sum(1 for o in resultado.ocorrencias if o.categoria == "duvida")
    print(f"Pronto. Arquivos gravados em {saida}")
    print(f"{duvidas} ocorrência(s) em dúvida: veja {saida / 'relatorio.md'}")

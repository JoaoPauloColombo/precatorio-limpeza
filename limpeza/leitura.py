"""Leitura dos arquivos como vieram. Nunca escreve nos originais."""
import csv
import io
import json
from pathlib import Path


def ler_texto(caminho):
    """Lê o arquivo em UTF-8; se não for, tenta Windows-1252 (Excel) e avisa."""
    bruto = Path(caminho).read_bytes()
    try:
        return bruto.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return bruto.decode("cp1252"), "cp1252 (não era UTF-8)"


def ler_csv(caminho):
    """Devolve (linhas, codificação). Cada linha é um dict com a chave '_linha'."""
    texto, codificacao = ler_texto(caminho)
    primeira = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primeira.count(";") > primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=separador)
    linhas = []
    for numero, linha in enumerate(leitor, start=2):  # linha 1 é o cabeçalho
        linha["_linha"] = numero
        linhas.append(linha)
    return linhas, codificacao


def ler_json(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))

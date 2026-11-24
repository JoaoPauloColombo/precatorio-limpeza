"""Junta tudo: lê os 4 arquivos, corrige o que dá, separa o que não dá.

Regra geral: na dúvida, NÃO entra na base. Fica registrado em Ocorrencia
para a operação decidir (ver docs/DIAGNOSTICO.md).
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from limpeza.leitura import ler_csv, ler_json
from limpeza.normalizar import (
    calcular_prazo, converter_data, converter_valor, data_em_utc,
    formatar_processo, normalizar_ente, normalizar_processo,
)

CORRIGIDO, DESCARTADO, DUVIDA = "corrigido", "descartado", "duvida"


@dataclass
class Ocorrencia:
    categoria: str  # corrigido, descartado ou duvida
    arquivo: str
    registro: str   # onde está (linha ou evento)
    motivo: str


@dataclass
class Resultado:
    precatorios: list
    pagamentos: list
    ocorrencias: list


def montar_precatorios(tribunal, hub, apresentacoes, ocorrencias):
    """Une as 3 fontes pelo número do processo (20 dígitos)."""
    fontes = defaultdict(dict)

    def guardar(nome_fonte, arquivo, linha_ou_item, bruto):
        try:
            chave = normalizar_processo(bruto["processo"])
        except ValueError as erro:
            ocorrencias.append(Ocorrencia(DESCARTADO, arquivo, linha_ou_item, str(erro)))
            return
        if "valor_face" in bruto:
            try:
                converter_valor(bruto["valor_face"])
            except ValueError as erro:  # linha ruim não derruba o resto da limpeza
                ocorrencias.append(Ocorrencia(DUVIDA, arquivo, linha_ou_item,
                                              f"{erro}; linha fora da base"))
                return
        if bruto["processo"] != formatar_processo(chave):
            ocorrencias.append(Ocorrencia(
                CORRIGIDO, arquivo, linha_ou_item,
                f"processo '{bruto['processo']}' reescrito como {formatar_processo(chave)}"))
        fontes[chave][nome_fonte] = bruto

    for linha in tribunal:
        guardar("tribunal", "tribunal.csv", f"linha {linha['_linha']}",
                {"processo": linha["numero_processo"], "ente": linha["ente_devedor"],
                 "valor_face": linha["valor_face"]})
    for linha in hub:
        guardar("hub", "hub.csv", f"linha {linha['_linha']}", linha)
    for item, apresentacao in enumerate(apresentacoes, start=1):
        guardar("apresentacao", "apresentacoes.json", f"item {item}", apresentacao)

    resultado = []
    for chave in sorted(fontes):
        if not (fontes[chave].get("tribunal") or fontes[chave].get("hub")):
            ocorrencias.append(Ocorrencia(
                DUVIDA, "apresentacoes.json", formatar_processo(chave),
                "tem data de apresentação mas não existe no tribunal nem no hub"))
            continue
        resultado.append(_unir_um_precatorio(chave, fontes[chave], ocorrencias))
    return resultado


def _unir_um_precatorio(chave, fonte, ocorrencias):
    numero = formatar_processo(chave)
    tribunal, hub, apres = fonte.get("tribunal"), fonte.get("hub"), fonte.get("apresentacao")
    duvidas = []

    # Tribunal é a fonte oficial; o hub só entra quando o tribunal não lista o processo.
    base = tribunal or hub
    ente = base["ente"]
    valor_face = converter_valor(base["valor_face"])
    origem = "tribunal+hub" if tribunal and hub else ("so_tribunal" if tribunal else "so_hub")

    if origem == "so_hub":
        duvidas.append("processo não consta no tribunal.csv")
    if origem == "so_tribunal":
        duvidas.append("processo não consta no hub.csv")
    if tribunal and hub:
        if normalizar_ente(tribunal["ente"]) != normalizar_ente(hub["ente"]):
            duvidas.append(f"ente diverge: tribunal='{tribunal['ente']}' hub='{hub['ente']}'")
        elif tribunal["ente"] != hub["ente"]:
            ocorrencias.append(Ocorrencia(
                CORRIGIDO, "hub.csv", numero,
                f"ente '{hub['ente']}' padronizado como '{tribunal['ente']}' (grafia do tribunal)"))
        valor_hub = converter_valor(hub["valor_face"])
        if valor_hub != valor_face:
            duvidas.append(f"valor_face diverge: tribunal={valor_face} hub={valor_hub}")

    apresentado_em, prazo = None, None
    if apres is None:
        duvidas.append("sem data de apresentação em apresentacoes.json")
    else:
        texto = apres["apresentado_em"]
        apresentado_em = converter_data(texto)
        prazo = calcular_prazo(apresentado_em)
        if calcular_prazo(data_em_utc(texto)) != prazo:
            duvidas.append(f"prazo depende do fuso: '{texto}' é dia {apresentado_em} em Brasília "
                           f"e dia {data_em_utc(texto)} em UTC; usado Brasília")
        if hub and hub.get("prazo_pagamento") and str(prazo) != hub["prazo_pagamento"]:
            ocorrencias.append(Ocorrencia(
                CORRIGIDO, "hub.csv", numero,
                f"prazo_pagamento {hub['prazo_pagamento']} recalculado para {prazo} "
                f"(apresentado em {apresentado_em})"))

    for motivo in duvidas:
        ocorrencias.append(Ocorrencia(DUVIDA, "precatorios", numero, motivo))

    return {"chave": chave, "numero_processo": numero, "ente_devedor": ente,
            "valor_face": valor_face, "apresentado_em": apresentado_em,
            "prazo_pagamento": prazo, "origem": origem,
            "situacao": "duvida" if duvidas else "ok"}



def montar_pagamentos(eventos, precatorios, ocorrencias):
    """Aceita só evento completo, sem repetição e ligado a um precatório conhecido."""
    por_processo = {p["chave"]: p for p in precatorios}
    lidos = []
    for item, bruto in enumerate(eventos, start=1):
        evento = _ler_evento(item, bruto, ocorrencias)
        if evento:
            lidos.append(evento)

    aceitos = []
    for evento in _resolver_repetidos(lidos, ocorrencias):
        onde = f"evento {evento['evento_id']} (item {evento['item']})"
        precatorio = por_processo.get(evento["chave"])
        if precatorio is None:
            ocorrencias.append(Ocorrencia(
                DUVIDA, "pagamentos.json", onde,
                "processo não existe em nenhum arquivo de precatórios; fora dos totais"))
            continue
        for correcao in evento["correcoes"]:
            ocorrencias.append(Ocorrencia(CORRIGIDO, "pagamentos.json", onde, correcao))
        alerta = ""
        apresentado = precatorio["apresentado_em"]
        if apresentado and evento["pago_em"] < apresentado:
            alerta = f"pago em {evento['pago_em']}, antes da apresentação ({apresentado})"
            ocorrencias.append(Ocorrencia(DUVIDA, "pagamentos.json", onde,
                                          alerta + "; mantido nos totais, confirmar"))
        aceitos.append({**evento, "numero_processo": precatorio["numero_processo"],
                        "alerta": alerta})
    return aceitos


def _ler_evento(item, bruto, ocorrencias):
    """Converte um evento do JSON. Devolve None se não puder ser usado."""
    evento_id = bruto.get("evento_id") or ""
    onde = f"evento {evento_id or '(sem id)'} (item {item})"

    def recusar(categoria, motivo):
        ocorrencias.append(Ocorrencia(categoria, "pagamentos.json", onde, motivo))

    correcoes = []  # só viram ocorrência se o evento for realmente aceito

    if not evento_id:
        recusar(DESCARTADO, "evento sem evento_id")
        return None
    if bruto.get("tipo") not in ("pagamento", "estorno"):
        recusar(DESCARTADO, f"tipo '{bruto.get('tipo')}' desconhecido")
        return None
    try:
        chave = normalizar_processo(bruto.get("processo"))
    except ValueError as erro:
        recusar(DUVIDA, f"{erro}; não dá para ligar a um precatório")
        return None
    try:
        valor = converter_valor(bruto.get("valor"))
        pago_em = converter_data(bruto.get("data_pagamento"))
    except ValueError as erro:
        recusar(DUVIDA, str(erro))
        return None
    if valor <= 0:
        recusar(DUVIDA, f"valor {valor} não é positivo (estorno deve vir com tipo 'estorno')")
        return None

    if bruto["processo"] != formatar_processo(chave):
        correcoes.append(f"processo '{bruto['processo']}' reescrito como {formatar_processo(chave)}")
    if isinstance(bruto["valor"], str):
        correcoes.append(f"valor '{bruto['valor']}' convertido para {valor}")
    if bruto["data_pagamento"] != str(pago_em):
        correcoes.append(f"data '{bruto['data_pagamento']}' convertida para {pago_em}")

    return {"item": item, "evento_id": evento_id, "chave": chave, "tipo": bruto["tipo"],
            "valor": valor, "pago_em": pago_em, "atualizado_em": bruto["atualizado_em"],
            "correcoes": correcoes}


def _resolver_repetidos(eventos, ocorrencias):
    """Mesmo evento_id: igual -> ignora a cópia; versão mais nova -> fica a nova."""
    por_id = defaultdict(list)
    for evento in eventos:
        por_id[evento["evento_id"]].append(evento)

    escolhidos = []
    for evento_id, grupo in por_id.items():
        grupo.sort(key=lambda e: (e["atualizado_em"], e["item"]))
        escolhido = grupo[-1]
        for outro in grupo[:-1]:
            onde = f"evento {evento_id} (item {outro['item']})"
            if _mesmo_conteudo(outro, escolhido):
                ocorrencias.append(Ocorrencia(DESCARTADO, "pagamentos.json", onde,
                                              f"cópia exata do item {escolhido['item']}"))
            elif outro["atualizado_em"] == escolhido["atualizado_em"]:
                ocorrencias.append(Ocorrencia(
                    DUVIDA, "pagamentos.json", onde,
                    "mesmo evento_id e mesmo atualizado_em com conteúdo diferente; evento fora dos totais"))
                escolhido = None
                break
            else:
                ocorrencias.append(Ocorrencia(
                    DESCARTADO, "pagamentos.json", onde,
                    f"versão antiga (valor {outro['valor']}), substituída pelo item "
                    f"{escolhido['item']} (valor {escolhido['valor']}, atualizado_em mais recente)"))
        if escolhido:
            escolhidos.append(escolhido)
    return sorted(escolhidos, key=lambda e: e["item"])


def _mesmo_conteudo(a, b):
    campos = ("chave", "tipo", "valor", "pago_em", "atualizado_em")
    return all(a[c] == b[c] for c in campos)



def total_pago(pagamentos, numero_processo):
    """Pagamentos menos estornos."""
    total = Decimal("0.00")
    for p in pagamentos:
        if p["numero_processo"] == numero_processo:
            total += p["valor"] if p["tipo"] == "pagamento" else -p["valor"]
    return total


def limpar(pasta_dados):
    ocorrencias = []
    tribunal, cod_tribunal = ler_csv(pasta_dados / "tribunal.csv")
    hub, _ = ler_csv(pasta_dados / "hub.csv")
    if cod_tribunal != "utf-8":
        ocorrencias.append(Ocorrencia(
            CORRIGIDO, "tribunal.csv", "arquivo",
            f"codificação lida como {cod_tribunal}; a documentação diz UTF-8, "
            "e o separador é ';' com valores no formato brasileiro (45.000,00)"))

    precatorios = montar_precatorios(
        tribunal, hub, ler_json(pasta_dados / "apresentacoes.json"), ocorrencias)
    pagamentos = montar_pagamentos(
        ler_json(pasta_dados / "pagamentos.json"), precatorios, ocorrencias)
    for p in precatorios:
        p["total_pago"] = total_pago(pagamentos, p["numero_processo"])
    return Resultado(precatorios, pagamentos, ocorrencias)

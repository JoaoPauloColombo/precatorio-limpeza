"""
Funções pequenas que arrumam um valor por vez.

Todas levantam ValueError com uma frase clara quando o valor não tem
conserto. Quem chama decide se isso é descarte ou dúvida.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

FUSO_BRASILIA = timezone(timedelta(hours=-3))


def normalizar_processo(texto):
    """Devolve o número do processo só com os 20 dígitos (sem máscara)."""
    digitos = re.sub(r"\D", "", texto or "")
    if len(digitos) != 20:
        raise ValueError(f"processo '{texto}' não tem 20 dígitos")
    return digitos


def formatar_processo(digitos):
    """20 dígitos -> NNNNNNN-DD.AAAA.J.TR.OOOO (padrão CNJ)."""
    d = digitos
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"


def converter_valor(valor):
    """Aceita 15000, 15000.5, '2.500,50' ou '2500.50'. Devolve Decimal com 2 casas."""
    if valor is None or isinstance(valor, bool):
        raise ValueError("valor ausente")
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:  
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"valor '{valor}' não é um número")
    if not numero.is_finite():
        raise ValueError(f"valor '{valor}' não é um número")
    if numero != numero.quantize(Decimal("0.01")):
        raise ValueError(f"valor '{valor}' tem mais de 2 casas decimais")
    return numero.quantize(Decimal("0.01"))


def _ler_data_hora(texto):
    """Lê 'AAAA-MM-DD', 'DD/MM/AAAA' ou data com hora. Devolve (data_ou_datetime)."""
    texto = str(texto).strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", texto):
        dia, mes, ano = texto.split("/")
        return date(int(ano), int(mes), int(dia))
    
    texto = re.sub(r"Z$", "+00:00", texto)
    try:
        if len(texto) == 10:
            return date.fromisoformat(texto)
        return datetime.fromisoformat(texto)
    except ValueError:
        raise ValueError(f"data '{texto}' em formato desconhecido")


def converter_data(texto):
    """Devolve a data (dia no horário de Brasília)."""
    lido = _ler_data_hora(texto)
    if isinstance(lido, datetime):
        if lido.tzinfo is not None:
            lido = lido.astimezone(FUSO_BRASILIA)
        return lido.date()
    return lido


def data_em_utc(texto):
    """Mesma data, mas vista em UTC. Usada só para detectar prazo que depende do fuso."""
    lido = _ler_data_hora(texto)
    if isinstance(lido, datetime) and lido.tzinfo is not None:
        return lido.astimezone(timezone.utc).date()
    return converter_data(texto)


def normalizar_ente(nome):
    """Chave para comparar nomes: sem acento, sem maiúscula, sem espaço extra."""
    sem_acento = unicodedata.normalize("NFKD", nome or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def calcular_prazo(apresentado_em):
    """Até 2 de abril (inclusive): 31/12 do ano seguinte. Depois: 31/12 do ano subsequente."""
    ate_2_de_abril = (apresentado_em.month, apresentado_em.day) <= (4, 2)
    ano = apresentado_em.year + (1 if ate_2_de_abril else 2)
    return date(ano, 12, 31)

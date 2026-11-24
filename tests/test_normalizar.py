import unittest
from datetime import date
from decimal import Decimal

from limpeza.normalizar import (
    calcular_prazo, converter_data, converter_valor, data_em_utc,
    formatar_processo, normalizar_ente, normalizar_processo,
)


class TestProcesso(unittest.TestCase):
    def test_com_e_sem_mascara_dao_a_mesma_chave(self):
        com = normalizar_processo("0023456-21.2020.8.26.0053")
        sem = normalizar_processo("00234562120208260053")
        self.assertEqual(com, sem)

    def test_formatar_volta_para_o_padrao_cnj(self):
        self.assertEqual(formatar_processo("00234562120208260053"),
                         "0023456-21.2020.8.26.0053")

    def test_vazio_ou_curto_e_erro(self):
        for ruim in ("", None, "123", "2.3456E+19"):
            with self.assertRaises(ValueError):
                normalizar_processo(ruim)


class TestValor(unittest.TestCase):
    def test_formatos_aceitos(self):
        self.assertEqual(converter_valor(15000.0), Decimal("15000.00"))
        self.assertEqual(converter_valor(8000), Decimal("8000.00"))
        self.assertEqual(converter_valor("2.500,50"), Decimal("2500.50"))
        self.assertEqual(converter_valor("45.000,00"), Decimal("45000.00"))
        self.assertEqual(converter_valor("2500.50"), Decimal("2500.50"))

    def test_nulo_e_texto_ruim_sao_erro(self):
        for ruim in (None, "abc", "", True, "1,234,5"):
            with self.assertRaises(ValueError):
                converter_valor(ruim)

    def test_mais_de_duas_casas_e_erro(self):
        with self.assertRaises(ValueError):
            converter_valor("10,555")


class TestData(unittest.TestCase):
    def test_formato_brasileiro_e_dia_primeiro(self):
        self.assertEqual(converter_data("10/04/2025"), date(2025, 4, 10))

    def test_iso_simples(self):
        self.assertEqual(converter_data("2024-02-29"), date(2024, 2, 29))

    def test_data_com_hora_usa_o_dia_de_brasilia(self):
        self.assertEqual(converter_data("2025-04-02T23:30:00-03:00"), date(2025, 4, 2))
        # 01:00 UTC ainda é noite do dia anterior em Brasília
        self.assertEqual(converter_data("2025-04-03T01:00:00Z"), date(2025, 4, 2))

    def test_utc_mostra_o_outro_dia(self):
        self.assertEqual(data_em_utc("2025-04-02T23:30:00-03:00"), date(2025, 4, 3))

    def test_formato_estranho_e_erro(self):
        with self.assertRaises(ValueError):
            converter_data("ontem")


class TestPrazo(unittest.TestCase):
    """Regra mais arriscada do projeto: errar muda a prioridade da carteira."""

    def test_2_de_abril_ainda_conta_como_ate(self):
        self.assertEqual(calcular_prazo(date(2025, 4, 2)), date(2026, 12, 31))

    def test_3_de_abril_ja_passou_do_limite(self):
        self.assertEqual(calcular_prazo(date(2025, 4, 3)), date(2027, 12, 31))

    def test_inicio_e_fim_do_ano(self):
        self.assertEqual(calcular_prazo(date(2025, 1, 1)), date(2026, 12, 31))
        self.assertEqual(calcular_prazo(date(2023, 12, 31)), date(2025, 12, 31))

    def test_29_de_fevereiro(self):
        self.assertEqual(calcular_prazo(date(2024, 2, 29)), date(2025, 12, 31))


class TestEnte(unittest.TestCase):
    def test_maiuscula_e_acento_nao_importam(self):
        self.assertEqual(normalizar_ente("MUNICIPIO DE SAO PAULO"),
                         normalizar_ente("Município  de São Paulo "))

    def test_entes_diferentes_continuam_diferentes(self):
        self.assertNotEqual(normalizar_ente("União"), normalizar_ente("Município de Santos"))


if __name__ == "__main__":
    unittest.main()

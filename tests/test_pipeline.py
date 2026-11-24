"""Testes das regras mais arriscadas: dinheiro (duplicado, estorno) e prazo."""
import hashlib
import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from limpeza.pipeline import DESCARTADO, DUVIDA, limpar, montar_pagamentos

DADOS = Path(__file__).resolve().parent.parent / "dados"


def precatorio(chave="00123451020198260053", apresentado=date(2025, 4, 2)):
    return {"chave": chave, "numero_processo": "0012345-10.2019.8.26.0053",
            "apresentado_em": apresentado}


def evento(evento_id="e1", valor=100, tipo="pagamento", atualizado="2025-05-01T10:00:00-03:00",
           processo="0012345-10.2019.8.26.0053", data="2025-05-01"):
    return {"evento_id": evento_id, "processo": processo, "valor": valor,
            "data_pagamento": data, "tipo": tipo, "atualizado_em": atualizado}


class TestPagamentos(unittest.TestCase):
    def rodar(self, eventos):
        ocorrencias = []
        aceitos = montar_pagamentos(eventos, [precatorio()], ocorrencias)
        return aceitos, ocorrencias

    def test_evento_repetido_conta_uma_vez(self):
        aceitos, ocorrencias = self.rodar([evento(), evento()])
        self.assertEqual(len(aceitos), 1)
        self.assertEqual(ocorrencias[0].categoria, DESCARTADO)

    def test_versao_mais_nova_vence(self):
        antigo = evento(valor=100, atualizado="2025-05-01T10:00:00-03:00")
        novo = evento(valor=150, atualizado="2025-05-02T10:00:00-03:00")
        aceitos, _ = self.rodar([novo, antigo])  # ordem do arquivo não importa
        self.assertEqual([a["valor"] for a in aceitos], [Decimal("150.00")])

    def test_versoes_diferentes_com_mesma_hora_viram_duvida(self):
        aceitos, ocorrencias = self.rodar([evento(valor=100), evento(valor=150)])
        self.assertEqual(aceitos, [])
        self.assertEqual(ocorrencias[-1].categoria, DUVIDA)

    def test_valor_negativo_ou_nulo_nao_entra(self):
        aceitos, ocorrencias = self.rodar([evento("a", -200), evento("b", None)])
        self.assertEqual(aceitos, [])
        self.assertEqual([o.categoria for o in ocorrencias], [DUVIDA, DUVIDA])

    def test_processo_desconhecido_nao_entra_mas_avisa(self):
        aceitos, ocorrencias = self.rodar([evento(processo="0000001-00.2020.8.26.0001")])
        self.assertEqual(aceitos, [])
        self.assertEqual(ocorrencias[0].categoria, DUVIDA)

    def test_pagamento_antes_da_apresentacao_avisa_mas_conta(self):
        aceitos, ocorrencias = self.rodar([evento(data="2025-03-10")])
        self.assertEqual(len(aceitos), 1)
        self.assertIn("antes da apresentação", aceitos[0]["alerta"])


class TestComOsDadosDoCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultado = limpar(DADOS)
        cls.por_processo = {p["numero_processo"]: p for p in cls.resultado.precatorios}

    def test_estorno_anula_o_pagamento(self):
        self.assertEqual(self.por_processo["0034567-32.2018.8.26.0405"]["total_pago"],
                         Decimal("0.00"))

    def test_total_sem_duplicados_e_com_versao_corrigida(self):
        # ev-001 (15500, versão nova) + ev-002 (2500,50 uma vez só)
        self.assertEqual(self.por_processo["0012345-10.2019.8.26.0053"]["total_pago"],
                         Decimal("18000.50"))

    def test_processo_sem_mascara_soma_no_processo_certo(self):
        # ev-003 (8000) + ev-005 (1200, que veio sem máscara)
        self.assertEqual(self.por_processo["0023456-21.2020.8.26.0053"]["total_pago"],
                         Decimal("9200.00"))

    def test_prazo_do_dia_2_de_abril_e_do_ano_seguinte(self):
        self.assertEqual(self.por_processo["0012345-10.2019.8.26.0053"]["prazo_pagamento"],
                         date(2026, 12, 31))

    def test_prazo_com_fuso_usa_o_dia_de_brasilia(self):
        self.assertEqual(self.por_processo["0056789-54.2017.4.03.6100"]["prazo_pagamento"],
                         date(2026, 12, 31))

    def test_divergencias_entre_hub_e_tribunal_ficam_em_duvida(self):
        self.assertEqual(self.por_processo["0023456-21.2020.8.26.0053"]["situacao"], "duvida")
        self.assertEqual(self.por_processo["0045678-43.2021.5.02.0011"]["situacao"], "duvida")

    def test_nenhum_processo_sumiu(self):
        self.assertEqual(len(self.resultado.precatorios), 6)


class TestArquivosRuins(unittest.TestCase):
    def test_linha_com_valor_invalido_nao_derruba_a_limpeza(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            (pasta / "tribunal.csv").write_text(
                "numero_processo;ente_devedor;valor_face\n"
                "0012345-10.2019.8.26.0053;União;abc\n"
                "0023456-21.2020.8.26.0053;União;1.000,00\n", encoding="utf-8")
            (pasta / "hub.csv").write_text(
                "processo,ente,valor_face,apresentado_em,prazo_pagamento\n", encoding="utf-8")
            (pasta / "apresentacoes.json").write_text("[]", encoding="utf-8")
            (pasta / "pagamentos.json").write_text("[]", encoding="utf-8")
            resultado = limpar(pasta)
        self.assertEqual(len(resultado.precatorios), 1)
        self.assertTrue(any(o.categoria == DUVIDA and "abc" in o.motivo
                            for o in resultado.ocorrencias))


class TestOriginaisIntactos(unittest.TestCase):
    def test_rodar_a_limpeza_nao_altera_os_arquivos(self):
        def hashes():
            return {a.name: hashlib.sha256(a.read_bytes()).hexdigest() for a in DADOS.iterdir()}
        antes = hashes()
        limpar(DADOS)
        self.assertEqual(antes, hashes())


if __name__ == "__main__":
    unittest.main()

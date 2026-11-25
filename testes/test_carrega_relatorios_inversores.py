"""Testes para o carregador de relatorios normalizados PHB e KSTAR."""

import csv
import os
import sqlite3
import sys
import tempfile
import unittest

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PASTA_PROJETO, "app"))
sys.path.insert(0, os.path.join(PASTA_PROJETO, "pipeline"))

import consultas  # noqa: E402
import carrega_relatorios_inversores as carregador  # noqa: E402


PHB_COLUNAS = [
    "ts_local", "ts_utc", "modo_texto", "inversores_ativos", "inversores_total",
    "i_ac_1_a", "i_ac_2_a", "i_ac_3_a", "potencia_w", "energia_intervalo_kwh",
    "temperatura_c", "qualidade", "arquivo",
]
KSTAR_COLUNAS = [
    "ts_local", "ts_utc", "modo", "modo_original", "modo_inferido",
    "pv1_v", "pv2_v", "pv3_v", "pv1_a", "pv2_a", "pv3_a", "pv1_w", "pv2_w",
    "pv3_w", "potencia_w", "energia_total_kwh", "energia_intervalo_kwh",
    "temp_radiador_c", "hora_corrigida", "qualidade", "arquivo",
]


def escrever_csv(pasta, nome, colunas, linhas):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


class TestCarregaRelatoriosInversores(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        consultas.inicializar_schema(self.conn)
        self.pasta = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.pasta.cleanup()
        self.conn.close()

    def test_phb_ajusta_zero_antigo_e_preserva_temperatura(self):
        caminho = escrever_csv(self.pasta.name, "phb.csv", PHB_COLUNAS, [
            {"ts_utc": "2024-12-31 22:00:00", "ts_local": "2024-12-31 19:00:00",
             "inversores_ativos": "0", "potencia_w": "", "energia_intervalo_kwh": "",
             "temperatura_c": "42.5"},
            {"ts_utc": "2024-12-31 22:05:00", "ts_local": "2024-12-31 19:05:00",
             "inversores_ativos": "0", "potencia_w": "150.0", "energia_intervalo_kwh": "0.01",
             "temperatura_c": "43.0"},
            {"ts_utc": "2025-01-01 00:00:00", "ts_local": "2024-12-31 21:00:00",
             "inversores_ativos": "0", "potencia_w": "", "energia_intervalo_kwh": ""},
        ])

        resultado = carregador.carregar_phb(caminho, self.conn)

        self.assertEqual(resultado, {"linhas_lidas": 3, "linhas_inseridas": 3, "linhas_ignoradas": 0})
        registros = self.conn.execute(
            "SELECT inversores_ativos, potencia_w, energia_intervalo_kwh, temperatura_c "
            "FROM phb_leitura ORDER BY ts_utc"
        ).fetchall()
        self.assertEqual(registros, [
            (None, None, None, 42.5),
            (0, 150.0, 0.01, 43.0),
            (0, None, None, None),
        ])

    def test_kstar_converte_flags_booleanas_e_preserva_mppts(self):
        caminho = escrever_csv(self.pasta.name, "kstar.csv", KSTAR_COLUNAS, [{
            "ts_utc": "2022-06-30 19:45:00", "ts_local": "2022-06-30 16:45:00",
            "modo_inferido": "True", "hora_corrigida": "False",
            "pv1_w": "0", "pv2_w": "125.5", "pv3_w": "0",
            "pv1_v": "0", "pv2_v": "340.0", "pv3_v": "0",
            "pv1_a": "0", "pv2_a": "0.37", "pv3_a": "0",
        }])

        resultado = carregador.carregar_kstar(caminho, self.conn)

        self.assertEqual(resultado, {"linhas_lidas": 1, "linhas_inseridas": 1, "linhas_ignoradas": 0})
        self.assertEqual(self.conn.execute(
            "SELECT modo_inferido, hora_corrigida, pv1_w, pv2_w, pv3_w "
            "FROM kstar_leitura"
        ).fetchone(), (1, 0, 0.0, 125.5, 0.0))

    def test_kstar_flags_false_true_viram_zero_um(self):
        caminho = escrever_csv(self.pasta.name, "kstar.csv", KSTAR_COLUNAS, [{
            "ts_utc": "2022-06-30 19:45:00", "ts_local": "2022-06-30 16:45:00",
            "modo_inferido": "False", "hora_corrigida": "True",
        }])

        carregador.carregar_kstar(caminho, self.conn)

        self.assertEqual(self.conn.execute(
            "SELECT modo_inferido, hora_corrigida FROM kstar_leitura"
        ).fetchone(), (0, 1))

    def test_duplicatas_sao_ignoradas_e_contabilizadas(self):
        caminho = escrever_csv(self.pasta.name, "phb.csv", PHB_COLUNAS, [{
            "ts_utc": "2025-01-01 00:00:00", "ts_local": "2024-12-31 21:00:00",
            "potencia_w": "100.0", "arquivo": "relatorio.xlsx",
        }])

        primeiro = carregador.carregar_phb(caminho, self.conn)
        segundo = carregador.carregar_phb(caminho, self.conn)

        self.assertEqual(primeiro, {"linhas_lidas": 1, "linhas_inseridas": 1, "linhas_ignoradas": 0})
        self.assertEqual(segundo, {"linhas_lidas": 1, "linhas_inseridas": 0, "linhas_ignoradas": 1})
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM phb_leitura").fetchone()[0], 1)

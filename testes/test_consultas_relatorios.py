"""Tests for reusable PHB and KSTAR report queries and views."""

import os
import sqlite3
import sys
import unittest

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PASTA_PROJETO, "app"))

import consultas  # noqa: E402


class BancoRelatorios(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        consultas.inicializar_schema(self.conn)

    def tearDown(self):
        self.conn.close()


class TestConsultasPHB(BancoRelatorios):
    def inserir_dados(self):
        self.conn.executemany(
            """INSERT INTO phb_leitura
               (ts_utc, ts_local, potencia_w, energia_intervalo_kwh,
                temperatura_c, inversores_ativos)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                ("2025-09-01 03:00:00", "2025-09-01 00:00:00", 100.0, 0.1, 20.0, 3),
                ("2025-09-01 03:10:00", "2025-09-01 00:10:00", 200.0, 0.2, 22.0, 4),
                ("2025-09-02 03:15:00", "2025-09-02 00:15:00", 150.0, 0.3, 24.0, 4),
            ],
        )
        self.conn.commit()

    def test_banco_vazio_retorna_resultados_consistentes(self):
        self.assertEqual(consultas.datas_phb(self.conn), [])
        periodo = consultas.phb_periodo(self.conn, "2025-09-01", "2025-09-30")
        self.assertTrue(periodo.empty)
        self.assertEqual(
            consultas.resumo_phb(self.conn),
            {"primeira_data": None, "ultima_data": None, "total_registros": 0},
        )

    def test_datas_phb_ordenadas(self):
        self.inserir_dados()
        self.assertEqual(consultas.datas_phb(self.conn), ["2025-09-01", "2025-09-02"])

    def test_phb_periodo_filtra_datas_inclusivas_e_ordena(self):
        self.inserir_dados()
        df = consultas.phb_periodo(self.conn, "2025-09-01", "2025-09-01")
        self.assertEqual(len(df), 2)
        self.assertEqual(df["ts_local"].dt.strftime("%H:%M:%S").tolist(), ["00:00:00", "00:10:00"])

    def test_view_e_resumo_phb_agregam_por_data_local(self):
        self.inserir_dados()
        dia = self.conn.execute(
            "SELECT * FROM vw_phb_resumo_diario WHERE data = '2025-09-01'"
        ).fetchone()
        self.assertEqual(dia[:2], ("2025-09-01", 2))
        for atual, esperado in zip(dia[2:], (0.3, 200.0, 150.0, 21.0, 3.5)):
            self.assertAlmostEqual(atual, esperado)
        self.assertEqual(
            consultas.resumo_phb(self.conn),
            {"primeira_data": "2025-09-01", "ultima_data": "2025-09-02", "total_registros": 3},
        )


class TestConsultasKSTAR(BancoRelatorios):
    def inserir_dados(self):
        self.conn.executemany(
            """INSERT INTO kstar_leitura
               (ts_utc, ts_local, potencia_w, energia_intervalo_kwh,
                pv1_w, pv2_w, pv3_w, temp_radiador_c, hora_corrigida, modo_inferido)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("2025-09-01 03:01:00", "2025-09-01 00:01:00", 100.0, 0.01, 10.0, 20.0, 30.0, 30.0, 1, 0),
                ("2025-09-01 03:07:00", "2025-09-01 00:07:00", 200.0, 0.02, 11.0, 21.0, 31.0, 32.0, 0, 1),
                ("2025-09-01 03:14:00", "2025-09-01 00:14:00", 300.0, 0.03, 12.0, 22.0, 32.0, 34.0, 1, 0),
                ("2025-09-01 03:16:00", "2025-09-01 00:16:00", 400.0, 0.04, 13.0, 23.0, 33.0, 36.0, 0, 0),
                ("2025-09-02 04:00:00", "2025-09-02 01:00:00", 500.0, 0.05, 14.0, 24.0, 34.0, 38.0, 1, 0),
            ],
        )
        self.conn.commit()

    def test_banco_vazio_retorna_resultados_consistentes(self):
        self.assertEqual(consultas.datas_kstar(self.conn), [])
        self.assertTrue(consultas.kstar_periodo(self.conn, "2025-09-01", "2025-09-30").empty)
        self.assertEqual(
            consultas.resumo_kstar(self.conn),
            {"primeira_data": None, "ultima_data": None, "total_registros": 0,
             "energia_intervalo_kwh": 0.0, "pct_hora_corrigida": 0.0},
        )

    def test_datas_kstar_ordenadas_e_periodo_inclusivo(self):
        self.inserir_dados()
        self.assertEqual(consultas.datas_kstar(self.conn), ["2025-09-01", "2025-09-02"])
        df = consultas.kstar_periodo(self.conn, "2025-09-01", "2025-09-01")
        self.assertEqual(len(df), 4)
        self.assertEqual(df["ts_local"].dt.strftime("%H:%M:%S").tolist(),
                         ["00:01:00", "00:07:00", "00:14:00", "00:16:00"])

    def test_view_resumo_e_resumo_kstar(self):
        self.inserir_dados()
        dia = self.conn.execute(
            "SELECT * FROM vw_kstar_resumo_diario WHERE data = '2025-09-01'"
        ).fetchone()
        self.assertEqual(dia, ("2025-09-01", 4, 0.1, 400.0, 13.0, 23.0, 33.0, 2))
        resumo = consultas.resumo_kstar(self.conn)
        self.assertEqual((resumo["primeira_data"], resumo["ultima_data"], resumo["total_registros"]),
                         ("2025-09-01", "2025-09-02", 5))
        self.assertAlmostEqual(resumo["energia_intervalo_kwh"], 0.15)
        self.assertAlmostEqual(resumo["pct_hora_corrigida"], 60.0)

    def test_view_kstar_15min_agrega_no_balde_local_correto(self):
        self.inserir_dados()
        linhas = self.conn.execute(
            "SELECT timestamp_15min, registros, energia_intervalo_kwh, potencia_media_w, "
            "potencia_max_w, pv1_max_w, hora_corrigida "
            "FROM vw_kstar_15min ORDER BY timestamp_15min"
        ).fetchall()
        self.assertEqual(len(linhas), 3)
        self.assertEqual(linhas[0][0:2], ("2025-09-01 00:00:00", 3))
        for atual, esperado in zip(linhas[0][2:], (0.06, 200.0, 300.0, 12.0, 2)):
            self.assertAlmostEqual(atual, esperado)
        self.assertEqual(linhas[1][0:2], ("2025-09-01 00:15:00", 1))
        self.assertEqual(linhas[2][0:2], ("2025-09-02 01:00:00", 1))

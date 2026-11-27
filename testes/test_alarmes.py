"""Tests for the idempotent alarm event generators."""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "app"))

import alarmes  # noqa: E402
import consultas  # noqa: E402


class TestGeracaoAlarmes(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.conn = sqlite3.connect(os.path.join(self.tempdir, "alarmes.db"))
        consultas.inicializar_schema(self.conn)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def inserir_phb(self, ts, qualidade, arquivo="phb.xlsx"):
        self.conn.execute(
            """INSERT INTO phb_leitura
               (ts_utc, ts_local, potencia_w, energia_intervalo_kwh, qualidade, arquivo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ts, ts, 100.0, 0.1, qualidade, arquivo),
        )

    def inserir_kstar(self, ts, corrigida, qualidade="ok"):
        self.conn.execute(
            """INSERT INTO kstar_leitura (ts_utc, ts_local, hora_corrigida, qualidade)
               VALUES (?, ?, ?, ?)""",
            (ts, ts, corrigida, qualidade),
        )

    def test_meteorologia_uma_lacuna_gera_um_evento_utc_e_idempotente(self):
        self.conn.executemany(
            "INSERT INTO meteorologia_15min (timestamp_15min) VALUES (?)",
            [
                ("2025-01-01 08:00:00",),
                ("2025-01-01 08:15:00",),
                ("2025-01-01 08:45:00",),
            ],
        )
        self.conn.commit()

        self.assertEqual(alarmes.gerar_alarmes_meteorologia(self.conn), 1)
        evento = self.conn.execute(
            "SELECT timestamp_evento, origem, codigo, severidade, referencia "
            "FROM historico_alarmes"
        ).fetchone()
        self.assertEqual(evento, (
            "2025-01-01 11:30:00", "meteorologia", "lacuna_dados", "aviso",
            "2025-01-01 11:15:00/2025-01-01 11:45:00",
        ))
        self.assertEqual(alarmes.gerar_alarmes_meteorologia(self.conn), 0)
        self.assertEqual(consultas.resumo_alarmes(self.conn)["total"], 1)

    def test_phb_gera_um_evento_por_dia_marcado_e_idempotente(self):
        self.inserir_phb("2025-06-29 08:45:00", "energia_diverge_da_potencia")
        self.inserir_phb("2025-06-29 09:00:00", "energia_diverge_da_potencia", "phb-2.xlsx")
        self.inserir_phb("2025-06-30 09:10:00", "energia_diverge_da_potencia")
        self.inserir_phb("2025-07-01 09:10:00", "ok")
        self.conn.commit()

        self.assertEqual(alarmes.gerar_alarmes_phb(self.conn), 2)
        eventos = self.conn.execute(
            "SELECT timestamp_evento, origem, codigo, severidade, referencia "
            "FROM historico_alarmes ORDER BY timestamp_evento"
        ).fetchall()
        self.assertEqual(eventos, [
            ("2025-06-29 08:45:00", "phb", "energia_diverge_da_potencia", "aviso", "2025-06-29"),
            ("2025-06-30 09:10:00", "phb", "energia_diverge_da_potencia", "aviso", "2025-06-30"),
        ])
        self.assertEqual(alarmes.gerar_alarmes_phb(self.conn), 0)

    def test_kstar_resume_amostras_corrigidas_em_um_evento(self):
        self.inserir_kstar("2025-08-01 08:00:00", 1, "hora_corrigida_+3h")
        self.inserir_kstar("2025-08-01 08:05:00", 1, "hora_corrigida_+3h")
        self.inserir_kstar("2025-08-10 09:00:00", 1, "hora_corrigida_+3h")
        self.inserir_kstar("2025-08-11 09:00:00", 0)
        self.conn.commit()

        self.assertEqual(alarmes.gerar_alarmes_kstar(self.conn), 1)
        evento = self.conn.execute(
            "SELECT timestamp_evento, origem, codigo, severidade, referencia, descricao "
            "FROM historico_alarmes"
        ).fetchone()
        self.assertEqual(evento[:5], (
            "2025-08-01 08:00:00", "kstar", "hora_corrigida", "informacao",
            "2025-08-01 08:00:00/2025-08-10 09:00:00",
        ))
        self.assertIn("3 amostras", evento[5])
        self.assertEqual(alarmes.gerar_alarmes_kstar(self.conn), 0)
        self.assertEqual(consultas.resumo_alarmes(self.conn)["total"], 1)

    def test_gerar_alarmes_chama_todos_e_segunda_execucao_nao_duplica(self):
        self.conn.executemany(
            "INSERT INTO meteorologia_15min (timestamp_15min) VALUES (?)",
            [("2025-01-01 00:00:00",), ("2025-01-01 00:30:00",)],
        )
        self.inserir_phb("2025-06-29 08:45:00", "energia_diverge_da_potencia")
        self.inserir_kstar("2025-08-01 08:00:00", 1, "hora_corrigida_+3h")
        self.conn.commit()

        self.assertEqual(
            alarmes.gerar_alarmes(self.conn),
            {"meteorologia": 1, "phb": 1, "kstar": 1, "total": 3},
        )
        self.assertEqual(
            alarmes.gerar_alarmes(self.conn),
            {"meteorologia": 0, "phb": 0, "kstar": 0, "total": 0},
        )
        self.assertEqual(consultas.resumo_alarmes(self.conn)["total"], 3)
        self.assertEqual(consultas.alarmes_por_origem(self.conn)["quantidade"].sum(), 3)

    def test_geradores_sem_fontes_com_eventos_nao_lancam_excecao(self):
        self.assertEqual(alarmes.gerar_alarmes(self.conn), {
            "meteorologia": 0, "phb": 0, "kstar": 0, "total": 0,
        })
        self.assertEqual(consultas.resumo_alarmes(self.conn)["total"], 0)

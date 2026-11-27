"""App-level checks for the History of Alarms dashboard page."""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "app"))

import banco  # noqa: E402
import consultas  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402


class TestDashboardHistoricoAlarmes(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tempdir, "dashboard.db")
        self.db_original = banco.DB_PATH
        banco.DB_PATH = self.db_path
        self.conn = sqlite3.connect(self.db_path)
        consultas.inicializar_schema(self.conn)
        # The default dashboard section loads these legacy tables before navigation.
        self.conn.execute("CREATE TABLE historico_anual_inversores (inversor TEXT)")
        self.conn.execute("CREATE TABLE historico_anual_usina (ano INTEGER)")
        self.conn.commit()
        st.cache_data.clear()

    def tearDown(self):
        self.conn.close()
        banco.DB_PATH = self.db_original
        st.cache_data.clear()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def abrir_pagina(self):
        app = AppTest.from_file(
            os.path.join(PROJECT, "app", "dashboard.py"), default_timeout=45
        ).run()
        app.radio[0].set_value("Histórico de Alarmes").run()
        return app

    def inserir_evento(self, timestamp, origem, codigo, severidade, titulo, referencia):
        self.conn.execute(
            """INSERT INTO historico_alarmes
               (timestamp_evento, origem, codigo, severidade, titulo, referencia, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, origem, codigo, severidade, titulo, referencia, timestamp),
        )
        self.conn.commit()

    def tabela_eventos(self, app):
        return next(
            tabela for tabela in app.dataframe
            if "origem" in tabela.value.columns and "referencia" in tabela.value.columns
        )

    def test_banco_vazio_mostra_mensagem_sem_excecao(self):
        app = self.abrir_pagina()
        self.assertFalse(app.exception)
        self.assertTrue(any(item.value == "Nenhum alarme registrado." for item in app.info))
        metricas = {item.label: item.value for item in app.metric}
        self.assertEqual(metricas["Total de alarmes"], "0")

    def test_banco_com_amostras_mostra_cards_tabela_e_filtros(self):
        self.inserir_evento(
            "2026-11-24 12:00:00", "kstar", "hora_corrigida", "informacao",
            "Hora corrigida", "2026-11-24/2026-11-25",
        )
        self.inserir_evento(
            "2026-11-25 12:00:00", "meteorologia", "lacuna_dados", "aviso",
            "Lacuna detectada", "2026-11-25T12:00/12:30",
        )
        self.inserir_evento(
            "2026-11-26 12:00:00", "phb", "energia_diverge_da_potencia", "erro",
            "Divergência PHB", "2026-11-26",
        )
        app = self.abrir_pagina()
        self.assertFalse(app.exception)
        metricas = {item.label: item.value for item in app.metric}
        self.assertEqual(metricas["Total de alarmes"], "3")
        self.assertEqual(metricas["Informação"], "1")
        self.assertEqual(metricas["Aviso"], "1")
        self.assertEqual(metricas["Erro"], "1")
        self.assertEqual(metricas["Crítico"], "0")
        tabela_origens = next(
            item.value for item in app.dataframe
            if item.value.columns.tolist() == ["Origem", "Quantidade"]
        )
        contagem_origens = dict(zip(tabela_origens["Origem"], tabela_origens["Quantidade"]))
        self.assertEqual(contagem_origens["Meteorologia"], 1)
        self.assertEqual(contagem_origens["PHB"], 1)
        self.assertEqual(contagem_origens["KSTAR"], 1)
        tabela_severidades = next(
            item.value for item in app.dataframe
            if item.value.columns.tolist() == ["Severidade", "Quantidade"]
        )
        contagem_severidades = dict(zip(
            tabela_severidades["Severidade"], tabela_severidades["Quantidade"]
        ))
        self.assertEqual(contagem_severidades["Informação"], 1)
        self.assertEqual(contagem_severidades["Aviso"], 1)
        self.assertEqual(contagem_severidades["Erro"], 1)
        eventos = self.tabela_eventos(app).value
        self.assertEqual(len(eventos), 3)
        self.assertEqual(
            eventos.columns.tolist(),
            ["timestamp_evento (UTC−3)", "origem", "codigo", "severidade", "titulo", "referencia"],
        )
        self.assertEqual(eventos.iloc[0]["origem"], "phb")

        app.date_input[0].set_value(date(2026, 11, 26)).run()
        app.date_input[1].set_value(date(2026, 11, 26)).run()
        self.assertFalse(app.exception)
        eventos_filtrados = self.tabela_eventos(app).value
        self.assertEqual(eventos_filtrados["origem"].tolist(), ["phb"])

        app.selectbox[0].select("Todas").run()
        self.assertFalse(app.exception)
        eventos_filtrados = self.tabela_eventos(app).value
        self.assertEqual(eventos_filtrados["origem"].tolist(), ["phb"])

        app.selectbox[1].select("Aviso").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Nenhum alarme encontrado" in item.value for item in app.info))
        self.assertFalse(any(
            "referencia" in tabela.value.columns and "origem" in tabela.value.columns
            for tabela in app.dataframe
        ))


if __name__ == "__main__":
    unittest.main()

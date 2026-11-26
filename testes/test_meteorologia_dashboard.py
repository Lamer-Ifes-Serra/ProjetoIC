"""Regression tests for standalone meteorological dashboard queries."""

import os
import sqlite3
import sys
import unittest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "app"))

import catalogo_meteorologia as catalogo  # noqa: E402
import consultas  # noqa: E402


class TestConsultasMeteorologiaDashboard(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        consultas.inicializar_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def inserir_dados(self):
        self.conn.executemany(
            """INSERT INTO meteorologia_15min
               (timestamp_15min, temperatura_c, ghi_lppyra02_w_m2)
               VALUES (?, ?, ?)""",
            [
                ("2025-09-01 00:00:00", 10.0, 100.0),
                ("2025-09-01 00:15:00", 20.0, 110.0),
                ("2025-09-01 00:30:00", None, 120.0),
                ("2025-09-01 00:45:00", 30.0, 130.0),
                ("2025-09-02 00:00:00", 40.0, 140.0),
            ],
        )
        self.conn.commit()

    def test_datas_meteorologia_ordenadas(self):
        self.inserir_dados()
        self.assertEqual(
            consultas.datas_meteorologia(self.conn),
            ["2025-09-01", "2025-09-02"],
        )

    def test_meteorologia_periodo_inclusivo_retorna_todas_as_colunas(self):
        self.inserir_dados()
        df = consultas.meteorologia_periodo(self.conn, "2025-09-01", "2025-09-01")
        self.assertEqual(len(df), 4)
        self.assertEqual(
            df["timestamp_15min"].dt.strftime("%Y-%m-%d").unique().tolist(),
            ["2025-09-01"],
        )
        colunas = [row[1] for row in self.conn.execute("PRAGMA table_info(meteorologia_15min)")]
        self.assertEqual(df.columns.tolist(), colunas)

    def inserir_dados_agregacao(self):
        self.conn.executemany(
            """INSERT INTO meteorologia_15min
               (timestamp_15min, temperatura_c, ghi_lppyra02_w_m2)
               VALUES (?, ?, ?)""",
            [
                ("2025-09-01 00:00:00", 10.0, 100.0),
                ("2025-09-01 00:15:00", 20.0, 200.0),
                ("2025-09-02 00:00:00", 30.0, 300.0),
                ("2025-10-01 00:00:00", 40.0, 400.0),
                ("2026-01-01 00:00:00", 50.0, 500.0),
            ],
        )
        self.conn.commit()

    def test_meteorologia_agregada_dia_preserva_linhas_e_filtro(self):
        self.inserir_dados_agregacao()
        df = consultas.meteorologia_agregada(
            self.conn, "temperatura_c", "Dia", "2025-09-01", "2025-09-01"
        )
        self.assertEqual(len(df), 2)
        self.assertEqual(df["temperatura_c"].tolist(), [10.0, 20.0])
        self.assertEqual(
            df["timestamp_15min"].dt.strftime("%H:%M").tolist(), ["00:00", "00:15"]
        )

    def test_meteorologia_agregada_mes_calcula_medias_diarias_ordenadas(self):
        self.inserir_dados_agregacao()
        df = consultas.meteorologia_agregada(
            self.conn, "temperatura_c", "Mês", "2025-09-01", "2026-01-01"
        )
        self.assertEqual(len(df), 4)
        self.assertEqual(df["temperatura_c"].tolist(), [15.0, 30.0, 40.0, 50.0])
        self.assertEqual(
            df["timestamp_15min"].dt.strftime("%Y-%m-%d").tolist(),
            ["2025-09-01", "2025-09-02", "2025-10-01", "2026-01-01"],
        )

    def test_meteorologia_agregada_ano_calcula_medias_mensais_ordenadas(self):
        self.inserir_dados_agregacao()
        df = consultas.meteorologia_agregada(
            self.conn, "temperatura_c", "Ano", "2025-09-01", "2026-01-01"
        )
        self.assertEqual(len(df), 3)
        self.assertEqual(df["temperatura_c"].tolist(), [20.0, 40.0, 50.0])
        self.assertEqual(
            df["timestamp_15min"].dt.strftime("%Y-%m-%d").tolist(),
            ["2025-09-01", "2025-10-01", "2026-01-01"],
        )

    def test_meteorologia_agregada_todos_calcula_medias_anuais_ordenadas(self):
        self.inserir_dados_agregacao()
        df = consultas.meteorologia_agregada(
            self.conn, "temperatura_c", "Todos", "2025-09-01", "2026-01-01"
        )
        self.assertEqual(len(df), 2)
        self.assertEqual(df["temperatura_c"].tolist(), [25.0, 50.0])
        self.assertEqual(
            df["timestamp_15min"].dt.strftime("%Y-%m-%d").tolist(),
            ["2025-01-01", "2026-01-01"],
        )

    def inserir_precipitacao(self, leituras):
        self.conn.executemany(
            "INSERT INTO meteorologia_15min (timestamp_15min, precipitacao) VALUES (?, ?)",
            leituras,
        )
        self.conn.commit()

    def test_catalogo_identifica_precipitacao_acumulativa(self):
        self.assertEqual(catalogo.VARIAVEIS_ACUMULATIVAS, {"precipitacao"})

    def test_precipitacao_agregada_soma_valores_do_dia(self):
        self.inserir_precipitacao([
            ("2025-09-01 00:00:00", 0.2),
            ("2025-09-01 00:15:00", 0.3),
            ("2025-09-01 00:30:00", 0.5),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, "precipitacao", "Mês", "2025-09-01", "2025-09-01"
        )
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df["precipitacao"].iloc[0], 1.0)

    def test_precipitacao_ignora_nulos_ao_somar(self):
        self.inserir_precipitacao([
            ("2025-09-01 00:00:00", 0.2),
            ("2025-09-01 00:15:00", None),
            ("2025-09-01 00:30:00", 0.3),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, "precipitacao", "Mês", "2025-09-01", "2025-09-01"
        )
        self.assertAlmostEqual(df["precipitacao"].iloc[0], 0.5)

    def test_precipitacao_totalmente_nula_permanece_nula(self):
        self.inserir_precipitacao([
            ("2025-09-01 00:00:00", None),
            ("2025-09-01 00:15:00", None),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, "precipitacao", "Mês", "2025-09-01", "2025-09-01"
        )
        self.assertTrue(df["precipitacao"].isna().iloc[0])

    def test_precipitacao_soma_em_mes_ano_e_todos(self):
        self.inserir_precipitacao([
            ("2025-09-01 00:00:00", 0.2),
            ("2025-09-01 00:15:00", 0.3),
            ("2025-09-02 00:00:00", 0.5),
            ("2025-10-01 00:00:00", 0.4),
            ("2026-01-01 00:00:00", 0.7),
        ])
        mensal = consultas.meteorologia_agregada(
            self.conn, "precipitacao", "Ano", "2025-09-01", "2026-01-01"
        )
        anual = consultas.meteorologia_agregada(
            self.conn, "precipitacao", "Todos", "2025-09-01", "2026-01-01"
        )
        self.assertEqual(mensal["precipitacao"].tolist(), [1.0, 0.4, 0.7])
        self.assertEqual(anual["precipitacao"].tolist(), [1.4, 0.7])

    def inserir_direcoes(self, coluna, leituras):
        self.conn.executemany(
            f"INSERT INTO meteorologia_15min (timestamp_15min, {coluna}) VALUES (?, ?)",
            leituras,
        )
        self.conn.commit()

    def assert_direcao_proxima_de_zero(self, valor):
        distancia = min(abs(valor), abs(valor - 360.0))
        self.assertLess(distancia, 1e-6)

    def test_catalogo_identifica_todas_as_direcoes_angulares(self):
        esperadas = {
            "vento_dir_med_graus",
            "vento_dir_max_graus",
            "vento_dir_min_graus",
        }
        self.assertEqual(catalogo.VARIAVEIS_CIRCULARES, esperadas)

    def test_media_circular_350_10_no_modo_mes(self):
        coluna = "vento_dir_med_graus"
        self.inserir_direcoes(coluna, [
            ("2025-09-01 00:00:00", 350.0),
            ("2025-09-01 00:15:00", 10.0),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, coluna, "M\u00eas", "2025-09-01", "2025-09-30"
        )
        self.assertEqual(len(df), 1)
        self.assert_direcao_proxima_de_zero(df[coluna].iloc[0])

    def test_media_circular_355_5_no_modo_ano(self):
        coluna = "vento_dir_max_graus"
        self.inserir_direcoes(coluna, [
            ("2025-09-01 00:00:00", 355.0),
            ("2025-09-02 00:00:00", 5.0),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, coluna, "Ano", "2025-09-01", "2025-09-30"
        )
        self.assertEqual(len(df), 1)
        self.assert_direcao_proxima_de_zero(df[coluna].iloc[0])

    def test_media_circular_direcao_ambigua_retorna_nulo(self):
        coluna = "vento_dir_min_graus"
        self.inserir_direcoes(coluna, [
            ("2025-09-01 00:00:00", 90.0),
            ("2025-09-02 00:00:00", 270.0),
        ])
        df = consultas.meteorologia_agregada(
            self.conn, coluna, "Todos", "2025-09-01", "2025-09-30"
        )
        self.assertEqual(len(df), 1)
        self.assertTrue(df[coluna].isna().iloc[0])

    def test_media_circular_no_modo_todos_e_dia_preservado(self):
        coluna = "vento_dir_med_graus"
        self.inserir_direcoes(coluna, [
            ("2025-09-01 00:00:00", 355.0),
            ("2025-09-02 00:00:00", 5.0),
        ])
        agregado = consultas.meteorologia_agregada(
            self.conn, coluna, "Todos", "2025-09-01", "2025-09-30"
        )
        self.assertEqual(len(agregado), 1)
        self.assert_direcao_proxima_de_zero(agregado[coluna].iloc[0])
        diario = consultas.meteorologia_agregada(
            self.conn, coluna, "Dia", "2025-09-01", "2025-09-30"
        )
        self.assertEqual(diario[coluna].tolist(), [355.0, 5.0])

    def test_meteorologia_agregada_rejeita_modo_invalido(self):
        with self.assertRaises(ValueError):
            consultas.meteorologia_agregada(
                self.conn, "temperatura_c", "semana", "2025-09-01", "2025-09-30"
            )

    def test_resumo_variavel_meteorologica_calcula_estatisticas(self):
        self.inserir_dados()
        resumo = consultas.resumo_variavel_meteorologica(self.conn, "temperatura_c")
        self.assertEqual(resumo["minimo"], 10.0)
        self.assertEqual(resumo["maximo"], 40.0)
        self.assertAlmostEqual(resumo["media"], 25.0)
        self.assertEqual(resumo["mediana"], 25.0)
        self.assertEqual(resumo["nao_nulos"], 4)
        self.assertEqual(resumo["nulos"], 1)
        self.assertEqual(resumo["percentual_valido"], 80.0)

    def test_resumo_variavel_rejeita_nome_de_coluna_invalido(self):
        with self.assertRaises(ValueError):
            consultas.resumo_variavel_meteorologica(
                self.conn, 'temperatura_c" FROM leitura_15min --'
            )

    def test_resumo_meteorologia_conta_dias_e_maior_lacuna(self):
        self.inserir_dados()
        self.assertEqual(
            consultas.resumo_meteorologia(self.conn),
            {
                "primeira_data": "2025-09-01",
                "ultima_data": "2025-09-02",
                "total_registros": 5,
                "total_dias": 2,
                "maior_lacuna_minutos": 1380,
            },
        )

    def inserir_timestamps(self, timestamps):
        self.conn.executemany(
            "INSERT INTO meteorologia_15min (timestamp_15min) VALUES (?)",
            [(timestamp,) for timestamp in timestamps],
        )
        self.conn.commit()

    def test_lacunas_serie_continua_nao_tem_lacunas(self):
        self.inserir_timestamps([
            "2025-09-01 00:00:00",
            "2025-09-01 00:15:00",
            "2025-09-01 00:30:00",
            "2025-09-01 00:45:00",
        ])
        df = consultas.lacunas_meteorologia(self.conn)
        self.assertTrue(df.empty)
        self.assertEqual(
            consultas.resumo_lacunas_meteorologia(self.conn),
            {"quantidade_lacunas": 0, "maior_lacuna_min": 0, "total_registros_ausentes": 0},
        )

    def test_lacunas_uma_lacuna_calcula_minutos_e_registros(self):
        self.inserir_timestamps([
            "2025-09-01 00:00:00",
            "2025-09-01 00:15:00",
            "2025-09-01 01:00:00",
        ])
        df = consultas.lacunas_meteorologia(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["inicio"].strftime("%H:%M"), "00:15")
        self.assertEqual(df.iloc[0]["fim"].strftime("%H:%M"), "01:00")
        self.assertEqual(df.iloc[0]["minutos_ausentes"], 30)
        self.assertEqual(df.iloc[0]["registros_ausentes"], 2)
        self.assertEqual(
            consultas.resumo_lacunas_meteorologia(self.conn),
            {"quantidade_lacunas": 1, "maior_lacuna_min": 30, "total_registros_ausentes": 2},
        )

    def test_lacunas_duas_lacunas_somam_registros_ausentes(self):
        self.inserir_timestamps([
            "2025-09-01 00:00:00",
            "2025-09-01 00:30:00",
            "2025-09-01 01:15:00",
        ])
        df = consultas.lacunas_meteorologia(self.conn)
        self.assertEqual(df["minutos_ausentes"].tolist(), [15, 30])
        self.assertEqual(df["registros_ausentes"].tolist(), [1, 2])
        self.assertEqual(
            consultas.resumo_lacunas_meteorologia(self.conn),
            {"quantidade_lacunas": 2, "maior_lacuna_min": 30, "total_registros_ausentes": 3},
        )

    def test_lacunas_banco_vazio_retorna_dataframe_e_resumo_consistentes(self):
        df = consultas.lacunas_meteorologia(self.conn)
        self.assertTrue(df.empty)
        self.assertEqual(
            df.columns.tolist(),
            ["inicio", "fim", "minutos_ausentes", "registros_ausentes"],
        )
        self.assertEqual(
            consultas.resumo_lacunas_meteorologia(self.conn),
            {"quantidade_lacunas": 0, "maior_lacuna_min": 0, "total_registros_ausentes": 0},
        )

    def test_banco_vazio_retorna_resultados_consistentes(self):
        self.assertEqual(consultas.datas_meteorologia(self.conn), [])
        self.assertTrue(
            consultas.meteorologia_periodo(self.conn, "2025-09-01", "2025-09-30").empty
        )
        self.assertEqual(
            consultas.resumo_variavel_meteorologica(self.conn, "temperatura_c"),
            {
                "minimo": None,
                "maximo": None,
                "media": None,
                "mediana": None,
                "nao_nulos": 0,
                "nulos": 0,
                "percentual_valido": 0.0,
            },
        )
        self.assertEqual(
            consultas.resumo_meteorologia(self.conn),
            {
                "primeira_data": None,
                "ultima_data": None,
                "total_registros": 0,
                "total_dias": 0,
                "maior_lacuna_minutos": 0,
            },
        )


    def test_resumo_ingestao_com_registros_ok_e_erro(self):
        self.conn.executemany(
            """INSERT INTO ingestao_arquivos
               (origem, nome_arquivo, sha256, processado_em, status,
                primeiro_registro, ultimo_registro, mensagem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("ftp", "a.txt", "a1", "2026-11-25 10:00:00", "ok",
                 "2026-11-01 00:00:00", "2026-11-01 23:45:00", None),
                ("ftp", "b.txt", "b1", "2026-11-25 10:15:00", "erro",
                 None, None, "falha de leitura"),
                ("ftp", "c.txt", "c1", "2026-11-25 10:30:00", "ok",
                 "2026-11-02 00:00:00", "2026-11-02 23:45:00", None),
            ],
        )
        self.assertEqual(
            consultas.resumo_ingestao_meteorologia(self.conn),
            {
                "ultima_aquisicao": "2026-11-25 10:30:00",
                "arquivos_ok": 2,
                "arquivos_erro": 1,
                "primeiro_registro": "2026-11-01 00:00:00",
                "ultimo_registro": "2026-11-02 23:45:00",
            },
        )

    def test_resumo_ingestao_sem_registros_retorna_zeros(self):
        self.assertEqual(
            consultas.resumo_ingestao_meteorologia(self.conn),
            {
                "ultima_aquisicao": None,
                "arquivos_ok": 0,
                "arquivos_erro": 0,
                "primeiro_registro": None,
                "ultimo_registro": None,
            },
        )

    def test_ingestao_periodo_ordena_mais_novo_e_respeita_limite(self):
        self.conn.executemany(
            """INSERT INTO ingestao_arquivos
               (origem, nome_arquivo, sha256, processado_em, status, mensagem)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                ("ftp", "antigo.txt", "a", "2026-11-25 10:00:00", "ok", None),
                ("ftp", "novo.txt", "b", "2026-11-25 10:30:00", "erro", "erro"),
                ("ftp", "meio.txt", "c", "2026-11-25 10:15:00", "ok", None),
            ],
        )
        df = consultas.ingestao_meteorologia_periodo(self.conn, limite=2)
        self.assertEqual(df.columns.tolist(), ["data_hora", "arquivo", "status", "mensagem"])
        self.assertEqual(df["arquivo"].tolist(), ["novo.txt", "meio.txt"])
        self.assertEqual(len(consultas.ingestao_meteorologia_periodo(self.conn, limite=0)), 0)

    def test_ingestao_periodo_vazio_retorna_dataframe_com_colunas(self):
        df = consultas.ingestao_meteorologia_periodo(self.conn, limite=50)
        self.assertTrue(df.empty)
        self.assertEqual(df.columns.tolist(), ["data_hora", "arquivo", "status", "mensagem"])


if __name__ == "__main__":
    unittest.main()

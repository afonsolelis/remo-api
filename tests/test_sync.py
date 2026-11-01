"""Contratos do coletor (docs/especificacao/sync.md). Sem rede e sem banco."""
import contextlib
import importlib.util
import pathlib
import re
import unittest
from unittest import mock

import requests

RAIZ = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync_supabase", RAIZ / "scripts" / "sync_supabase.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class Conexao:
    """Imita o psycopg o bastante para registrar o que cada liga gravou."""

    def __init__(self):
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def commit(self):
        pass

    @contextlib.contextmanager
    def transaction(self):
        yield

    @contextlib.contextmanager
    def cursor(self):
        yield self

    def executemany(self, sql, linhas):
        self.sql.append((sql, list(linhas)))

    def ligas_gravadas(self):
        return [p[0] for s, p in self.sql if "insert into remo_ligas" in s]

    def ligas_apagadas(self):
        return [p[0] for s, p in self.sql if s.startswith("delete from")]


def liga_com_jogos():
    jogo = (1, 1, None, 10, 20, 1, 0, True, "Fase única", 0, None, None, None)
    return {"zonas": [], "fases": [{"nome": "Fase única", "grupos": []}], "rodada_atual": 1,
            "clubes": {10: (10, "A", "A", None), 20: (20, "B", "B", None)}, "partidas": [jogo]}


LIGAS_TESTE = {
    "quebra": ("Quebra", "copa", "x/quebra", "00000000-0000-0000-0000-000000000001"),
    "boa": ("Boa", "copa", "x/boa", "00000000-0000-0000-0000-000000000002"),
}


def rodar(buscar, pagina_ge=None, noticias=lambda conn: [], argv=("sync_supabase.py",)):
    """Roda o main com banco e ge falsos. Sem pagina_ge, a edição atual é sempre a reserva."""
    conn = Conexao()
    if pagina_ge is None:
        edicao = mock.patch.object(sync, "uuid_atual", side_effect=lambda pagina, reserva: reserva)
    else:
        edicao = mock.patch.object(sync.session, "get", side_effect=pagina_ge)
    with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://teste"}), \
            mock.patch.object(sync, "LIGAS", LIGAS_TESTE), \
            mock.patch.object(sync.psycopg, "connect", return_value=conn), \
            edicao, \
            mock.patch.object(sync, "fetch_liga", side_effect=buscar),             mock.patch.object(sync, "sync_noticias", side_effect=noticias),             mock.patch.object(sync.sys, "argv", list(argv)):
        try:
            sync.main()
            codigo = 0
        except SystemExit as e:
            codigo = e.code
    return conn, codigo


def quebra_a_primeira(uuid):
    if uuid.endswith("1"):
        raise requests.ConnectionError("ge fora do ar")
    return liga_com_jogos()


class TestToleranciaFonte(unittest.TestCase):
    """TC-tolerancia-fonte: QS-tolerancia-fonte, RF-preservar."""

    def test_falha_de_uma_liga_preserva_o_dado_e_segue(self):
        conn, _ = rodar(quebra_a_primeira)
        self.assertEqual(conn.ligas_gravadas(), ["boa"])
        self.assertNotIn("quebra", conn.ligas_apagadas())

    def test_liga_sem_jogos_preserva_o_dado(self):
        def sem_jogos(uuid):
            d = liga_com_jogos()
            if uuid.endswith("1"):
                d["partidas"] = []
            return d
        conn, _ = rodar(sem_jogos)
        self.assertEqual(conn.ligas_gravadas(), ["boa"])
        self.assertNotIn("quebra", conn.ligas_apagadas())


class TestAvisarFalha(unittest.TestCase):
    """TC-avisar-falha: RF-avisar-falha. Falha de liga termina com código != 0."""

    def test_falha_de_liga_termina_com_erro_depois_de_gravar_as_outras(self):
        conn, codigo = rodar(quebra_a_primeira)
        self.assertEqual(conn.ligas_gravadas(), ["boa"])
        self.assertNotIn(codigo, (0, None))

    def test_sem_falha_termina_com_sucesso(self):
        _, codigo = rodar(lambda uuid: liga_com_jogos())
        self.assertIn(codigo, (0, None))

    def test_usar_o_uuid_reserva_e_falha(self):
        # Página do campeonato sem o UUID (ge mudou o HTML): coleta segue com o reserva, mas avisa.
        conn, codigo = rodar(lambda uuid: liga_com_jogos(), pagina_ge=lambda *a, **k: Resposta("<html></html>"))
        self.assertEqual(conn.ligas_gravadas(), ["quebra", "boa"])
        self.assertNotIn(codigo, (0, None))

    def test_sem_jogos_nao_e_falha(self):
        def vazia(uuid):
            d = liga_com_jogos()
            d["partidas"] = []
            return d
        _, codigo = rodar(vazia)
        self.assertIn(codigo, (0, None))


class Resposta:
    def __init__(self, texto="", dados=None):
        self.text = texto
        self.dados = dados

    def json(self):
        return self.dados

    def raise_for_status(self):
        pass


class TestViradaTemporada(unittest.TestCase):
    """TC-virada-temporada: QS-virada-temporada, RF-edicao-atual."""

    NOVO = "a1b2c3d4-0000-4000-8000-123456789abc"
    RESERVA = "00000000-0000-0000-0000-000000000009"

    def test_usa_o_uuid_publicado_na_pagina(self):
        html = f'<div data-bs-resource-id="{self.NOVO}"></div>'
        with mock.patch.object(sync.session, "get", return_value=Resposta(html)):
            self.assertEqual(sync.uuid_atual("x/camp", self.RESERVA), self.NOVO)

    def test_pagina_fora_do_ar_usa_o_reserva(self):
        with mock.patch.object(sync.session, "get", side_effect=requests.ConnectionError()):
            self.assertEqual(sync.uuid_atual("x/camp", self.RESERVA), self.RESERVA)

    def test_pagina_sem_uuid_usa_o_reserva(self):
        with mock.patch.object(sync.session, "get", return_value=Resposta("<html></html>")):
            self.assertEqual(sync.uuid_atual("x/camp", self.RESERVA), self.RESERVA)


class TestSomenteLeitura(unittest.TestCase):
    """TC-somente-leitura: QS-somente-leitura, RNF-banco-compartilhado."""

    sql = (RAIZ / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()

    def tabelas(self):
        return set(re.findall(r"create table if not exists (\w+)", self.sql))

    def test_so_tabelas_remo(self):
        self.assertTrue(self.tabelas())
        for t in self.tabelas():
            self.assertTrue(t.startswith("remo_"), t)

    def test_rls_ligado_em_todas_as_tabelas(self):
        for t in self.tabelas():
            self.assertRegex(self.sql, rf"alter table {t}\s+enable row level security")

    def test_politicas_so_de_leitura(self):
        politicas = re.findall(r"create policy \w+ on (\w+)\s+for (\w+)", self.sql)
        self.assertEqual({t for t, _ in politicas}, self.tabelas())
        self.assertEqual({op for _, op in politicas}, {"select"})
        self.assertNotRegex(self.sql, r"grant\s+(insert|update|delete|all)")


class TestAtualidade(unittest.TestCase):
    """TC-atualidade: QS-atualidade. Coleta diária que regrava atualizado_em."""

    def test_agendamento_diario(self):
        yml = (RAIZ / ".github" / "workflows" / "dados.yml").read_text(encoding="utf-8")
        crons = re.findall(r'cron:\s*"([^"]+)"', yml)
        self.assertEqual(len(crons), 1)
        minuto, hora, dia, mes, semana = crons[0].split()
        self.assertTrue(minuto.isdigit() and hora.isdigit())
        self.assertEqual((dia, mes, semana), ("*", "*", "*"))

    def test_gravacao_atualiza_a_data(self):
        conn, _ = rodar(lambda uuid: liga_com_jogos())
        inserts = [s for s, _ in conn.sql if "insert into remo_ligas" in s]
        self.assertTrue(inserts)
        for s in inserts:
            self.assertIn("atualizado_em = now()", s)


def materia(n, url=None, tipo="materia", imagem="https://s2-ge.glbimg.com/x.jpg"):
    return {"id": f"n{n}", "type": tipo, "publication": "2026-10-31T21:08:10Z",
            "content": {"title": f"Notícia {n}", "summary": "Resumo", "url": url or f"https://ge.globo.com/pa/n{n}.ghtml",
                        "image": {"sizes": {"S": {"url": imagem}}}}}


class TestNoticias(unittest.TestCase):
    """TC-noticias: RF-noticias (docs/especificacao/sync.md#notícias)."""

    def test_slug_igual_ao_endereco_do_ge(self):
        self.assertEqual(sync.slug("São Paulo"), "sao-paulo")
        self.assertEqual(sync.slug("Atlético-MG"), "atletico-mg")

    def test_so_materias_do_ge_e_no_maximo_dez(self):
        itens = [materia(i) for i in range(15)] + [materia(99, tipo="video"),
                                                    materia(98, url="https://outro.site/x"),
                                                    materia(97, imagem="javascript:alert(1)")]
        itens = itens[-3:] + itens[:-3]
        with mock.patch.object(sync.session, "get", return_value=Resposta(dados={"items": itens})):
            noticias = sync.fetch_noticias("feed")
        self.assertEqual(len(noticias), sync.NOTICIAS_POR_CLUBE)
        ids = [n[0] for n in noticias]
        self.assertNotIn("n99", ids)
        self.assertNotIn("n98", ids)
        self.assertIsNone(noticias[0][4], "imagem sem https é descartada")
        self.assertTrue(all(n[3].startswith("https://ge.globo.com/") for n in noticias))

    def rodar_noticias(self, feed):
        conn = Conexao()
        paginas = {"remo": "https://ge.globo.com/pa/futebol/times/remo/",
                   "paysandu": "https://ge.globo.com/pa/futebol/times/paysandu/"}
        with mock.patch.object(sync, "clubes_do_banco", return_value={364: "Remo", 1: "Paysandu", 2: "Time Sem Página"}),                 mock.patch.object(sync, "paginas_dos_times", return_value=paginas),                 mock.patch.object(sync, "feed_do_time", side_effect=lambda pagina: pagina),                 mock.patch.object(sync, "fetch_noticias", side_effect=feed):
            falhas = sync.sync_noticias(conn)
        apagados = [p[0] for s, p in conn.sql if s.startswith("delete from remo_noticias where clube_id = ")]
        return apagados, falhas

    def test_falha_de_um_clube_preserva_as_noticias_dele(self):
        def feed(pagina):
            if "paysandu" in pagina:
                raise requests.ConnectionError()
            return [("n1", "T", None, "https://ge.globo.com/x", None, "2026-10-31T00:00:00Z")]
        apagados, falhas = self.rodar_noticias(feed)
        self.assertEqual(apagados, [364])
        self.assertEqual(falhas, [])

    def test_nenhum_clube_gravado_e_falha(self):
        apagados, falhas = self.rodar_noticias(lambda pagina: [])
        self.assertEqual(apagados, [])
        self.assertTrue(falhas)

    def test_modo_noticias_nao_toca_nas_ligas(self):
        chamadas = []
        conn, codigo = rodar(lambda uuid: liga_com_jogos(), noticias=lambda c: chamadas.append(1) or [],
                             argv=("sync_supabase.py", "noticias"))
        self.assertEqual(conn.ligas_gravadas(), [])
        self.assertEqual(chamadas, [1])
        self.assertIn(codigo, (0, None))

    def test_falha_nas_noticias_avisa(self):
        _, codigo = rodar(lambda uuid: liga_com_jogos(), noticias=lambda c: ["Notícias: quebrou"])
        self.assertNotIn(codigo, (0, None))


if __name__ == "__main__":
    unittest.main()

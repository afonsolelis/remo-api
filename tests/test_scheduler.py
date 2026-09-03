"""Validação do snapshot que o atualizador publica."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import scheduler
from src import liga


def _projection() -> dict:
    return {
        "source_fetched_at": "2026-09-02T10:00:00+00:00",
        "league": {"team_ids": [1, 2]},
        **{chave: {"liga": {"chave": chave}} for chave in liga.LIGAS},
    }


def test_projecao_com_todas_as_ligas_esta_atualizada():
    snapshot = {"fetched_at": "2026-09-02T10:00:00+00:00"}
    with patch.object(scheduler.store, "load_projection", return_value=_projection()):
        assert scheduler.projection_is_current(snapshot)


def test_projecao_sem_mls_e_incompleta():
    snapshot = {"fetched_at": "2026-09-02T10:00:00+00:00"}
    projection = _projection()
    projection["mls"] = None
    with patch.object(scheduler.store, "load_projection", return_value=projection):
        assert not scheduler.projection_is_current(snapshot)


if __name__ == "__main__":
    test_projecao_com_todas_as_ligas_esta_atualizada()
    test_projecao_sem_mls_e_incompleta()
    print("ok — validação do snapshot do scheduler coberta")

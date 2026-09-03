"""Configuração do cliente das ligas internacionais."""

import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import espn


def test_endpoint_compativel_com_a_railway():
    """``site.api`` devolve 403 para o IP de saída da Railway."""
    assert urlparse(espn.BASE).hostname == "site.web.api.espn.com"


if __name__ == "__main__":
    test_endpoint_compativel_com_a_railway()
    print("ok — endpoint da ESPN validado")

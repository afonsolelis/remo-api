"""Executor comum das páginas do dashboard."""

from pathlib import Path


def render_page(page_name: str) -> None:
    """Executa o renderer compartilhado para a página selecionada."""
    source = Path(__file__).with_name("dashboard.py")
    code = compile(source.read_bytes(), str(source), "exec")
    exec(
        code,
        {
            "__name__": "__main__",
            "__file__": str(source),
            "SELECTED_PAGE": page_name,
        },
    )

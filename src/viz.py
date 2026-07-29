"""Paleta e estilo dos gráficos (plotly), em modo claro.

Valores da paleta validada (banda de luminosidade, separação CVD e contraste):
azul como cor principal — e do Leão —, laranja como segunda série, cinza
neutro para empates/demais times.
"""

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE = "#2a78d6"        # série principal / Remo
BLUE_DARK = "#104281"
BLUE_LIGHT = "#cde2fb"
ORANGE = "#eb6834"      # segunda série (visitante, validação)
GRAY = "#898781"        # empate / neutro
OTHERS = "#c3c2b7"      # demais times em gráficos com destaque

# rampa sequencial de um matiz (magnitude) — heatmap
SEQ_BLUES = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
SEQ_COLORSCALE = [[i / (len(SEQ_BLUES) - 1), c] for i, c in enumerate(SEQ_BLUES)]

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def apply_layout(fig, height: int = 380, title: str | None = None):
    fig.update_layout(
        height=height,
        title=title,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK_2, size=13),
        title_font=dict(color=INK, size=15),
        margin=dict(l=10, r=10, t=48 if title else 16, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=dict(bgcolor=INK, font=dict(family=FONT, color="#ffffff")),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                     tickfont=dict(color=MUTED))
    return fig


def pct(x: float, dec: int = 1) -> str:
    """0.1234 -> '12,3%'"""
    return f"{100 * x:.{dec}f}".replace(".", ",") + "%"

# Parecer da camada de engenharia (SP3)

Validador: `@val-eng`, redigido com IA em 2026-10-31. Não substitui a
assinatura humana da baseline (Art. II).

## Veredito

**Aprovado com ressalvas**, depois que o mantenedor confirmar as views recuperadas.

## Achados do gate

Nenhum achado `ENG-*`. `VW-engineering` tem modelo `deployment`, realiza
`VW-computational` (`COR-eng-comp`) e é afetada por decisões rastreadas a
requisitos e cenários (`AD-coleta-agendada`, `AD-isolamento-por-liga`,
`AD-aviso-por-falha`, `AD-simulacao-sob-demanda`, `AD-rls-somente-leitura`).

Bloqueio comum a todas as views: `RECOVERED-CONFIRMED`. As views foram
recuperadas do código e precisam da confirmação do mantenedor.

## Leitura crítica

- A distribuição responde aos cenários. O ge só é acessado pelo runner
  (`QS-tolerancia-fonte`), a escrita só existe no runner (`QS-somente-leitura`) e
  a carga pesada no celular foi reduzida a uma liga por vez (`QS-desempenho`).
- **Ressalva 1:** o nó mais fraco (o celular) carrega a simulação. A decisão está
  justificada por custo e simplicidade, mas o proxy de 1 s no Node supõe que o
  celular seja só 3 vezes mais lento. A medida real fica para a SP5.
- **Ressalva 2:** o banco é um ponto único compartilhado com outro projeto
  (`AD-tec-banco`). Não há cenário para indisponibilidade do Supabase: se ele
  cair, o site fica sem dados.

## Decisões do mantenedor (2026-10-31)

1. As views recuperadas e as mudanças planejadas foram confirmadas (`confirmed: true`).
2. O risco de indisponibilidade do Supabase foi aceito sem cenário próprio.

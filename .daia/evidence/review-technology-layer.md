# Parecer da camada de tecnologia (SP3)

Validador: `@val-tec`, redigido com IA em 2026-10-31. Não substitui a
assinatura humana da baseline (Art. II).

## Veredito

**Aprovado com ressalvas**, depois que o mantenedor confirmar as views recuperadas.

## Achados do gate

Nenhum achado `TEC-*`. `VW-technology` realiza `VW-engineering` (`COR-tec-eng`).
Cada escolha é uma decisão com alternativa e critério: `AD-tec-coleta`,
`AD-tec-banco`, `AD-tec-pagina`, `AD-tec-testes` e `AD-modulo-calculos`.

## Leitura crítica

- As tecnologias foram herdadas do projeto existente. As decisões registram o
  critério depois do fato: é uma recuperação, não uma escolha nova.
- **Ressalva 1:** o motivo para preterir os arquivos JSON no repositório
  (`AD-tec-banco`) foi inferido pela IA a partir da pasta `data/` abandonada. Só o
  mantenedor sabe o motivo real.
- **Ressalva 2:** `AD-tec-pagina` preteriu o Chart.js por equivalência, não por
  requisito. A alternativa é real, mas o critério é inércia. Isso é aceitável, e
  fica registrado assim.
- **Novidade tecnológica:** `AD-tec-testes` cria a primeira suíte de testes do
  projeto. Isso muda a regra do `CLAUDE.md` "Sem suíte de testes", que precisa
  ser atualizada na SP4.

## Decisões do mantenedor (2026-10-31)

1. O critério inferido em `AD-tec-banco` foi confirmado (ressalva 1 resolvida).
2. A suíte de testes foi aceita; o `CLAUDE.md` é atualizado na SP4.

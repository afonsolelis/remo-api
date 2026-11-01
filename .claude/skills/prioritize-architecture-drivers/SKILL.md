---
name: prioritize-architecture-drivers
description: Priorize cenários de qualidade por importância e dificuldade para revelar os direcionadores arquiteturais. Use entre requisitos e decisões de arquitetura.
---

# Priorizar direcionadores arquiteturais

Facilite um QAW sobre cenários já especificados. Não crie cenários para preencher lacunas e não escolha a solução.

## Resultado

Preencha `utility_tree.importance` e `utility_tree.difficulty` com `H`, `M` ou `L` em cada cenário. Entregue à arquitetura a lista ordenada, destacando combinações `(H,H)`.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Confirme que os cenários passaram pelo gate SP2.
2. Obtenha a importância com os stakeholders e a dificuldade com participantes técnicos.
3. Registre divergências em vez de calcular consenso artificial.
4. Questione cenários `(L,L)` e destaque `(H,H)` como drivers.
5. Encaminhe lacunas ao responsável por requisitos e prioridades ao arquiteto.

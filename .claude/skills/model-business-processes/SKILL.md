---
name: model-business-processes
description: Modele personas, processos de negócio em BPMN 2.0 e a decomposição funcional IDEF0 antes de elicitar requisitos. Use na SP1, depois de identificar stakeholders e direcionadores.
---

# Modelar processos de negócio

Represente como o trabalho acontece hoje (ou deve acontecer), quem o executa e qual função ele cumpre. Base: BABOK v3 §10.43 (Personas) e §10.35 (Process Modelling, notações BPMN e IDEF0).

## Resultado

- `Persona` (`PER-*`) para cada perfil que executa ou sofre um processo, ligada a `STK-*`, com objetivos e evidência de origem.
- `Idef0Activity` (`IDF-*`) com raiz `A0` e filhos numerados a partir do pai (`A1`, `A11`...). Cada atividade declara entradas, controles, saídas, mecanismos e `automation` (`system`, `manual` ou `external`), que marca a fronteira do sistema.
- `BusinessProcess` (`BP-*`) para cada processo relevante, com gatilho, resultado, personas executoras, direcionadores sustentados, atividade IDEF0 realizada e um arquivo `.bpmn` (XML BPMN 2.0).

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas `persona`, `process` e `idef0` em `.daia/schemas/`.

1. Derive as personas dos stakeholders e da evidência de elicitação. Não invente perfis.
2. Escreva o diagrama de contexto `A0`: a função única do sistema de interesse, com ICOM completo.
3. Decomponha em 3 a 6 atividades por nível, somente até onde a fronteira fica clara.
4. Para cada processo, desenhe o BPMN com uma raia (`lane`) nomeada exatamente como cada persona executora, evento de início, atividades, fluxos e evento de fim.
5. Ligue o processo à atividade IDEF0 (`activity`) e aos direcionadores (`supports`).
6. Rode `daia gate SP1` e corrija os bloqueios `BIZ-*`.

Pare quando um processo depender de uma persona sem origem verificável ou quando o BPMN começar a descrever telas ou componentes. Isso é solução, não negócio.

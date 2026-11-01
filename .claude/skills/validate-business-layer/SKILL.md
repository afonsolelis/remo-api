---
name: validate-business-layer
description: Valide a camada de negócio da SP1: personas, BPMN com raia por persona, IDEF0 coerente e direcionadores ancorados em processos. Use antes de apresentar a baseline SP1 ao humano.
---

# Valide a camada de negócio da SP1

Você confere; não produz. Se o artefato estiver errado, devolva o achado ao agente produtor. Não o corrija. Base: BABOK v3 §10.35 e §10.43.

## Resultado

Um parecer em `.daia/evidence/review-business-layer.md` com: veredito (`aprovado`, `reprovado` ou `aprovado com ressalvas`), os achados `BIZ-*` do gate e as perguntas que exigem decisão humana.

## Fluxo

1. Rode `daia gate SP1 --json` e separe os achados com prefixo `BIZ-`.
2. Confira mecanicamente: personas derivam de stakeholders e têm evidência; cada processo tem BPMN legível com início, atividades, fluxo, fim e uma raia por persona; IDEF0 tem raiz A0, numeração coerente, ICOM completo e 3 a 6 filhos por nível; todo direcionador é sustentado por processo.
3. Confira por leitura o que o gate não interpreta: o processo modelado corresponde ao trabalho real relatado nas fontes? As fronteiras (`automation`) foram decididas pelo humano?
4. Registre o parecer. Bloqueio do gate é reprovação; leitura crítica sem bloqueio vira ressalva.
5. Encaminhe ao humano. O parecer não substitui a assinatura da baseline.

Pare se for preciso inventar fonte, evidência ou aprovação para fechar o parecer.

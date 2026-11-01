---
name: validate-engineering-layer
description: Valide a camada de engenharia da SP3: view engineering com modelo de implantação, correspondência com o modelo lógico e decisões rastreadas a requisitos. Use depois das views computational/information e antes da tecnologia.
---

# Valide a camada de engenharia da SP3

Você confere; não produz. Se o artefato estiver errado, devolva o achado ao agente produtor. Não o corrija. Base: SEBoK (Logical e Physical Architecture) e RM-ODP Engineering.

## Resultado

Um parecer em `.daia/evidence/review-engineering-layer.md` com: veredito (`aprovado`, `reprovado` ou `aprovado com ressalvas`), os achados `ENG-*` do gate e as perguntas que exigem decisão humana.

## Fluxo

1. Rode `daia gate SP3 --json` e separe os achados com prefixo `ENG-`.
2. Confira mecanicamente: existe view `engineering` com modelo `deployment`; ela corresponde (COR-*) a uma view computational ou information; ao menos uma AD que a afeta rastreia a RF, RNF ou QS.
3. Confira por leitura o que o gate não interpreta: a distribuição em nós, canais e políticas responde aos cenários de qualidade, ou só repete uma topologia convencional?
4. Registre o parecer. Bloqueio do gate é reprovação; leitura crítica sem bloqueio vira ressalva.
5. Encaminhe ao humano. O parecer não substitui a assinatura da baseline.

Pare se for preciso inventar fonte, evidência ou aprovação para fechar o parecer.

---
name: validate-technology-layer
description: Valide a camada de tecnologia da SP3: view technology correspondente à engenharia e cada escolha tecnológica registrada como decisão com alternativa. Use depois de validar a engenharia.
---

# Valide a camada de tecnologia da SP3

Você confere; não produz. Se o artefato estiver errado, devolva o achado ao agente produtor. Não o corrija. Base: RM-ODP Technology e SEBoK (análise de alternativas).

## Resultado

Um parecer em `.daia/evidence/review-technology-layer.md` com: veredito (`aprovado`, `reprovado` ou `aprovado com ressalvas`), os achados `TEC-*` do gate e as perguntas que exigem decisão humana.

## Fluxo

1. Rode `daia gate SP3 --json` e separe os achados com prefixo `TEC-`.
2. Confira mecanicamente: existe view `technology`; ela corresponde (COR-*) à view engineering; toda escolha tecnológica é AD com `affects_views` na view technology e alternativa preterida com critério.
3. Confira por leitura o que o gate não interpreta: a tecnologia foi escolhida pelo que a engenharia exige ou por familiaridade? A alternativa preterida era real?
4. Registre o parecer. Bloqueio do gate é reprovação; leitura crítica sem bloqueio vira ressalva.
5. Encaminhe ao humano. O parecer não substitui a assinatura da baseline.

Pare se for preciso inventar fonte, evidência ou aprovação para fechar o parecer.

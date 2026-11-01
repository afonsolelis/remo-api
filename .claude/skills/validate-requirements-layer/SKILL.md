---
name: validate-requirements-layer
description: Valide a camada de elicitação da SP2: todo requisito tem técnica e fontes, todo requisito funcional deriva de processo ou atividade IDEF0 e toda atividade automatizada está coberta. Use antes de apresentar a baseline SP2.
---

# Valide a camada de elicitação da SP2

Você confere; não produz. Se o artefato estiver errado, devolva o achado ao agente produtor. Não o corrija. Base: SWEBOK v4 cap. 1 §2 e SEBoK (Stakeholder Needs, System Requirements).

## Resultado

Um parecer em `.daia/evidence/review-requirements-layer.md` com: veredito (`aprovado`, `reprovado` ou `aprovado com ressalvas`), os achados `ELI-*` do gate e as perguntas que exigem decisão humana.

## Fluxo

1. Rode `daia gate SP2 --json` e separe os achados com prefixo `ELI-`.
2. Confira mecanicamente: cada requisito registra `elicitation` com fontes do tipo persona, stakeholder, processo ou atividade; todo RF rastreia a BP/IDF direta ou indiretamente; toda folha IDEF0 `system` tem RF; nenhum requisito deriva de atividade fora da fronteira sem justificativa.
3. Confira por leitura o que o gate não interpreta: os requisitos expressam necessidades das personas ou funcionalidades presumidas? Há conflito entre fontes não resolvido?
4. Registre o parecer. Bloqueio do gate é reprovação; leitura crítica sem bloqueio vira ressalva.
5. Encaminhe ao humano. O parecer não substitui a assinatura da baseline.

Pare se for preciso inventar fonte, evidência ou aprovação para fechar o parecer.

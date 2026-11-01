---
name: evaluate-architecture-tradeoffs
description: Avalie decisões arquiteturais por sensibilidade, tradeoffs e riscos, e reabra somente cenários afetados por mudanças. Use em ATAM ou análise de impacto.
---

# Avaliar tradeoffs arquiteturais

Exponha consequências; a decisão continua pertencendo ao arquiteto e sua aceitação ao humano.

## Resultado

Preencha `sensitivity_points`, `tradeoff_points` e `risks` das decisões. Em manutenção, produza o subconjunto de cenários que precisa ser reavaliado.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Relacione cada decisão aos cenários prioritários que ela influencia.
2. Identifique parâmetros cuja mudança altera atributos de qualidade.
3. Registre onde melhorar um atributo degrada outro e descreva o risco observável.
4. Em mudança existente, rode `daia impact <AD-id>` e limite a reavaliação ao alcance retornado.
5. Devolva decisões incompletas ao arquiteto; não selecione a alternativa em seu lugar.

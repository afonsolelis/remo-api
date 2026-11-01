---
name: implement-from-baseline
description: Implemente software a partir de uma baseline arquitetural assinada e leve contratos de teste de vermelho para verde. Use somente após a SP3.
---

# Implementar a partir da baseline

A baseline e seus contratos são a autoridade de escopo. Pedidos em linguagem natural não substituem decisões registradas.

## Resultado

Produza código rastreável à especificação, preserve os contratos e atualize `TestContract.phase` para `green` somente após execução bem-sucedida.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Rode `daia status` e pare se a SP3 não estiver assinada ou tiver drift não deliberado.
2. Leia views, decisões, especificações e testes antes de editar código.
3. Implemente contrato por contrato, sem funcionalidades oportunistas.
4. Se houver lacuna de decisão, devolva à arquitetura; se o cenário estiver errado, devolva a requisitos.
5. Declare os arquivos de implementacao/configuracao em `verification.<TC-id>.inputs`, execute os gates tecnicos e `daia verify SP4`. Produza o relatorio de qualidade por caracteristica.

Não altere um teste apenas para obter resultado verde e não assine a baseline.

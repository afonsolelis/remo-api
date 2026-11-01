---
name: write-executable-specification
description: Transforme decisões arquiteturais em contratos técnicos e testes executáveis inicialmente vermelhos. Use antes de implementar funcionalidades ou integrações.
---

# Escrever especificação executável

A especificação precede o teste; o teste precede a implementação. Uma lacuna que exige decisão deve voltar à arquitetura.

## Resultado

Produza contratos de interface, dados, regras e integrações referenciados em `models[].path`. Crie `TestContract` em `.daia/model/tests/` e o teste em `test_path`, com fase inicial `red` e `verifies` apontando ao requisito ou cenário.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Leia views, decisões e cenários; mantenha rastreio por afirmação relevante.
2. Especifique formatos, invariantes, erros e limites sem inventar comportamento.
3. Escreva testes contra a especificação e confirme que falham pela ausência da implementação.
4. Configure `verification` por contrato em `.daia/config.json` e execute `daia verify SP3`. Registre `phase` conforme o resultado. Inspecione a falha: erro de infraestrutura nao comprova comportamento ausente. Em projeto existente, preserve contratos ja verdes.

Não implemente o produto e não afrouxe contratos para acomodar código existente.

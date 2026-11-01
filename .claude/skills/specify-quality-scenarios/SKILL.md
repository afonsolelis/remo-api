---
name: specify-quality-scenarios
description: Converta necessidades em requisitos rastreáveis e atributos de qualidade em cenários mensuráveis de seis partes. Use na engenharia de requisitos ou ao reparar RNFs vagos.
---

# Especificar requisitos e qualidade

Use a ISO/IEC 25010 como vocabulário, não como checklist obrigatório. Um cenário sem limiar efetivo ainda não é uma especificação.

## Resultado

Produza `Requirement` e `QualityScenario` sob `.daia/model/`. Cada RNF deve apontar para cenário com `source`, `stimulus`, `artifact`, `environment`, `response` e `response_measure` (`metric`, `operator`, `threshold`).

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Leia drivers e concerns assinados na SP1.
2. Derive requisitos sem introduzir funcionalidades ou tecnologias não solicitadas.
3. Identifique somente características de qualidade relevantes ao contexto.
4. Negocie métricas e limites observáveis; recuse “rápido”, “aceitável” ou “TBD”.
5. Rode `daia gate SP2` e apresente lacunas ao humano.

Não decida arquitetura nem escreva testes nesta skill.

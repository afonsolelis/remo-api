---
name: validate-system-evidence
description: Organize medidas por característica de qualidade e confronte a hipótese de negócio com evidências e limitações. Use em auditoria SP4 e validação SP5.
---

# Validar evidências do sistema

Diferencie conformidade ao cenário, verificação técnica e validação da hipótese. Não generalize além da evidência coletada.

## Resultado

Produza em `.daia/evidence/` um relatório por característica da ISO 25010, roteiro de demonstração, medidas contra limiares, veredito da hipótese e limitações explícitas.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Rode `daia trace --matrix` e associe requisito, cenário, teste e medida.
2. Organize o relatório por característica, não por arquivo ou componente.
3. Declare características sem cenário e resultados negativos.
4. Recupere a hipótese da SP1 e classifique-a como confirmada, refutada ou inconclusiva.
5. Rode os gates SP4/SP5 aplicáveis e apresente a evidência para decisão humana.

Não conclua causalidade, superioridade ou generalização que o desenho não sustente.

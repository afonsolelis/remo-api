---
name: describe-software-architecture
description: Produza uma descrição arquitetural ISO 42010 com views, modelos, correspondências, decisões e alternativas. Use para desenhar ou recuperar a arquitetura de software.
---

# Descrever arquitetura de software

O catálogo ativo define as views concretas; a ISO 42010 define as relações que precisam permanecer coerentes.

## Resultado

Produza views em `.daia/model/views`, decisões em `decisions` e correspondências em `correspondences`. Inclua pelo menos um modelo estático e um dinâmico, enderece toda concern e registre alternativa preterida com critério para cada decisão relevante.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Leia a baseline SP2 e os drivers priorizados; consulte `daia viewpoints`.
2. Declare a fronteira do sistema e modele entidades/relações antes dos fluxos e estados.
3. Instancie apenas as views necessárias, ligando stakeholders e concerns.
4. Registre correspondências verificáveis entre views.
5. Para cada decisão, registre motivação, alternativa, critério, riscos e views afetadas.
6. Rode `daia gate SP3`; envie tradeoffs à avaliação e contratos à especificação.

Não gere código de produto antes de a SP3 ser assinada.

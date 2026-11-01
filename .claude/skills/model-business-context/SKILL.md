---
name: model-business-context
description: Modele o contexto de negócio, stakeholders, concerns, fronteira e hipótese antes de formular requisitos ou escolher tecnologia. Use ao iniciar ou recuperar a arquitetura de um sistema.
---

# Modelar contexto de negócio

Estabeleça por que o sistema existe, para quem e dentro de qual fronteira. Não converta soluções presumidas em necessidades.

## Resultado

Produza `BusinessDriver`, `Stakeholder`, `Concern` e a view `enterprise` em `.daia/model/`, rastreando cada afirmação à evidência fornecida. Registre ao menos uma hipótese que possa ser confrontada na SP5.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`. Registre o resultado com `daia verify` na etapa aplicável.

1. Confirme que o projeto foi inicializado com `daia init`.
2. Identifique stakeholders por papel e elicite suas preocupações como perguntas ou tensões.
3. Derive direcionadores verificáveis e registre a fronteira: implementado, simulado, externo e fora de escopo.
4. Relacione a view enterprise às concerns e aos stakeholders.
5. Rode `daia gate SP1`; não assine a baseline em nome do usuário.

Pare quando a origem de uma afirmação não puder ser demonstrada ou quando uma escolha técnica estiver sendo antecipada.

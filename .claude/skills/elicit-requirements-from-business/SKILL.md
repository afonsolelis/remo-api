---
name: elicit-requirements-from-business
description: Elicite requisitos a partir das personas, processos BPMN e atividades IDEF0 da baseline SP1, registrando técnica e fontes. Use na SP2 antes de escrever cenários de qualidade.
---

# Elicitar requisitos a partir do negócio

Transforme o modelo de negócio assinado em necessidades e requisitos verificáveis. Base: SWEBOK v4 cap. 1 (§2 Requirements Elicitation: fontes e técnicas) e SEBoK (Stakeholder Needs Definition → System Requirements Definition).

## Resultado

`Requirement` (`RF-*`, `RNF-*`) com:

- `traces_to` apontando para `BP-*` ou `IDF-*`, ou para uma necessidade (`level: stakeholder-need`) que aponte para eles;
- `elicitation.technique` (entrevista, workshop, observação, análise de documento, análise de processo, prototipação, cenário de uso, questionário, mapeamento de user stories);
- `elicitation.sources` com as personas, stakeholders, processos ou atividades consultados;
- `level` opcional: `stakeholder-need` para a necessidade na linguagem do negócio, `system` para o requisito que a transforma.

## Fluxo

1. Percorra cada atividade IDEF0 com `automation: system` que não tenha filhos: ela precisa de ao menos um requisito funcional.
2. Para cada tarefa do BPMN executada por uma persona, pergunte o que o sistema precisa fazer para ela. A resposta vira necessidade ou requisito.
3. Registre técnica e fonte no momento da elicitação, não depois.
4. Atividades `manual` ou `external` não geram requisito funcional. Se gerarem, a fronteira mudou: volte à SP1.
5. Rode `daia gate SP2` e corrija os bloqueios `ELI-*`. Depois aplique `specify-quality-scenarios` aos RNF.

Pare quando um requisito não tiver fonte demonstrável ou nomear componente ou tecnologia.

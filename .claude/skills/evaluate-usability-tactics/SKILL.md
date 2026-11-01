---
name: evaluate-usability-tactics
description: Avalie se as decisões que atendem cenários de usabilidade apoiam a iniciativa do usuário e a do sistema, com a interface separada da lógica (Bass, Clements & Kazman, cap. 11). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic interaction_capability.
---

# Avaliar táticas de usabilidade

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `usability/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `interaction_capability`, nome que a ISO/IEC 25010:2023 dá à antiga usabilidade. Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Verifique se a interface está separada da lógica (ex.: MVC, PAC, Seeheim). Se não estiver, registre lacuna: as táticas abaixo dependem dessa separação, que se apoia nas táticas de modificabilidade.
4. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente; na dúvida, pergunte a `@arch`.
5. Para cada operação longa, destrutiva ou automática citada no cenário, responda às perguntas de verificação. Uma tática ausente só é lacuna quando o cenário a exige.
6. Percorra o design checklist do §11.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
7. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
8. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Apoiar a iniciativa do usuário**

| Tática | Pergunta de verificação |
|---|---|
| `cancel` | Operações longas podem ser canceladas, com liberação de recursos e aviso aos colaboradores? |
| `undo` | Há estado suficiente para restaurar o anterior, por snapshot ou operação reversível? |
| `pause-resume` | Operações longas podem ser pausadas e retomadas? |
| `aggregate` | Operações repetitivas sobre muitos objetos podem ser feitas em grupo? |

**Apoiar a iniciativa do sistema**

| Tática | Pergunta de verificação |
|---|---|
| `maintain-task-model` | O sistema conhece a tarefa do usuário, para oferecer assistência contextual? |
| `maintain-user-model` | O sistema modela o conhecimento e o comportamento do usuário, com customização explícita? |
| `maintain-system-model` | O sistema prevê o próprio comportamento para informar o usuário (ex.: tempo restante)? |

## Trade-offs conhecidos

- Usabilidade × segurança: confirmações e reautenticação adicionam fricção.
- Usabilidade × desempenho: desfazer exige guardar estado; modelos de usuário custam processamento.
- Usabilidade × modificabilidade: separar a interface exige camadas e interfaces adicionais.

## Não faz

- Não cria fluxo de interação que não esteja nos cenários (Art. IV).
- Não recomenda tática sem cenário que a justifique.

---
name: evaluate-interoperability-tactics
description: Avalie se as decisões que atendem cenários de interoperabilidade aplicam táticas de localização e gerenciamento de interfaces (Bass, Clements & Kazman, cap. 6). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic compatibility.
---

# Avaliar táticas de interoperabilidade

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `interoperability/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `compatibility` (sub_characteristic interoperability). Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um padrão (ex.: ESB, mediator), registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
4. Para cada ponto de integração do cenário, responda às perguntas de verificação. Uma tática ausente só é lacuna quando o cenário a exige.
5. Percorra o design checklist do §6.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
6. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
7. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

| Tática | Família | Pergunta de verificação |
|---|---|---|
| `discover-service` | Localizar | O serviço é localizado por diretório ou registro, em vez de endereço fixo? |
| `orchestrate` | Gerenciar interfaces | A sequência de chamadas entre serviços é coordenada por um controle explícito? |
| `tailor-interface` | Gerenciar interfaces | Tradução, buffering ou ocultação de funções para consumidores não confiáveis está prevista? |

## Trade-offs conhecidos

- Interoperabilidade × desempenho: intermediários e tradução acrescentam latência.
- Interoperabilidade × segurança: diretórios e interfaces expostas ampliam a superfície de ataque.

## Não faz

- Não cria integração que não esteja nos requisitos (Art. IV).
- Não recomenda tática sem cenário que a justifique.

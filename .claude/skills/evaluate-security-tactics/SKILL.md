---
name: evaluate-security-tactics
description: Avalie se as decisões que atendem cenários de segurança aplicam táticas de detecção, resistência, reação e recuperação de ataques (Bass, Clements & Kazman, cap. 9). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic security.
---

# Avaliar táticas de segurança

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `security/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `security`. Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Identifique, em cada cenário, o ator, o ativo e a superfície de entrada.
4. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um mecanismo (ex.: OAuth, TLS), registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
5. Responda às perguntas de verificação das famílias pertinentes ao estímulo do cenário. Uma tática ausente só é lacuna quando o cenário a exige.
6. Percorra o design checklist do §9.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
7. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
8. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Detectar ataques**

| Tática | Pergunta de verificação |
|---|---|
| `detect-intrusion` | Padrões de requisição são comparados com assinaturas conhecidas? |
| `detect-service-denial` | Tráfego de entrada é comparado com perfis de negação de serviço? |
| `verify-message-integrity` | Mensagens, arquivos de configuração e artefatos de deploy têm checksum ou hash verificado? |
| `detect-message-delay` | Variações anômalas de tempo de entrega são detectadas? |

**Resistir a ataques**

| Tática | Pergunta de verificação |
|---|---|
| `identify-actors` | Toda entrada externa tem fonte identificada? |
| `authenticate-actors` | O mecanismo de autenticação corresponde ao risco do cenário? |
| `authorize-actors` | Permissões são verificadas por ator, grupo ou papel? |
| `limit-access` | Há firewalls, DMZ ou restrição de portas e protocolos? |
| `limit-exposure` | Recursos críticos estão divididos e distribuídos, de modo que uma única fraqueza não comprometa todos? Fatos sobre o sistema (ex.: número de pontos de entrada) são ocultados? |
| `encrypt-data` | Dados em repouso e em trânsito estão cifrados? |
| `separate-entities` | Dados sensíveis estão separados dos não sensíveis (servidor, VM, air-gap)? |
| `change-default-settings` | Configurações padrão são forçadas a mudar? |

**Reagir a ataques**

| Tática | Pergunta de verificação |
|---|---|
| `revoke-access` | Há revogação rápida de acesso a recursos sensíveis sob suspeita? |
| `lock-computer` | Tentativas repetidas de login bloqueiam a origem por janela de tempo? |
| `inform-actors` | Operadores e sistemas cooperantes são notificados? |

**Recuperar de ataques**

| Tática | Pergunta de verificação |
|---|---|
| `maintain-audit-trail` | Ações de usuários e do sistema são registradas de forma auditável? |
| `restore` | O serviço comprometido é restaurado? Avalie as táticas de recuperação com `evaluate-availability-tactics`. |

## Trade-offs conhecidos

- Segurança × usabilidade: autenticação adiciona fricção.
- Segurança × desempenho: cifragem e verificação de integridade custam ciclos.
- Segurança × interoperabilidade: interfaces expostas ampliam a superfície.

## Não faz

- Não cria requisito de segurança que não esteja nos requisitos (Art. IV).
- Não recomenda tática sem cenário que a justifique.

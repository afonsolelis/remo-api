# Relatório de qualidade (SP4)

Redigido com IA (`@audit`) em 2026-10-31, depois da implementação da SP4.
Organizado pelas características da ISO/IEC 25010:2023 que têm cenário. As
medidas valem para esta execução, neste ambiente; não são comparação com
outras abordagens.

Ambiente: Windows 11, Node 24.21.0, Python 3.12.10, Chrome do mantenedor,
servidor local `python -m http.server`, dados reais do Supabase.

## Resumo

| Característica | Cenário | Limiar | Medida observada | Veredito |
|---|---|---|---|---|
| reliability | `QS-tolerancia-fonte` | 100% dos campeonatos exibidos após falha | 100% (teste com falha simulada de 1 de 2 ligas) | atende |
| reliability | `QS-atualidade` | idade ≤ 25 h | agendamento diário e `atualizado_em = now()` verificados no código; dado visto na página: 31/10/2026 23:12 | atende (verificação estática) |
| flexibility | `QS-virada-temporada` | 0 alterações manuais | 0; as 4 ligas acham o UUID na página do ge (consulta real em 2026-10-31) | atende |
| security | `QS-somente-leitura` | 0 escritas aceitas | RLS ligado nas 3 tabelas, só políticas `select`, nenhum `grant` de escrita | atende (verificação estática) |
| interaction_capability | `QS-facilidade` | ≤ 2 ações | 0 ações para o torcedor do Remo; 2 (aba + time) para os outros | atende |
| interaction_capability | `QS-legibilidade` | menor fonte visível ≥ 14 px a 390 px | 14 px (Série A, Série B e Copa Verde, incluindo os gráficos) | atende |
| interaction_capability | `QS-tabela-celular` | 0 px além da tela a 390 px | 0 px na classificação e nos próximos jogos (Série A, 4 zonas; Série B) | atende |
| performance_efficiency | `QS-desempenho` | ≤ 3 s no celular | proxy no Node: 215 ms no pior caso (limite do proxy: 1.000 ms); Chrome no computador: 46 ms (Série A, 51 jogos restantes); página carregada em 204 ms | atende o proxy; celular não medido |

Contratos: 10 de 10 verdes (`daia verify SP4`). São 28 casos de teste: 14 em
Python e 14 em JavaScript.

## reliability

**`QS-tolerancia-fonte` (H,H).** `TC-tolerancia-fonte`: com o ge falhando para
uma liga, essa liga não é apagada nem regravada, e a outra é gravada. Vale
igual para uma liga sem jogos. Desde a SP4, a falha também termina a execução
com erro (`TC-avisar-falha`), e o GitHub avisa o mantenedor. O caso do UUID
reserva também gera aviso.

**`QS-atualidade` (H,M).** `TC-atualidade` confere o agendamento diário e a
regravação de `atualizado_em`. Ninguém mediu a idade real do dado em
produção ao longo de vários dias.

## flexibility

**`QS-virada-temporada` (M,H).** `TC-virada-temporada` cobre a página com UUID
novo, a página fora do ar e a página sem o atributo. Na consulta real ao ge de
2026-10-31, as 4 ligas acharam o UUID na página.

## security

**`QS-somente-leitura` (M,L).** `TC-somente-leitura` lê o `schema.sql`. Não
houve tentativa real de escrita com a chave publishable contra o Supabase.

## interaction_capability

**`QS-facilidade` (H,L).** `TC-facilidade`: o Remo é o padrão quando participa,
e as abas e o seletor ficam no topo, fora de menus. No Chrome, a página abriu
na Série A com o Remo escolhido, a posição e as chances visíveis.

**`QS-legibilidade` (H,L) e `QS-tabela-celular` (M,M)** — ciclo de mudança de
2026-11-01, a partir do relato do mantenedor ("achei pequenas as letras").
`TC-legibilidade` e `TC-tabela-celular` estavam vermelhos antes da mudança (7
casos falhando por falta do `@media`) e passaram depois. Medida real num iframe
de 390 px no Chrome, com dados reais: a menor fonte visível é 14 px (rótulos dos
cards e cabeçalho), o texto corrido tem 16 px e nenhuma tabela sai da tela. No
celular a classificação mostra #, sigla, pontos e as chances por zona (rótulo
curto, nome completo na legenda e no `title`).

## performance_efficiency

**`QS-desempenho` (M,M).** O pior caso (20 clubes, 380 jogos por disputar,
10.000 simulações) caiu de cerca de 1,3 s (estimado a partir de ~330 ms com
100 jogos, versão anterior) para 215 ms no Node. Antes, a página simulava todas
as ligas de pontos ao abrir; agora simula só a liga aberta.

## Características sem cenário (decisão da SP2)

compatibility, maintainability e safety. Funcionalidade (functional suitability)
é coberta pelos RF e pelos contratos `TC-classificacao`, `TC-simulacao` e `TC-copa`.

## Requisitos sem teste automatizado

- `RF-data-atualizacao`: verificado só no navegador (a data aparece no cabeçalho).
- As restrições `RNF-sem-custo`, `RNF-simplicidade`, `RNF-sem-segredos` e
  `RNF-portugues` foram conferidas por revisão do diff: nenhuma dependência nova,
  nenhum build, nenhum segredo, texto em português.

## Limitações

- **Celular emulado na legibilidade.** As medidas de 390 px foram feitas num iframe no
  computador; densidade de pixels e zoom do sistema do celular não entram.
- **Celular não medido.** O limiar de 3 s é verificado por um proxy (Node no
  computador, supondo um celular até 3 vezes mais lento). A medida real fica para a SP5.
- **Sync real não executado.** Sem a `DATABASE_URL` local, o coletor só rodou com
  banco e ge falsos. A primeira execução real será a do GitHub Actions depois do push.
- **Verificações estáticas.** `QS-atualidade` e `QS-somente-leitura` foram
  verificados lendo o código e a configuração, não observando o sistema em produção.
- **Dublês de teste.** Os testes do coletor imitam o psycopg; uma divergência com
  a biblioteca real não seria detectada (risco de `AD-tec-testes`).
- **Precisão do modelo.** Nada mede se as probabilidades acertam. Isso fica para a SP5.

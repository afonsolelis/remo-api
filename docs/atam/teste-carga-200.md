# Teste de carga — 200 acessos simultâneos

Data: 04/11/2026. Cenário avaliado: **D1** da [árvore de utilidade](arvore-utilidade.md), em que 200 torcedores abrem o site no minuto seguinte a um gol do Remo.

## Resultado em uma frase

O dashboard **não atende o cenário D1**:

- Com 200 sessões simultâneas, **48,5% falham** por tempo esgotado.
- **Nenhuma** das que conseguem abrir recebe a página em menos de 60 s. O p95 do primeiro conteúdo é de **248 s**, contra a meta de 3 s.
- A RAM do processo vai de 0,28 GB para **3,6 GB** e não volta.

O gargalo é a arquitetura de processo único do Streamlit. Cada sessão consome de 0,35 a 1 s de CPU, e tudo é serializado num único núcleo.

| Medida (meta do D1) | Meta | Medido, 200 em rajada | Situação |
|---|---|---|---|
| p95 até o primeiro conteúdo | ≤ 3 s | 248,5 s | ❌ |
| Falhas | < 1% | 48,5% (97 de 200) | ❌ |
| RAM do contêiner | < 80% do limite | pico de 3,6 GB, 2,7 a 3,1 GB depois do teste | ❌ em qualquer plano com até 4 GB |

## Como o teste foi feito

- **Sistema**: código da `main` (commit `ed9519a`), rodando com `streamlit run app.py` em modo *headless* e armazenamento JSON (o mesmo modo do Railway, sem `MONGO_URL`).
- **Dados**: gerados com `scripts/update_data.py` no mesmo dia: rodada 34, 20.000 simulações Ensemble. `projection.json` tem 2,1 MB. As ligas da ESPN responderam 400 e ficaram com o cache anterior, o que não afeta a página testada.
- **Cliente**: `scripts/loadtest.py`. Cada usuário virtual faz o mesmo caminho do navegador:
  1. `GET /`, o HTML estático.
  2. Abre o websocket `/_stcore/stream`.
  3. Envia `rerun_script`, que equivale a abrir a página padrão, o Brasileirão.
  4. Espera o `script_finished`, com cerca de 150 elementos da página.
  5. Envia um segundo `rerun_script`, que equivale a trocar o time em destaque, como no cenário D2.
- **O que conta como falha**: abrir o websocket em mais de 30 s ou esperar mais de 120 s por uma mensagem. Nenhum torcedor espera tanto, então a regra é generosa.
- **Métricas do servidor**: CPU e RSS do processo Streamlit lidos de `/proc` a cada 0,5 s.
- **Máquina**: 12 núcleos e 15 GB de RAM, com cliente e servidor na mesma máquina, sem latência de rede. O resultado é um **limite otimista** para o Railway, porque o processo usa um só núcleo de qualquer forma (ver CPU abaixo) e a rede real só acrescenta tempo.

## Resultados

Tempos em segundos. "Primeiro conteúdo" conta do pedido HTTP até o primeiro elemento da página. "Página completa" vai até o fim do script.

| Execução | Usuários | Chegada | OK | Falhas | Primeiro conteúdo p50 / p95 | Página completa p50 / p95 | Interação (D2) p50 / p95 | RSS antes → pico → depois (MB) | CPU média / pico |
|---|---|---|---|---|---|---|---|---|---|
| Linha de base (servidor novo) | 1 | — | 1 | 0% | 0,43 | 1,49 | 0,22 | 67 → 279 | — |
| **Rajada (D1)** | **200** | **mesmo instante** | **103** | **48,5%** | **206 / 248** | **206 / 249** | **51 / 99** | **278 → 3.601 → 3.160** | **104% / 116%** |
| Rampa de 1 min | 200 | 60 s, 3,3 por s | 111 | 44,5% | 158 / 190 | 159 / 191 | 57 / 104 | 278 → 3.614 → 3.009 | 104% / 116% |
| Depois da rajada | 1 | — | 1 | 0% | 0,13 | 0,99 | 0,75 | 2.790 | — |
| Depois da rajada | 10 | mesmo instante | 10 | 0% | 10,3 / 13,6 | 10,7 / 16,5 | 6,3 / 6,4 | 2.684 → 2.734 | 95% / 110% |

Leitura:

- **A capacidade é de cerca de 0,6 página por segundo.** Dez usuários levaram 17,9 s no total, quase 10 × 1,7 s. Na rampa de 1 minuto chegam 3,3 sessões por segundo, cinco vezes a capacidade, e a fila cresce até estourar o tempo limite.
- **A espera começa antes do script.** Na rajada, o próprio `GET /` do HTML estático teve p50 de 85 s. O processo está tão ocupado que nem o servidor HTTP responde.
- **A CPU fica presa em cerca de 100%, um núcleo.** O processo Python executa as sessões em threads sob o GIL, então os outros 11 núcleos ficaram ociosos.
- **A memória não volta.** Cada sessão deixa cerca de 16 MB, e o RSS ficou acima de 2,7 GB minutos depois do teste. O servidor fica mais lento depois da carga: a interação passou de 0,22 s para 0,75 s, provavelmente pelo custo do coletor de lixo num heap de 3 GB.
- **A interação (D2) também falha sob carga.** Com 50 a 100 s de p50, a meta de 1 s fica fora de alcance enquanto houver pico.

## Onde está o custo de uma sessão

Perfil de uma execução do script com `AppTest` e `cProfile`, com cache aquecido:

- O script inteiro (`app.py` e `src/dashboard.py`) leva **0,22 a 0,3 s**. Os maiores itens são o layout dos gráficos Plotly (`viz.apply_layout`, 72 ms), as barras de probabilidade (39 ms) e o histórico recente dos 20 times (35 ms).
- `store.load_projection()`, chamado sem cache em `app.py:42`, custa **15 ms** e **5,5 MB** por cópia.
- Num servidor real, a sessão nova custa de 1,0 a 1,5 s. A diferença em relação ao script vem de serializar os ~150 elementos (figuras Plotly em JSON, tabelas em Arrow) e enviá-los pelo websocket, tudo no mesmo processo.

## Experimento: cache da projeção em `app.py`

O achado D1 da árvore apontava o `load_projection()` sem cache em `app.py:42`. Para medir o efeito, rodei uma cópia do código, fora do repositório, com essa única mudança: a projeção num `st.cache_resource` com balde de 300 s, igual ao de `src/dashboard.py:52`.

| Execução | Original | Com cache | Ganho |
|---|---|---|---|
| 1 usuário, página completa (aquecido) | 0,99 s | 0,35 s | 2,8× |
| 1 usuário, interação | 0,22 a 0,75 s | 0,19 s | até 3,9× |
| 10 usuários, tempo total | 17,9 s | 6,7 s | 2,7× |
| 10 usuários, RSS de pico | 2.734 MB* | 445 MB | — |
| **200 em rajada, falhas** | **48,5%** | **38,5%** | −10 p.p. |
| 200 em rajada, primeiro conteúdo p95 | 248 s | 227 s | −8% |
| 200 em rajada, RSS de pico | 3.601 MB | 2.424 MB | −33% |

\* O original já carregava o heap da rajada anterior.

- **Conclusão**: o cache vale a pena. É uma mudança de poucas linhas que quase triplica a vazão e corta um terço da memória. **Ele não resolve D1.** Mesmo a 0,35 s por sessão, 200 sessões serializadas somam cerca de 70 s de CPU, longe da meta de p95 ≤ 3 s.
- **Atualização do achado D1**: continua sendo **risco**. A causa dominante não é o `json.loads` em si, e sim a decisão de **renderizar cada visita no servidor, num processo único**.

## Conclusões para o ATAM

1. **D1 é risco confirmado por medição.** O sistema atende com folga de 1 a 2 acessos simultâneos (p95 ≤ 3 s). Com 10, o p95 já é de 5 a 16 s. Com 200, falha para quase metade.
2. **O risco reforça o trade-off de A4.** A saída natural é ter mais processos, com réplicas ou vários workers atrás de um balanceador com sessão fixa. Isso esbarra no JSON em volume preso a uma única instância.
3. **O risco reforça D3.** Se a atualização de 20.000 simulações começar durante esse pico, ela disputa o mesmo núcleo que já está saturado.
4. **Novo achado: crescimento de memória sem devolução.** Sessões encerradas deixam cerca de 2,5 GB residentes. Num plano com limite de memória, a próxima onda de acessos pode levar o contêiner a OOM, o que liga o risco de desempenho ao de disponibilidade (A2).

## Recomendações, em ordem de esforço

| # | Ação | Efeito esperado | Esforço |
|---|---|---|---|
| 1 | Pôr em cache a leitura da projeção em `app.py:42` (medido acima) | ~2,7× de vazão, −33% de memória | Baixo |
| 2 | Limitar o RSS do contêiner e reiniciar ao estourar; avaliar `server.maxCachedMessageAge` e o tempo de retenção de sessões | Evita OOM silencioso depois de picos | Baixo |
| 3 | Rodar N processos Streamlit (um por núcleo) atrás de um proxy com sessão fixa, todos lendo o mesmo volume | Vazão ~N× no mesmo contêiner | Médio |
| 4 | Servir a parte pública como **site estático** gerado pelo atualizador (HTML/JSON pré-computado em CDN), deixando o Streamlit só para o `/admin` | A carga deixa de depender do servidor; 200 acessos viram 200 GETs de arquivo em cache | Alto |

A opção 4 é a direção do projeto "Remo nos Campeonatos" (site estático lendo um banco pela API REST). O resultado deste teste é o argumento quantitativo para essa mudança.

## Limitações

- Cliente e servidor estavam na mesma máquina. Em produção, a rede soma latência e o Railway pode ter menos CPU e RAM. Os números aqui são o melhor caso.
- Só a página padrão (Brasileirão, time Remo) foi exercitada. As páginas de mata-mata e das ligas estrangeiras não entraram.
- O cliente usa um *pool* de threads para o `GET /`. Isso não limita o resultado: o servidor demorou dezenas de segundos para responder, e o cliente ficou quase ocioso.
- A interação foi simulada com um novo `rerun_script` sem mudar o estado do seletor. O custo é o mesmo de uma re-renderização.

## Como reproduzir

```bash
.venv/bin/python scripts/update_data.py            # gera data/projection.json
.venv/bin/streamlit run app.py --server.headless true --server.port 8501 &
PID=$(pgrep -f "streamlit run app.py" | head -1)
.venv/bin/python scripts/loadtest.py --users 1   --pid $PID --out /tmp/aquece.json
.venv/bin/python scripts/loadtest.py --users 200 --ramp 0  --pid $PID --out /tmp/rajada.json
.venv/bin/python scripts/loadtest.py --users 200 --ramp 60 --pid $PID --out /tmp/rampa.json
```

Reinicie o Streamlit entre as execuções de 200 usuários, porque a memória retida da anterior distorce a seguinte.

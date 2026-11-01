-- Tabelas lidas pelo site (GitHub Pages) e escritas pelo GitHub Actions.
-- Idempotente: o script de sincronização roda este arquivo a cada execução.
-- O banco é compartilhado: tudo deste projeto usa o prefixo remo_.

drop table if exists remo_atualizacao;  -- substituída por remo_ligas

create table if not exists remo_ligas (
  liga           text primary key,            -- 'serie_a', 'serie_b'
  nome           text not null,
  zonas          jsonb not null default '[]', -- [{nome, cor, posicoes: [1, 2, ...]}]
  rodada_atual   integer,
  atualizado_em  timestamptz not null
);

create table if not exists remo_clubes (
  liga        text not null references remo_ligas(liga),
  id          integer not null,
  nome        text not null,
  abreviacao  text,
  escudo      text,
  primary key (liga, id)
);

create table if not exists remo_partidas (
  liga        text not null references remo_ligas(liga),
  partida_id  bigint not null,
  rodada      integer not null,
  data        timestamptz,
  casa_id     integer not null,
  fora_id     integer not null,
  gols_casa   integer,
  gols_fora   integer,
  encerrada   boolean not null default false,
  primary key (liga, partida_id)
);

-- Leitura pública (chave publishable), escrita só pela conexão do Actions.
alter table remo_ligas    enable row level security;
alter table remo_clubes   enable row level security;
alter table remo_partidas enable row level security;

drop policy if exists leitura_publica on remo_ligas;
drop policy if exists leitura_publica on remo_clubes;
drop policy if exists leitura_publica on remo_partidas;
create policy leitura_publica on remo_ligas    for select to anon, authenticated using (true);
create policy leitura_publica on remo_clubes   for select to anon, authenticated using (true);
create policy leitura_publica on remo_partidas for select to anon, authenticated using (true);

grant select on remo_ligas, remo_clubes, remo_partidas to anon, authenticated;

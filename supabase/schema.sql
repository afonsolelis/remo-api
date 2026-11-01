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

-- Copas e estaduais: fases (grupos/mata-mata), chaves e pênaltis.
alter table remo_ligas    add column if not exists tipo text not null default 'pontos';  -- 'pontos' ou 'copa'
alter table remo_ligas    add column if not exists fases jsonb not null default '[]';     -- [{nome, tipo, grupos: [...]}]
alter table remo_partidas add column if not exists fase text;
alter table remo_partidas add column if not exists fase_ordem integer;
alter table remo_partidas add column if not exists chave text;     -- grupo ou chave do mata-mata
alter table remo_partidas add column if not exists pen_casa integer;
alter table remo_partidas add column if not exists pen_fora integer;

-- Notícias do ge por clube (as mais recentes de cada um).
create table if not exists remo_noticias (
  clube_id      integer not null,
  noticia_id    text not null,
  titulo        text not null,
  resumo        text,
  url           text not null,
  imagem        text,
  publicado_em  timestamptz not null,
  primary key (clube_id, noticia_id)
);

-- Leitura pública (chave publishable), escrita só pela conexão do Actions.
alter table remo_ligas    enable row level security;
alter table remo_clubes   enable row level security;
alter table remo_partidas enable row level security;
alter table remo_noticias enable row level security;

drop policy if exists leitura_publica on remo_ligas;
drop policy if exists leitura_publica on remo_clubes;
drop policy if exists leitura_publica on remo_partidas;
drop policy if exists leitura_publica on remo_noticias;
create policy leitura_publica on remo_ligas    for select to anon, authenticated using (true);
create policy leitura_publica on remo_clubes   for select to anon, authenticated using (true);
create policy leitura_publica on remo_partidas for select to anon, authenticated using (true);
create policy leitura_publica on remo_noticias for select to anon, authenticated using (true);

grant select on remo_ligas, remo_clubes, remo_partidas, remo_noticias to anon, authenticated;

notify pgrst, 'reload schema';

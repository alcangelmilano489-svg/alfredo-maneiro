create table if not exists public.mensajes_contacto (
    id uuid primary key default gen_random_uuid(),
    nombre_completo text not null
        check (char_length(btrim(nombre_completo)) between 1 and 120),
    apellido text not null
        check (char_length(btrim(apellido)) between 1 and 100),
    email text not null
        check (char_length(email) between 3 and 254),
    telefono text not null
        check (char_length(btrim(telefono)) between 7 and 32),
    mensaje text not null
        check (char_length(btrim(mensaje)) between 1 and 3000),
    created_at timestamptz not null default now()
);

alter table public.mensajes_contacto enable row level security;
revoke all on table public.mensajes_contacto from public, anon, authenticated;
grant all on table public.mensajes_contacto to service_role;

create index if not exists mensajes_contacto_created_at_idx
    on public.mensajes_contacto (created_at desc);

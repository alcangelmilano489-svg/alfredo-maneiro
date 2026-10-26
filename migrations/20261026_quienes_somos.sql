alter table public.contenido_secciones
    drop constraint if exists contenido_secciones_seccion_check;

alter table public.contenido_secciones
    add constraint contenido_secciones_seccion_check
    check (seccion in ('vida', 'obra', 'quienes-somos'));

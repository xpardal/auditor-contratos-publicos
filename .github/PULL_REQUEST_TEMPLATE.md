## Descripción

<!-- Qué cambia esta PR y por qué. -->

## Tipo de cambio

- [ ] Corrección de error
- [ ] Nueva funcionalidad
- [ ] Mejora de rendimiento o usabilidad
- [ ] Refactor sin cambio de comportamiento
- [ ] Documentación

## Cómo se ha probado

- [ ] `python -m py_compile app.py core/*.py`
- [ ] `pytest -q`
- [ ] Verificación manual en `streamlit run app.py`

Indica qué fuentes de datos se han usado para la verificación (PLACSP o Tribunal de Cuentas).

## Checklist

- [ ] Mantiene la app **local-first** (no añade scraping autenticado ni envío a la nube).
- [ ] Mantiene el lenguaje de *indicios estadísticos* (no acusaciones).
- [ ] Añade o actualiza tests si toca `core/`.
- [ ] Añade o actualiza documentación si cambia el comportamiento visible.
- [ ] No incluye datos personales ni archivos pesados en el repo.

## Issues relacionados

Closes #

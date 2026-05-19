# Contribuir

Gracias por mejorar el Auditor de Contratos Públicos. El proyecto prioriza cambios reproducibles, explicables y útiles para investigación periodística o académica.

## Preparación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # dependencias de la app
pip install -r requirements-dev.txt      # pytest, pyinstaller, etc.
pytest -q
```

En Windows, activa el entorno con `.venv\\Scripts\\activate`.

> Los **usuarios finales** no necesitan instalar `requirements-dev.txt`: solo se
> usa para ejecutar tests, contribuir y construir binarios distribuibles.

## Antes de proponer cambios

- Mantén la app local-first: no subas datos a servicios externos.
- No añadas scraping de formularios autenticados ni automatización de sesiones.
- Conserva la metodología: las alertas son indicios estadísticos, no acusaciones.
- Añade tests cuando cambies parsers, radar, descargadores o visualizaciones.
- No incluyas en Git ficheros descargados, cachés, bases `.accdb` pesadas ni datos personales.
- Conserva la fórmula "Esta aplicación es parte de los proyectos de I+D+i" con los nombres completos de *Inteligencia artificial en medios digitales en España: efectos y roles* (PID2024-156034OB-C22) y *XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación* (PDC2025-166024-I00), además de la autoría, cuando añadas pantallas o documentación.

## Qué debe entrar en el repositorio

Incluye código, tests, documentación, lanzadores, workflows, licencias,
metadatos de cita y archivos de configuración necesarios para ejecutar o
validar la aplicación.

No incluyas `.venv/`, `.cache/`, `data/`, `exports/`, `reports/`, ficheros
`.accdb`, `.parquet`, informes generados, credenciales, `.env`, capturas
temporales ni documentos con datos personales. Esos patrones están cubiertos por
[.gitignore](.gitignore). Cualquier usuario debe poder clonar el proyecto,
reconstruir el entorno con `requirements.txt` y descargar o cargar sus propias
fuentes desde la interfaz.

## Comprobaciones recomendadas

```bash
python -m py_compile app.py core/*.py
pytest -q
streamlit run app.py
```

## Licencia

Al contribuir aceptas que tus cambios se publiquen bajo la licencia MIT del proyecto.

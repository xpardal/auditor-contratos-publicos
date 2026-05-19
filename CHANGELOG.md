# Changelog

Todas las novedades relevantes de este proyecto se documentan en este archivo. El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y el versionado [SemVer](https://semver.org/lang/es/).

## [1.0.1] - 2026-05-19

### Corregido

- Red de relaciones de la interfaz: queda un único grafo dinámico embebido con `st.iframe`, sin duplicado Plotly superior ni API obsoleta.
- Informes HTML/PNG: se sustituyen visualizaciones no aptas para exportación por rankings estáticos legibles y se filtran figuras vacías.
- Informes PDF: tablas con textos largos en celdas envolventes para evitar solapes.
- PLACSP: la caché `.cache/` se recrea automáticamente si se borra durante una sesión.
- Tribunal de Cuentas: consultas DuckDB robustas ante códigos numéricos inferidos desde CSV.

### Documentación

- Guía de uso, README, metadatos y cabeceras actualizados con el marco correcto: esta aplicación es parte de los proyectos de I+D+i PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
- Proyecto preparado para repositorio privado: se documenta qué debe subirse y qué queda excluido por `.gitignore`.

## [1.0.0] - 2026-05-14

### Añadido

- Primera versión funcional del Auditor de Contratos Públicos.
- Carga de datos PLACSP (.atom y descarga oficial paginada).
- Análisis del Tribunal de Cuentas (CSV + .accdb vía mdbtools + DuckDB).
- Modo *Archivo individual* con escáner de patrones (CSV/PDF/JSON/XML).
- Radar de indicios de fraccionamiento de contratos menores (LCSP 9/2017).
- Visualizaciones interactivas Plotly (radar, treemap, barras, red, evolución).
- Informe HTML autoportante reproducible.
- Lanzadores doble clic para macOS, Linux y Windows.
- Empaquetado binario opcional (PyInstaller) para los tres SO con workflow de release automatizado.
- Documentación académica completa: `docs/GUIA_USO.md`, `docs/ARCHITECTURE.md`, memoria TFG y informe de mejoras.
- Suite de 53 tests (`pytest`) y CI en GitHub Actions (Python 3.10 y 3.12).

### Notas

- Esta aplicación es parte de los proyectos de I+D+i PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
- Coautoría: Xoán Xosé Pardal Pérez (autor principal) y Alberto Quian (apoyo metodológico y técnico).

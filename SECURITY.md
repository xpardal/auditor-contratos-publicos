# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
|---------|---------|
| 1.0.x   | ✅ activa |
| < 1.0   | ❌ no soportada |

## Cómo reportar una vulnerabilidad

Si detectas una vulnerabilidad de seguridad en el Auditor de Contratos Públicos, **no la publiques en un *issue* público**. En su lugar:

1. Abre un *Security Advisory* privado desde la pestaña **Security → Advisories** del repositorio en GitHub, **o**
2. Envía un correo a la persona autora de contacto indicada en [`AUTHORS.md`](AUTHORS.md).

Incluye, si es posible:

- Descripción del problema y su impacto.
- Pasos para reproducirlo.
- Versión y sistema operativo en los que has observado el comportamiento.
- Cualquier mitigación temporal que hayas detectado.

Nos comprometemos a:

- Confirmar la recepción en un plazo razonable.
- Investigar y comunicar el plan de respuesta.
- Publicar un parche y un aviso público una vez la corrección esté disponible.

## Buenas prácticas para usuarios

- La aplicación es **local-first**: no envía datos a la nube. Mantén actualizado tu Python y tus dependencias (`pip install -U -r requirements.txt`).
- No expongas la app de Streamlit a internet sin un proxy con autenticación.
- Las alertas son **indicios estadísticos**, no acusaciones; cualquier publicación derivada debe verificarse con documentación oficial.

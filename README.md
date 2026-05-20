# Local AI Studio - Landing de Producto

Landing page de producto para una plataforma local-first de IA, automatización y dashboards. El sitio está preparado como demo estática, sin dependencias externas de ejecución: no usa CDNs, fuentes remotas ni librerías de animación remotas.

## Cómo usar
1. Abre `index.html` en tu navegador.
2. Edita `assets/logo.svg` y `assets/favicon.svg` si necesitas personalizar la marca.
3. Para generar un ZIP de entrega, ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File tools/package-site.ps1
```

## Verificación

Ejecuta la comprobación técnica del paquete con:

```powershell
powershell -ExecutionPolicy Bypass -File tools/check-project.ps1
```

## Estructura

```text
index.html
landing-local-ai.html   # alias heredado que redirige a index.html
assets/
  favicon.svg
  logo.svg
css/
  styles.css
js/
  main.js
tools/
  check-project.ps1
  package-site.ps1
vercel.json
netlify.toml
```

## Secciones del producto

- Hero con posicionamiento Local-first, CTA de demo y resumen operativo.
- Producto: capacidades principales de orquestación AI, dashboards y plantillas SaaS.
- Flujo: pasos para pasar de prototipo local a experiencia comercial.
- Privacidad: argumentos de control local y reducción de dependencias externas.
- Stack recomendado: recursos para evolucionar hacia prototipo funcional.
- Demo: formulario local simulado que no envía datos.

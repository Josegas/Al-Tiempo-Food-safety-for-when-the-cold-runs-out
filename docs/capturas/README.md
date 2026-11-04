# Capturas para el artículo y el video

Las capturas de la demo se tomaron automáticamente (Chromium sin pantalla, tamaño de celular 390×844)
contra la demo en vivo, el 2026-11-04. Las de la consola se generaron con APIs de AWS (datos reales).

| Archivo | Qué muestra | Cómo se obtuvo |
|---|---|---|
| `01-demo-home.png` | Inicio de la demo: banner, EN/ES, botones de escenarios | Playwright, demo en vivo |
| `02-safe-window-reminder.png` | Ventana segura → recordatorio que llega | Playwright, esperó el recordatorio real |
| `03-shelter.png` | Plan del albergue de 120 personas | Playwright |
| `09-outage.png` | Modo apagón | Playwright |
| `10-danger-signs.png` | Señales de alarma → 911 | Playwright |
| `11-baby-rice.png` | Bebé + arroz de hace 5 h → deséchalo | Playwright |
| `07-cloudwatch-dashboard.png` | Dashboard `al-tiempo` (4 gráficas) | CloudWatch `GetMetricWidgetImage` |
| `06-github-actions.png` | **Pendiente:** Actions con Deploy en verde (tras arreglar OIDC) | — |

En el artículo, la salida de `make smoke` y del presupuesto va como **texto** (mejor para la calificación con IA).
Imágenes generadas por código: `docs/img/` (`make figures`).

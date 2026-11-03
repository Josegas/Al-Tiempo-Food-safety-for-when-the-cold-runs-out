# Development diary

## 2026-11-03 14:30
- Qué intenté: verificar automáticamente las fuentes oficiales de cada regla (FSIS, CDC, NHS, OMS).
- Qué pasó: FSIS y FoodSafety.gov devolvieron 403 a clientes automáticos; la URL de CDC de fórmula dio 404; la página de "Cinco claves" de la OMS no trae los límites (están en el PDF del manual).
- Cómo lo supe: respuesta HTTP de cada página.
- Qué decidí: marcar esas reglas `unverified: true`. El motor las rechaza salvo con `ALLOW_UNVERIFIED_RULES=true` (dev/demo) y la CI bloquea releases (`scripts/check_rules.py --strict`) hasta verificarlas a mano en el navegador.
- Extra: la hoja de la OMS (4 junio 2026) trae cifras nuevas: 866 millones enfermos/año, 1.52 millones de muertes, 143 000 muertes de menores de 5 años (2021). Las de CLAUDE.md (600 M / 420 000 / 125 000) están desactualizadas.

## 2026-11-03 15:20 — Error real medido #1 (unsafe answer)
- Qué intenté: prueba de humo contra Bedrock (Nova Lite) con "Can I give my baby the rice I cooked 5 hours ago?".
- Qué pasó: el agente respondió "eat the rice before 13:00". Inseguro: el arroz ya llevaba 5 h fuera.
- Cómo lo supe: prueba manual de punta a punta; el verificador no lo bloqueó porque 13:00 sí venía de la herramienta (el error estaba en la ENTRADA, no en la salida).
- Causa: el modelo no pasó la hora de cocción y la herramienta asumía "recién cocinado = ahora".
- Qué decidí: (1) nuevo parámetro `minutes_ago` calculado en código; (2) si no hay hora de cocción, peor caso = desechar; (3) el motor devuelve `status: discard_now | eat_before_deadline`; (4) la plantilla segura del verificador dice "deséchalo ahora" si ya expiró; (5) tests de regresión `test_baby_rice_five_hours_ago_is_discard` y `test_unknown_cooking_time_is_discard`.
- Resultado: misma pregunta → "discard the rice now". Medir antes/después en evals.

## 2026-11-03 15:30
- Qué intenté: usar Claude Haiku 4.5 en Bedrock.
- Qué pasó: `ResourceNotFoundException: Model use case details have not been submitted`.
- Qué decidí: modelo por defecto `us.amazon.nova-lite-v1:0` (barato, funciona). Opcional: llenar el formulario de Anthropic en la consola de Bedrock para comparar.

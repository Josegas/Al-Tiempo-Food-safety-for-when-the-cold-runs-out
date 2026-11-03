# DevOps en Al Tiempo — qué hay y qué significa (para tu CV)

## Ya implementado
| Práctica | Archivo | Qué hace en 1 línea | Cómo lo dices en el CV/entrevista |
|---|---|---|---|
| Integración continua (CI) | `.github/workflows/ci.yml` | En cada push/PR corre lint, tests y cobertura en una máquina limpia de GitHub. | "Pipeline de CI en GitHub Actions con quality gates (lint, tests, cobertura)." |
| Quality gate de seguridad | mismo archivo, job `security` | Busca secretos filtrados (gitleaks), librerías con vulnerabilidades (pip-audit) y código inseguro (reglas S de ruff/bandit). | "Shift-left security: escaneo de secretos, dependencias y SAST en CI." |
| Policy as code | `scripts/check_rules.py` + job `release-gate` | Un release no sale si una regla de salud no está verificada en su fuente oficial. | "Release gates basados en políticas versionadas en el repo." |
| Dependabot | `.github/dependabot.yml` | Abre PRs solo para actualizar librerías y actions. | "Gestión automatizada de dependencias." |
| Tests de regresión de seguridad | `tests/` | Cada error real encontrado queda como test para que no vuelva. | "Testing de regresión sobre fallas reales de un agente de IA." |
| Logs estructurados | `agent/app.py` | Cada respuesta deja un JSON con latencia, tokens y bloqueos del verificador → CloudWatch. | "Observabilidad: logs estructurados para métricas de latencia y costo." |
| Config por variables de entorno | `.env.example` | El mismo código corre en demo, local y AWS (12-factor). | "Aplicación 12-factor." |
| Makefile | `Makefile` | Un comando para instalar, probar y chatear igual en tu PC y en CI. | — |

## Siguiente (lo armo en el próximo paso)
1. **Infraestructura como código (AWS CDK en Python):** DynamoDB con TTL, Lambda de recordatorios, EventBridge Scheduler, SNS, S3 + CloudFront, API Gateway, alarmas de CloudWatch y AWS Budgets. Todo se crea/borra con un comando.
2. **Despliegue continuo (CD) con OIDC:** GitHub Actions se autentica en AWS **sin llaves guardadas** (rol IAM con confianza OIDC) y despliega al hacer merge a `main`.
3. **Mínimo privilegio:** roles IAM separados para el agente, la Lambda y el pipeline.
4. **Dashboard + alarmas:** errores, latencia y bloqueos del verificador.
5. **Evals en CI:** los escenarios de `evals/` corren en un workflow manual y publican el % de aciertos.

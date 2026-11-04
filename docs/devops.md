# DevOps en Al Tiempo — qué hay, cómo se despliega y qué significa (para tu CV)

## Arquitectura en AWS
```
Celular/navegador ──HTTPS──► CloudFront ──► S3 privado (web, OAC)
                               └─ /api/* ─► API Gateway HTTP API (límite: 10 req/s, ráfaga 20)
                                              └─► Lambda API (tope diario de conversaciones en DynamoDB)
                                                    └─► AgentCore Runtime (agente Strands, auth IAM, ARM64)
                                                          ├─► Bedrock: Nova 2 Lite vía *application inference profile* (etiquetado)
                                                          ├─► Open-Meteo (pronóstico por hora; demo usa fixtures)
                                                          └─► EventBridge Scheduler (recordatorio de una sola vez, se borra solo)
                                                                └─► Lambda recordatorio ─► DynamoDB (TTL 7 días) / SNS SMS (opcional)
Observabilidad: logs JSON sin datos personales (retención 7 días), dashboard "al-tiempo", 3 alarmas → correo.
Costos: presupuesto por etiqueta project=al-tiempo + "kill switch" (Budget Action) que bloquea Bedrock/AgentCore al 100%.
```

## Dos stacks de CDK (infra/)
| Stack | Quién lo despliega | Qué tiene |
|---|---|---|
| `AlTiempoAccess` | Un admin, **una vez** (`make deploy-access`) | Usuario IAM `al-tiempo-dev` + grupo con política de mínimo privilegio; rol `al-tiempo-github-deploy` (OIDC, solo rama `main`); presupuesto mensual de $10 con alertas por correo; tema SNS de alarmas |
| `AlTiempoApp` | `al-tiempo-dev` (`make deploy`) o GitHub Actions | Todo el producto (ver arquitectura) |

## Cómo desplegar (orden)
```bash
make diff-access      # admin: revisa qué se crea (solo lectura)
make deploy-access    # admin: crea accesos y presupuesto; CDK te pide aprobar los cambios de IAM (y)
make dev-profile      # admin: crea la llave de al-tiempo-dev en el perfil "al-tiempo" (no imprime secretos)
make deploy           # ya con al-tiempo-dev: empaqueta el agente y despliega la app (aprueba con y)
make outputs          # URL de la demo
make smoke            # prueba de punta a punta del sistema desplegado
make activate-cost-tag  # admin: activa la etiqueta "project" para el presupuesto (puede tardar 24 h)
```
Despliegue continuo: después de configurar `gh variable set AWS_DEPLOY_ROLE_ARN ...`, cada merge a `main`
que toque el agente/infra/web despliega solo (`.github/workflows/deploy.yml`) y corre un smoke test.

## Decisiones (y por qué)
| Decisión | Por qué |
|---|---|
| AgentCore con **código en zip** (direct code deployment) en vez de contenedor | El runtime es ARM64; la laptop es x86. El zip se arma con wheels `aarch64` sin Docker ni emulación; es **determinista** (mismo código → mismo hash → no redeploy). |
| Usuario IAM por proyecto **con mínimo privilegio** | Igual que en tus proyectos anteriores, pero sin AdministratorAccess: solo puede desplegar a través de los roles de CDK (todo cambio pasa por CloudFormation y queda auditado), probar el agente, leer logs y costos. |
| GitHub Actions con **OIDC** | No hay llaves de AWS guardadas en GitHub. AWS solo acepta tokens de la rama `main` de este repo. |
| Red **PUBLIC** del runtime (no VPC) | VPC requiere NAT/endpoints (~$30+/mes). La entrada sigue protegida: solo se invoca con IAM (la Lambda). Siguiente paso documentado: VPC. |
| Presupuesto **por etiqueta** + Budget Action | El presupuesto solo avisa; el kill switch sí detiene el gasto (aplica una política DENY a los roles del runtime y de la API). Los recursos llevan `project=al-tiempo`. |
| Application inference profile | Permite ver el gasto de Bedrock de este proyecto separado de los demás en Cost Explorer. |
| Throttling + tope diario + `max_tokens` | Un bot o un bug no puede gastar los créditos. |
| Logs sin texto del usuario, retención 7 días, TTL 7 días en DynamoDB, ubicación redondeada (~1 km) | Privacidad por diseño. |

## Prácticas para el CV
| Práctica | Dónde | Frase para el CV |
|---|---|---|
| Infraestructura como código | `infra/` (AWS CDK, Python) | "Infraestructura 100% en AWS CDK: 2 stacks separados por responsabilidad (acceso/costos vs. producto)." |
| CI | `.github/workflows/ci.yml` | "Quality gates en CI: lint, 100+ tests, cobertura, reglas verificadas, escaneo de secretos y dependencias." |
| CD sin secretos | `.github/workflows/deploy.yml` | "Despliegue continuo con GitHub Actions + OIDC (sin llaves de larga duración) y smoke test post-deploy." |
| Validación de IaC en PRs | `.github/workflows/infra-check.yml` | "cdk synth en cada PR para detectar errores de infraestructura antes del merge." |
| Mínimo privilegio | `infra/stacks/access_stack.py` | "Diseñé políticas IAM de mínimo privilegio por proyecto y roles con protección *confused deputy*." |
| FinOps | presupuesto + kill switch + inference profile | "Guardarraíles de costo: presupuesto por etiqueta, freno automático y costo por conversación medido ($0.0023)." |
| Observabilidad | dashboard + alarmas + logs JSON | "Observabilidad con CloudWatch: métricas, alarmas a correo y logs estructurados sin PII." |
| Evals como gate de calidad | `evals/` | "Selección de modelo basada en evals (44% → 100%)." |

## Pendiente / siguiente nivel (honesto)
- **Cuota de Lambda:** la cuenta permite 10 ejecuciones simultáneas (cuenta nueva; lo normal es 1,000). La prueba de carga (`make loadtest`) lo mostró: en ráfagas, Lambda responde 503. Pedir el aumento (gratis): `aws service-quotas request-service-quota-increase --service-code lambda --quota-code L-B99A9384 --desired-value 1000`.
- Runtime en VPC con endpoints privados (costo extra).
- `cdk diff` automático en los PR (requiere un rol de solo lectura para PRs).
- Cifrado KMS propio para los logs del runtime.
- SMS: el código está listo (`smsEnabled`), pero hay que verificar el número en el sandbox de SNS.

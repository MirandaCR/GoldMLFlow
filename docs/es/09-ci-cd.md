# 09 · CI/CD con GitHub Actions

> 🌐 [English](../en/09-ci-cd.md) · **Español** · ⬅️ [08 · Docker](08-docker.md) · ➡️ [10 · Monitoreo](10-monitoring.md)

| | |
|---|---|
| 🍳 **Analogía** | 🕵️ El inspector de sanidad revisa cada cambio **antes** de que el restaurante abra con él; luego 🚚 el camión nuevo se entrega automáticamente |
| 🎯 **Objetivo** | Cada push se prueba solo; solo los cambios en verde se publican |
| 🏭 **Archivos** | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), [`.github/workflows/cd.yml`](../../.github/workflows/cd.yml) |
| 🌐 **Verlo** | https://github.com/MirandaCR/GoldMLFlow/actions |

## 🤔 CI vs CD

| | **CI**: Integración Continua | **CD**: Entrega Continua |
|---|---|---|
| Pregunta | "¿Este cambio es seguro?" | "¡Publícalo!" |
| Cuándo | en cada push y pull request | solo cuando el CI está ✅ en `main` |
| Hace | lint, pruebas, pipeline, control de calidad, build de Docker | construye y publica la imagen Docker |
| Resultado | ✅ / ❌ junto a cada commit | `ghcr.io/mirandacr/goldmlflow:latest` |

## 🔄 El flujo completo del robot

```mermaid
flowchart TD
    DEV[👩‍💻 git push / pull request] --> CI
    subgraph CI[⚙️ CI · ci.yml · ubuntu-latest]
        J1[① Lint ruff + pruebas pytest<br/>incluye la prueba de fuga de datos]
        J2[② Pipeline de humo con datos de muestra<br/>validar → features → entrenar → promover → drift]
        J3[③ Control de calidad del modelo<br/>¿el campeón del repo cumple las reglas?]
        J4[④ Build de Docker + prueba de humo<br/>el contenedor responde /health y /model-info]
        J1 --> J2
        J1 --> J3
        J2 --> J4
        J3 --> J4
    end
    J4 -->|todo ✅ en main| CD
    subgraph CD[📦 CD · cd.yml]
        B[Construir imagen] --> P[Publicar en ghcr.io<br/>tags: latest · sha del commit · model-v2]
    end
    J4 -->|algún ❌| STOP[🛑 X roja en el commit<br/>no se publica nada]
```

## 🔎 Cada trabajo del CI en palabras simples

| Trabajo | Qué detecta |
|---|---|
| **① Lint y pruebas** | código desordenado, funciones rotas, **fuga de datos**, errores de la API |
| **② Pipeline de humo** | "todo el pipeline sigue corriendo de punta a punta" (con la muestra de 4.000 velas en Git: el robot no tiene MT5 ni acceso a tu almacenamiento DVC local) |
| **③ Control de calidad** | alguien subió un **modelo peor** de lo que permiten las reglas |
| **④ Build de Docker** | la imagen no se construye o el contenedor no responde |

Los resultados aparecen en el **Summary** del trabajo (tabla de métricas + chequeos del campeón) y se pueden descargar los artefactos (reportes, ejecuciones de MLflow).

## 📦 CD: publicar la imagen

Cuando el CI está en verde en `main`, `cd.yml`:
1. lee la versión del campeón en `models/champion/metadata.json`
2. construye la imagen y la sube al **GitHub Container Registry** con 3 tags: `latest`, el SHA del commit y `model-v2`
3. cualquiera puede ejecutarla sin clonar nada:

```powershell
docker run -p 8000:8000 ghcr.io/mirandacr/goldmlflow:latest
```

> 🔐 No hacen falta secretos: el `GITHUB_TOKEN` integrado tiene permiso `packages: write` (declarado en el workflow).
> La primera vez el paquete es **privado**; hazlo público en GitHub → tu perfil → Packages → goldmlflow → Package settings.

## 🧭 El día a día con CI/CD

```mermaid
gitGraph
    commit id: "campeón v1"
    branch feature/nuevas-pistas
    checkout feature/nuevas-pistas
    commit id: "agregar pista ATR"
    commit id: "dvc repro → v3"
    checkout main
    merge feature/nuevas-pistas id: "PR ✅ CI verde"
    commit id: "CD → ghcr.io:model-v3"
```

1. Crea una rama, cambia código o parámetros, `dvc repro`, `dvc push`.
2. `git push` → abre un Pull Request → corre el CI.
3. ✅ verde → fusionar → el CD publica la nueva imagen automáticamente.

## 💡 Para ir más allá (mejoras del mundo real)

| Mejora | Cómo |
|---|---|
| El CI entrena con **todos** los datos | usar un remote DVC en la nube (S3/GCS) + `dvc pull` en el CI con secretos |
| Reentrenar de forma programada | agregar `on: schedule: - cron: "0 6 * * 1"` |
| Comentar métricas en el PR | [CML](https://cml.dev) (`cml comment create`) |
| Desplegar en un servidor | después del push, un paso `ssh` / Cloud Run / Kubernetes |

---
⬅️ [08 · Docker](08-docker.md) · ➡️ [10 · Monitoreo y data drift](10-monitoring.md)

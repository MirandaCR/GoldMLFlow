# 13 · Glosario y preguntas frecuentes

> 🌐 [English](../en/13-glossary-faq.md) · **Español** · ⬅️ [12 · Notebook → producción](12-notebook-to-production.md) · [🏠 README](../../README.es.md)

## 📖 Glosario (en palabras simples)

| Término | En palabras simples |
|---|---|
| **MLOps** | Prácticas para llevar modelos de ML de un notebook a producción de forma confiable y repetible |
| **Vela (OHLCV)** | Resumen de 1 hora de mercado: Apertura, Máximo, Mínimo, Cierre, Volumen |
| **H1** | Marco temporal de 1 hora por vela |
| **Clasificación binaria** | Predecir una de dos respuestas: SUBE (1) o BAJA (0) |
| **Feature (pista)** | Un número que se le da al modelo como pista |
| **Target / etiqueta** | La respuesta correcta que el modelo debe aprender |
| **Baseline** | El modelo razonable más tonto (siempre SUBE). Cualquier modelo real debe vencerlo |
| **Fuga de datos (data leakage)** | Una pista que esconde información del futuro → resultados falsamente buenos |
| **Sobreajuste (overfitting)** | Memorizar el pasado (ruido) en vez de aprender patrones |
| **Validación walk-forward** | Validación que siempre entrena con el pasado y prueba con lo que viene |
| **ROC-AUC** | Qué tan bien ordena el modelo las subidas por encima de las bajadas. 0,5 = moneda, 1,0 = perfecto |
| **Pipeline (DVC)** | Cadena de etapas con entradas y salidas declaradas; re-ejecuta solo lo que cambió |
| **Remote / almacenamiento DVC** | Donde viven las versiones de los datos (aquí una carpeta local; en empresas S3/GCS…) |
| **Experiment tracking** | Registrar parámetros, métricas y artefactos de cada entrenamiento (MLflow) |
| **Run (ejecución)** | Un intento de entrenamiento registrado en MLflow |
| **Artefacto** | Un archivo guardado con una ejecución (gráfico, modelo, reporte) |
| **Firma del modelo (signature)** | El "contrato" del modelo: qué entradas acepta y qué devuelve |
| **Model Registry** | Catálogo de versiones de modelos aprobados |
| **Alias (@champion)** | Una etiqueta movible que apunta a la versión en producción |
| **Control de calidad (quality gate)** | Reglas escritas que un modelo debe cumplir antes de ser promovido |
| **API** | Una puerta por la que los programas se comunican por HTTP |
| **Endpoint** | Una puerta específica de la API (p. ej. `/predict`) |
| **Imagen / contenedor Docker** | La caja empacada / la caja funcionando |
| **Registry (ghcr.io)** | Donde se guardan y comparten las imágenes Docker |
| **CI** | Revisiones automáticas en cada cambio |
| **CD** | Entrega automática de los cambios que pasaron el CI |
| **Data drift** | Los datos de hoy ya no se parecen a los de entrenamiento |
| **Prueba KS** | Prueba estadística que mide qué tan distintas son dos distribuciones (0–1) |
| **Training/serving skew** | Calcular las pistas distinto al entrenar y en producción (un error silencioso) |

## ❓ Preguntas frecuentes

**¿Me puedo hacer rico con este modelo?**
No. Acierta ~51,5 % y perdió contra comprar y mantener en el año de prueba. Es una herramienta para aprender. No es asesoría financiera.

**`MT5 initialize() failed`**
Abre la terminal de MetaTrader 5 e inicia sesión (sirve una cuenta demo). El paquete de Python habla con la terminal abierta.

**Mi broker no tiene `XAUUSD`**
Agrega su nombre en `params.yaml → data.symbol_candidates` (el script de extracción te muestra qué nombres encontró).

**Uso Mac/Linux**
Todo funciona menos la extracción. Usa el CSV de muestra (ver [01 · Instalación](01-setup.md#-no-tienes-metatrader-5-maclinux-o-sin-cuenta)).

**`dvc repro` dice "didn't change, skipping"**
¡Esa es la idea! Fuerza una etapa con `dvc repro -f <etapa>` (p. ej. `-f extract` para bajar datos nuevos).

**`dvc pull` falla en otro PC**
El almacenamiento es una carpeta local de *tu* PC. Para equipos usa un remote compartido o en la nube: `dvc remote modify localstorage url s3://bucket/ruta`.

**El puerto 8000 ya está en uso**
`$env:API_PORT=8010; docker compose up` (o `uvicorn src.api.main:app --port 8010`).

**¿Por qué el CI entrena solo con 4.000 velas?**
El robot de GitHub no tiene MT5 ni acceso a tu almacenamiento DVC local. El CI verifica que el *código* funcione; el modelo *real* se entrena en tu PC y lo verifica el control de calidad.

**¿Dónde veo los resultados del CI?**
https://github.com/MirandaCR/GoldMLFlow/actions → clic en una ejecución → **Summary**.

**¿Cómo vuelvo a un modelo anterior?**
En la interfaz de MLflow (Models → gold-direction-h1) mueve el alias `@champion` a la versión anterior y luego vuelve a exportarlo con `python scripts/export_champion.py` y haz commit de `models/champion`.

---
[🏠 Volver al README](../../README.es.md)

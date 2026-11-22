# Fotos catalogadas — categorias

Total de frames catalogados: **1467**. Cada imagem foi copiada para uma ou mais pastas abaixo, conforme rótulos de anotação humana (Level-A frame observation).

- `normal/` — 1230 imagens (`normal_0001.jpg`, `normal_0002.jpg`, ...)
- `sonolencia/` — 221 imagens (`sonolencia_0001.jpg`, `sonolencia_0002.jpg`, ...)
- `fadiga/` — 34 imagens (`fadiga_0001.jpg`, `fadiga_0002.jpg`, ...)
- `bocejo/` — 117 imagens (`bocejo_0001.jpg`, `bocejo_0002.jpg`, ...)
- `olhos_fechados/` — 82 imagens (`olhos_fechados_0001.jpg`, `olhos_fechados_0002.jpg`, ...)
- `usando_celular/` — 16 imagens (`usando_celular_0001.jpg`, `usando_celular_0002.jpg`, ...)

## Nomenclatura

Cada arquivo foi renomeado para `categoria_NNNN.ext` em ordem de `frame_id`. O nome original e o `frame_id` estão preservados em `manifest.csv` (colunas `original_filename`, `frame_id` e `renamed_files`).

## Regras de inclusão

- `normal`: sem sonolência, fadiga, bocejo, olho fechado ou celular detectado.
- `sonolencia`: rótulo PRESENT/UNCERTAIN de sonolência sem código específico de bocejo/olho fechado.
- `fadiga`: olho fechado observado em frame isolado (UNCERTAIN por falta de persistência temporal — ver `documentation/fatigue_criteria.md`).
- `bocejo`: somente `SLEEP_003` confirmado por revisão visual.
- `olhos_fechados`: `SLEEP_001` / `SLEEP_006` ou atividade DROWSY.
- `usando_celular`: `phone_detection=YES` após verificação visual em tamanho real; a presença de celular sozinha nunca gera `DISTRACTION=PRESENT` (§2.3).

Auditoria cruzada: **0** problema(s) encontrado(s).

# Fotos catalogadas — categorias

Total de frames catalogados: **1467**. Cada imagem foi copiada para uma ou mais pastas abaixo, conforme rótulos de anotação humana (Level-A frame observation).

- `normal/` — 1230 imagens
- `sonolencia/` — 221 imagens
- `fadiga/` — 34 imagens
- `bocejo/` — 117 imagens
- `olhos_fechados/` — 82 imagens
- `usando_celular/` — 16 imagens

## Regras de inclusão

- `normal`: sem sonolência, fadiga, bocejo, olho fechado ou celular detectado.
- `sonolencia`: rótulo PRESENT/UNCERTAIN de sonolência sem código específico de bocejo/olho fechado.
- `fadiga`: olho fechado observado em frame isolado (UNCERTAIN por falta de persistência temporal — ver `documentation/fatigue_criteria.md`).
- `bocejo`: `SLEEP_003` ou atividade visual YAWNING.
- `olhos_fechados`: `SLEEP_001` / `SLEEP_006` ou atividade DROWSY.
- `usando_celular`: `phone_detection=YES` após verificação visual em tamanho real; a presença de celular sozinha nunca gera `DISTRACTION=PRESENT` (§2.3).

Auditoria cruzada: **0** problema(s) encontrado(s).

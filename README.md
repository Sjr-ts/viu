# NightEyes — Dataset de imagens catalogadas

Base supervisionada para avaliação offline do **Risk Engine V1.0**. As imagens foram catalogadas e anotadas visualmente, com rótulos independentes para **sonolência**, **fadiga**, **distração**, **detecção de rosto** e **detecção de celular**.

**Estado atual:** validação `PASS` · **74 testes aprovados** · **1.467 frames catalogados** · **1.700 imagens organizadas** · splits `TRAIN/VALIDATION/TEST` por participante.

> Os rótulos de referência **nunca** foram produzidos com EAR, MAR, PERCLOS, scores do motor ou nomes de arquivo. `UNCERTAIN` e `UNOBSERVABLE` nunca são convertidos em `ABSENT`. A presença de celular sozinha nunca gera `DISTRACTION=PRESENT`.

---

## 1. Pasta principal: `fotos catalogadas/`

É a fonte canônica e única das imagens do dataset.

```
fotos catalogadas/
├── normal/                1230 imagens  (normal_0001.jpg ... normal_1230.jpg)
├── sonolencia/             221 imagens  (sonolencia_0001.jpg ... sonolencia_0221.jpg)
├── bocejo/                 117 imagens  (bocejo_0001.jpg ... bocejo_0117.jpg)
├── olhos_fechados/          82 imagens  (olhos_fechados_0001.jpg ... olhos_fechados_0082.jpg)
├── fadiga/                  34 imagens  (fadiga_0001.jpg ... fadiga_0034.jpg)
├── usando_celular/          16 imagens  (usando_celular_0001.jpg ... usando_celular_0016.jpg)
├── manifest.csv            1.467 linhas — rastreabilidade e rótulos por frame
└── README.md               regras de inclusão e nomenclatura
```

Uma imagem pode aparecer em mais de uma categoria (multilabel). Exemplo: um bocejo com olhos fechados aparece em `bocejo/` e `olhos_fechados/`.

### Regras de inclusão

| Pasta | Critério visual |
|---|---|
| `normal` | Sem sonolência, fadiga, bocejo, olho fechado ou celular detectado. |
| `sonolencia` | `SLEEPINESS` com `PRESENT` ou `UNCERTAIN`. |
| `bocejo` | Somente `SLEEP_003` confirmado por revisão visual. |
| `olhos_fechados` | `SLEEP_001` / `SLEEP_006` ou atividade `DROWSY`. |
| `fadiga` | Evidência ocular em frame isolado, rotulada `UNCERTAIN` por falta de persistência temporal. |
| `usando_celular` | `phone_detection=YES` após verificação visual em tamanho real. |

### Nomenclatura

Cada arquivo segue o padrão `categoria_NNNN.jpg`. O nome original do frame, o `frame_id`, o `dataset_id`, todas as categorias e os rótulos estão em `fotos catalogadas/manifest.csv`.

Colunas principais do manifesto: `frame_id`, `dataset_id`, `original_filename`, `image`, `renamed_files`, `categories`, `activity_label`, `sleepiness_label`, `sleepiness_behavior`, `fatigue_label`, `distraction_label`, `phone_detection`, `face_detection`, `audit`.

---

## 2. Uso rápido

```python
import csv
from pathlib import Path

ROOT = Path(".")

# Todas as imagens e rótulos por categoria
with (ROOT / "fotos catalogadas" / "manifest.csv").open(encoding="utf-8") as fh:
    manifest = list(csv.DictReader(fh))

print(len(manifest))                      # 1467
print(manifest[0]["image"])              # fotos catalogadas/normal/normal_0001.jpg
print(manifest[0]["categories"])         # ex.: normal|sonolencia

# Splits supervisionados (por participante)
with (ROOT / "data/processed/train.csv").open(encoding="utf-8") as fh:
    train = list(csv.DictReader(fh))

print(train[0]["image_path"])
print(train[0]["sleepiness_label"], train[0]["distraction_label"])
```

`image_path` nos splits e `frame_file` em `data/catalog/frame_samples.csv` apontam para a pasta canônica `fotos catalogadas/`. A coluna `original_frame_file` preserva o caminho derivado original para auditoria. O SHA-256 em `frame_samples.csv` valida a integridade de cada imagem.

---

## 3. Estrutura do repositório

```
NightEyes/
├── fotos catalogadas/                 # imagens canônicas por categoria
├── README.md                          # este arquivo
├── requirements.txt                   # pandas, pytest, opencv-python, numpy
├── data/
│   ├── catalog/
│   │   ├── datasets.csv               # 10 fontes inventariadas
│   │   ├── licenses.csv               # licenças verificadas
│   │   ├── compatibility_matrix.csv   # mapeamento rótulo-origem → NightEyes
│   │   ├── sources_registry.csv       # proveniência e SHA-256 dos arquivos brutos
│   │   ├── frame_samples.csv          # índice dos 1.467 frames
│   │   └── hf_facecrops_manifest.json # amostragem SRC010
│   ├── annotation/
│   │   ├── frame_annotations.csv      # 3.240 anotações Level-A por frame
│   │   ├── episodes.csv               # 3.240 episódios observados
│   │   ├── windows.csv                # 3.188 janelas de 5 s
│   │   ├── participants.csv
│   │   ├── sessions.csv
│   │   ├── annotators.csv
│   │   └── self_reports.csv           # esquema KSS (sem registros)
│   ├── processed/
│   │   ├── train.csv
│   │   ├── validation.csv
│   │   ├── test.csv
│   │   └── split_manifest.json
│   ├── reports/
│   │   ├── annotation_status.md
│   │   ├── phone_verification.csv     # 16 celulares confirmados visualmente
│   │   ├── engine_evaluation.json
│   │   ├── engine_evaluation.csv
│   │   └── validation_report.json/.csv
│   └── raw/                           # originais ignorados pelo Git (.gitkeep)
├── documentation/
│   ├── fatigue_criteria.md
│   ├── sleepiness_criteria.md
│   ├── distraction_criteria.md
│   ├── behavior_dictionary.csv
│   ├── label_mapping_rules.md
│   ├── metadata_dictionary.csv
│   ├── annotation_workflow.md
│   └── IMPLEMENTATION_REPORT.md
├── scripts/                           # aquisição, catalogação, consolidação, validação
└── tests/                             # 74 testes
```

Artefatos intermediários (folhas de revisão, frames extraídos, rascunhos automáticos) ficam em `data/_incoming/` e são ignorados pelo Git.

---

## 4. Fontes de dados

| ID | Fonte | Licença | Uso no dataset |
|---|---|---|---|
| `SRC003` | YawDD | CC BY | Vídeos de motoristas; frames de Normal/Talking/Yawning e amostragem densa |
| `SRC009` | Drowsiness Detection using Edge Computing (Zenodo) | CC BY 4.0 | Imagens de olhos/bocejo/celular; rótulos YOLO da fonte não usados como referência |
| `SRC010` | CNN-Based Drowsiness Detection (HuggingFace, MIT) | MIT | Face-crops para estado ocular; rótulos EAR/MAR da fonte descartados por §7 |

As demais sete fontes do catálogo permanecem bloqueadas por licença/EULA e não foram baixadas. O dataset Zenodo "Multi-Class Driver Behavior" foi rejeitado porque seu acordo de uso proíbe redistribuição.

---

## 5. Anotação Level-A

- **Unidade:** observação visual de frame catalogado (`start_ms = timestamp`, `end_ms = timestamp + 1`). A extensão temporal não é inferida.
- **Domínios:** `FATIGUE`, `SLEEPINESS`, `DISTRACTION`.
- **Rótulos:** `PRESENT`, `ABSENT`, `UNCERTAIN`, `UNOBSERVABLE`.
- **Campos por linha:** `participant_id`, `session_id`, `timestamp_ms`, `domain`, `reference_label`, `behavior_code`, `annotator_id`, `annotation_confidence`, `lighting_condition`, `occlusion_condition`, `annotation_notes`, `face_visible`, `activity_label`, `phone_detection`, `face_detection`.
- **Detecção de celular:** 50 candidatos SRC009 foram revisados em tamanho real; 16 imagens confirmadas permanecem em `usando_celular/`. A evidência está em `data/reports/phone_verification.csv`.
- **Independência:** scores/classificações do Risk Engine são proibidos como origem de rótulo; `scripts/label_mapping.py` retorna `FORBIDDEN` para tentativas desse tipo.

---

## 6. Splits

Divisão determinística por `participant_id` (seed `20261121`), sem participante repetido entre conjuntos:

| Split | Frames | Participantes |
|---|---:|---:|
| `TRAIN` | 1004 | 338 |
| `VALIDATION` | 220 | 79 |
| `TEST` | 243 | 67 |

`TEST` está marcado como `test_locked=true` em `data/processed/split_manifest.json` e não deve ser usado para calibração.

---

## 7. Validação e avaliação

```bash
python scripts/validate_dataset.py
python -m pytest -q
python scripts/evaluate_engine.py --root .
python scripts/evaluate_engine.py --root . --scores data/reports/engine_scores.csv
```

- `validate_dataset.py` executa as verificações V01–V22 e grava `data/reports/validation_report.json/.csv`.
- Resultado atual: `PASS`, 0 erros. No projeto de trabalho há 1 aviso (`V20`: 29 participantes com consentimento `RESTRICTED` aparecem em episódios). No clone Git, avisos `V09` adicionais são esperados porque `data/raw/` é ignorado pelo Git.
- `engine_evaluation.json` está `NOT_EVALUATED` até um arquivo de scores/predições do motor ser fornecido.
- `scripts/build_categorized_catalog.py` reconstrói `fotos catalogadas/`, o `manifest.csv` e o `README.md` da pasta a partir de `frame_samples.csv` + `frame_annotations.csv`.

---

## 8. Limitações declaradas

- Apenas `ANN_1` produziu anotações visuais; avaliação cega com `ANN_2` está pendente.
- Fadiga usa unidades `UNCERTAIN` de frame isolado; não há evidência de persistência temporal.
- `self_reports.csv` existe como esquema, mas não há dados KSS.
- Episódios são pontuais; janelas de 5 s cobrem apenas material anotado.
- Iluminação SRC003 marcada como `UNVERIFIED_DAYLIGHT` quando herdada do lote.
- SRC009/SRC010 são imagens públicas sob CC BY 4.0/MIT, sem consentimento individual documentado.
- Scores do motor não foram fornecidos; métricas de sensibilidade/especificidade ainda não foram calculadas.

---

## 9. Segurança

Dados brutos, staging e artefatos intermediários são ignorados pelo Git. Nenhum token, credencial ou PAT deve ser versionado neste repositório.

# NightEyes — Runbook de Anotação (Protocolo V0.1 §6 → comandos)

Este documento operacionaliza o processo de anotação do protocolo
*NightEyes — Anotação de Dataset V0.1* com as ferramentas deste repositório.
Uso na **sessão piloto** e depois em escala.

---

## 0. Pré-condições de legalidade (§12 — critério 7)

```bash
python scripts/acquire.py list
```

- Só avance com fontes em gate **CLEARED** (ou com EULA/permissão já
  arquivado em `data/catalog/licenses.csv`).
- Dados brutos entram apenas via `acquire.py fetch` → `finalize`
  (SHA-256 + `sources_registry.csv`).

---

## 1. Registrar a sessão (§6 passo 1 + §9)

Após `finalize`, popular os esquemas a partir dos metadados de origem
(**sem** identificação facial, **sem** fusão entre datasets):

1. `data/annotation/participants.csv` — 1 linha por participante:
   `participant_id` (ex.: `PT_SRC003_001`), `dataset_id`,
   `original_participant_id`, `anonymized_id`, `consent_status`,
   `demographic_metadata_availability`.
2. `data/annotation/sessions.csv` — 1 linha por vídeo/sessão:
   `duration_ms`, `original_fps`, `resolution`, `lighting_condition`,
   `camera_position`, `glasses_condition`, `occlusion_condition`,
   `activity_type` (§9).

> Nunca copiar nome/rosto/identidade. IDs são opacos e por dataset.

## 2. Registrar os avaliadores (§6 passo 4)

`data/annotation/annotators.csv`:

| coluna | valor esperado |
|---|---|
| `annotator_id` | ex.: `ANN_1`, `ANN_2`, `AN_CONSOLIDATED` |
| `training_status` | `TRAINED` após leitura do manual |
| `independent_annotation_enabled` | `YES` |
| `access_to_engine_scores` | **`NO`** (obrigatório — §7) |
| `notes` | data de treino, observações |

> O validador **V02** recusa anotações cujo `annotator_id` não exista aqui.

## 3. Disponibilizar material SEM scores (§6 passo 4)

- Entregar aos avaliadores apenas: vídeos de `data/raw/` + este runbook +
  `documentation/behavior_dictionary.csv`.
- **Proibido** entregar: scores do Risk Engine, EAR/MAR/PERCLOS, saídas do
  motor (§7). O módulo `label_mapping.py` devolve `FORBIDDEN` para esses
  sinais — é a regra de projeto, não uma preferência.

## 4. Anotação independente (§6 passo 5)

Cada avaliador produz o próprio `episodes.csv` (Nível A):

- `start_ms`/`end_ms` em milissegundos **relativos à sessão**.
- `domain` independente por domínio: `FATIGUE` | `SLEEPINESS` | `DISTRACTION`.
- `reference_label`: `PRESENT` | `ABSENT` | `UNCERTAIN` | `UNOBSERVABLE`.
  - `UNCERTAIN` = evidência insuficiente/ambígua.
  - `UNOBSERVABLE` = não dá para avaliar (captura).
  - **Nunca** converter `UNCERTAIN`/`UNOBSERVABLE` em `ABSENT`.
- `behavior_code` conforme `behavior_dictionary.csv` (domínio compatível —
  **V12** confere).
- `annotation_confidence`: `LOW` | `MEDIUM` | `HIGH`.
- Bocejo sem intervalo confiável → `UNCERTAIN` ou marcar sem rotular
  episódio (CASO 3). Celular presente sem desvio de atenção → **não** é
  `DIST_00x = PRESENT` (CASO 4/5).

> **Domínio DISTRACTION / celular:** seguir obrigatoriamente
> `documentation/distraction_criteria.md` (limiares PROPOSED, árvore de
> decisão presença-vs-uso, regra da associação temporal, casos-limite).

Arquivos sugeridos: `data/original_labels/episodes_<ANN_X>.csv`
(preservados como origem).

## 5. Comparação e resolução (§6 passos 6–7)

```bash
python scripts/merge_annotations.py \
    --annotator-a ANN_1 --annotator-b ANN_2 \
    --consolidator AN_CONSOLIDATED \
    --episodes data/original_labels/episodes_ALL.csv \
    --out data/annotation/episodes_consolidated.csv \
    --report data/quality_control/divergence_report.csv
```

| Situação | Resultado |
|---|---|
| Mesmo comportamento, mesmo rótulo (IoU ≥ 0,5) | consenso — mantém o rótulo |
| Rótulos diferentes | **`UNCERTAIN`** (divergência) |
| Visto por um só | **`UNCERTAIN`** (observação única) |

> Divergências podem ser resolvidas manualmente **antes** do merge; qualquer
> resolução humana deve ser documentada em `annotation_notes`. Casos não
> resolvidos permanecem `UNCERTAIN` — **jamais** viram `ABSENT`.

## 6. Nível B — janelas (§3)

```bash
python scripts/make_windows.py --window-ms 5000 --annotator AN_CONSOLIDATED
```

- Grade 0 → `duration_ms` por sessão e domínio (janela final parcial ok).
- Prioridade: `PRESENT` > `UNCERTAIN` > `UNOBSERVABLE` > `ABSENT`.
- Episódios originais **não** são modificados (intervalos preservados).
- A duração definitiva será reavaliada contra a frequência de atualização
  do Risk Engine; a grade de 5 s é a configuração inicial do protocolo.

## 7. Validação antes de consolidar (§12)

```bash
python -m pytest tests/ -q        # suite completa
python scripts/validate_dataset.py
```

Checklist §12 ↔ ferramentas:

| Critério §12 | Como checar |
|---|---|
| Timestamps alinhados | V03, V04, V05 (validador) |
| Rótulos com critério documentado | `behavior_dictionary.csv` + `label_mapping_rules.md` |
| Avaliadores sem scores | coluna `access_to_engine_scores = NO` + revisão manual do runbook |
| Casos inconclusivos identificados | relatório de divergência + rótulos `UNCERTAIN` |
| Divisão por participante | `train/validation/test` gerados **por participante** (§8) |
| Origem e condições documentadas | `sources_registry.csv` + `sessions.csv` (§9) |
| Licença/consentimento | gate do `acquire.py list` |

## 8. Divisão por participante (§8)

- Gerar `data/processed/train.csv`, `validation.csv`, `test.csv` atribuindo
  **participantes inteiros** a cada conjunto (nunca cortar por sessão).
- Partições fixadas por semente e registradas em `annotation_notes`/relatório.
- Dados de `TEST` ficam isolados durante calibração do motor.

## 9. Consolidação final

1. Trocar `data/annotation/episodes.csv` pelo consolidado **após** revisão
   humana (manter `episodes_consolidated.csv` como evidência do processo).
2. Rodar `make_windows.py` para regenerar `windows.csv`.
3. `validate_dataset.py` → esperado **PASS**.
4. Tags de versão: incrementar `schema_version` no
   `metadata_dictionary.csv` se os CSVs mudarem de forma.

---

**Regras de ouro (§7):** nenhum score do motor entra na referência ·
`UNCERTAIN`/`UNOBSERVABLE` nunca viram `ABSENT` · originais intactos ·
divergência não resolvida = `UNCERTAIN`.

# NightEyes — status da anotação e do ground truth

Gerado em 2026-11-22T04:49:42+00:00.

## O que é ground truth observado

- 3240 unidades Level-A derivadas de anotação visual humana de frames catalogados (não de nomes de arquivo nem de scores do motor).
- 3188 janelas Level-B de 5 s apenas onde há episódio anotado; nenhum rótulo ABSENT fabricado para material não revisado.
- Rótulos UNCERTAIN/UNOBSERVABLE preservados (nunca convertidos em ABSENT).

## Arquivos preservados (rascunhos)

- `data/_incoming/original_labels/episodes_draft_auto.csv` — rascunho local por filename; não usar para avaliação e não versionado.
- `data/_incoming/original_labels/windows_draft_auto.csv` — rascunho local por filename; não usar para avaliação e não versionado.

## Divisão por participante (protocolo §8)

- Semente: `20261121`; participantes: 484.
- TRAIN: 1004 frames / 338 participantes (`data/processed/train.csv`)
- VALIDATION: 220 frames / 79 participantes (`data/processed/validation.csv`)
- TEST: 243 frames / 67 participantes (`data/processed/test.csv`)
- TEST está bloqueado para calibração (`test_locked=true`).

## Limitações conhecidas (declaradas, não ocultadas)

- **Avaliação cega dupla pendente**: apenas ANN_1 produziu anotações visuais; ANN_2 não tem linhas. Um segundo avaliador independente é necessário antes de uso como referência final.
- **Fadiga**: episódios UNCERTAIN de frame isolado (sem persistência observável); critérios em `documentation/fatigue_criteria.md`. Nenhum episódio FATIGUE=PRESENT fabricado.
- **KSS/autorrelato**: esquema `data/annotation/self_reports.csv` criado, sem registros (fonte atual não fornece KSS).
- **Episódios pontuais**: cada unidade Level-A cobre apenas o frame observado (`end_ms = start_ms + 1`); extensão temporal não foi inferida.
- **Iluminação SRC003**: `UNVERIFIED_DAYLIGHT` indica valor herdado do lote, não verificado quadro a quadro.
- **Consentimento SRC009/SRC010**: imagens públicas sob CC BY 4.0 / MIT (`DOCUMENTED_PUBLIC_LICENSE`), sem consentimento individual documentado. SRC010 descarta rótulos EAR/MAR da fonte (protocolo §7).

## Distribuição de rótulos nos episódios

- ABSENT: 1793
- PRESENT: 197
- UNCERTAIN: 770
- UNOBSERVABLE: 480

## Domínios

- DISTRACTION: 1467 episódios
- FATIGUE: 306 episódios
- SLEEPINESS: 1467 episódios

## Detecção de rosto e celular (por frame catalogado)

- face_visible=UNKNOWN: 1161
- face_visible=YES: 306
- phone_visible=NO: 1176
- phone_visible=UNKNOWN: 275
- phone_visible=YES: 16
- `phone_visible=YES` sozinho nunca gera `DISTRACTION=PRESENT` (protocolo §2.3).
- 50 candidatos SRC009 (rótulo-fonte 'Object') foram revisados visualmente; 13 confirmados como celular nesse lote, o restante são garrafas/copos (falso positivo da fonte). Total final no dataset: 16 imagens confirmadas como celular.
- Amostragem densa (0.2..0.8) adicionada aos vídeos 5-FemaleGlasses para capturar bocejos reais que a amostragem 0.1/0.5/0.9 não alcançava.

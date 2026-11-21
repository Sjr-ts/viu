# NightEyes — status da anotação e do ground truth

Gerado em 2026-11-21T20:00:37+00:00.

## O que é ground truth observado

- 2322 unidades Level-A derivadas de anotação visual humana de frames catalogados (não de nomes de arquivo nem de scores do motor).
- 2312 janelas Level-B de 5 s apenas onde há episódio anotado; nenhum rótulo ABSENT fabricado para material não revisado.
- Rótulos UNCERTAIN/UNOBSERVABLE preservados (nunca convertidos em ABSENT).

## Arquivos preservados (rascunhos)

- (rascunhos já arquivados em execução anterior)

## Divisão por participante (protocolo §8)

- Semente: `20261121`; participantes: 204.
- TRAIN: 786 frames / 145 participantes (`data/processed/train.csv`)
- VALIDATION: 164 frames / 23 participantes (`data/processed/validation.csv`)
- TEST: 211 frames / 36 participantes (`data/processed/test.csv`)
- TEST está bloqueado para calibração (`test_locked=true`).

## Limitações conhecidas (declaradas, não ocultadas)

- **Avaliação cega dupla pendente**: apenas ANN_1 produziu anotações visuais; ANN_2 não tem linhas. Um segundo avaliador independente é necessário antes de uso como referência final.
- **Fadiga**: sem episódios anotados; domínio documentado mas não rotulado. Nenhuma janela FATIGUE foi fabricada.
- **KSS/autorrelato**: esquema `data/annotation/self_reports.csv` criado, sem registros (fonte atual não fornece KSS).
- **Episódios pontuais**: cada unidade Level-A cobre apenas o frame observado (`end_ms = start_ms + 1`); extensão temporal não foi inferida.
- **Iluminação SRC003**: `UNVERIFIED_DAYLIGHT` indica valor herdado do lote, não verificado quadro a quadro.
- **Consentimento SRC009**: imagens públicas sob CC BY 4.0 (`DOCUMENTED_PUBLIC_LICENSE`), sem consentimento individual documentado.

## Distribuição de rótulos nos episódios

- ABSENT: 1504
- PRESENT: 114
- UNCERTAIN: 462
- UNOBSERVABLE: 242

## Domínios

- DISTRACTION: 1161 episódios
- SLEEPINESS: 1161 episódios

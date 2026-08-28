# Data Schema — Pharmacovigilance NLP Project


---

## PHEE Dataset

### Top-level Parquet Schema

| Column | dtype | Notes |
|---|---|---|
| `id` | object | PubMed article ID + sentence index (e.g. `8908396_3`) |
| `context` | object | Raw pharmacovigilance/medical narrative sentence |
| `is_mult_event` | bool | True when the sentence contains more than one annotated event |
| `annotations` | object | List of annotation blocks; each block contains an `events` array |

### Annotation Structure

```
annotations  →  list of annotation blocks
  block.events  →  array of event rows
    event_row.event_id        str   e.g. 'E1'
    event_row.event_type      str   'Adverse_event' | 'Potential_therapeutic_event' | 'Combination'
    event_row.event_data      str   JSON-encoded event argument dict (must be parsed)

  event_data keys (top-level):
    event_id        str
    event_type      str
    Trigger         {text, start, entity_id}
    Effect          {text, start, entity_id}            ← adverse effect text
    Treatment       {text, start, entity_id, Drug?, Disorder?, Route?, Dosage?, Freq?, Duration?, Combination?}
    Subject         {text, start, entity_id, Age?, Gender?, Population?}
    Severity        {text, start, entity_id, value}     ← 'High' | 'Low' | ...
    Speculated      {text, start, entity_id, value}     ← bool
    Drug            nested inside Treatment
    Disorder        nested inside Treatment or Subject
    Route           nested inside Treatment
    Dosage          nested inside Treatment
    Freq            nested inside Treatment
    Duration        nested inside Treatment
    Combination     list of sub-events (event_type='Combination')
```

### Parsing Requirements

1. `event_data` is a **JSON-encoded string** inside each event row. It must be parsed with `json.loads`.
2. `Drug` appears **nested inside `Treatment`**, not at the event top level.
3. Multi-drug events use `Combination` sub-events; each names the participant drugs.
4. `Subject` contains `Age` and `Gender` as nested dicts, not flat strings.
5. Character offsets (`start`) are lists of lists, supporting discontinuous spans.
6. `Speculated.value` is a Python bool; `Severity.value` is a string.

### Split: train

- Rows: **2898**
- Multi-event rows: {'False': 2439, 'True': 459}
- Max events per row: 4
- Speculated events: 367
- Null annotation rows: 0

**Event type distribution:**
- `Adverse_event`: 2710
- `Potential_therapeutic_event`: 296

**Severity value distribution:**
- `High`: 182
- `Low`: 18
- `Medium`: 58

**Most frequent argument keys (top-level and nested):**
- `Trigger.text`: 3006
- `event_id`: 3006
- `Trigger.entity_id`: 3006
- `event_type`: 3006
- `Trigger.start`: 3006
- `Trigger`: 3006
- `Treatment.start`: 3005
- `Treatment`: 3005
- `Treatment.text`: 3005
- `Treatment.entity_id`: 3005
- `Treatment.Drug.start`: 2973
- `Treatment.Drug.text`: 2973
- `Treatment.Drug.entity_id`: 2973
- `Treatment.Drug`: 2973
- `Effect.entity_id`: 2781
- `Effect.start`: 2781
- `Effect`: 2781
- `Effect.text`: 2781
- `Subject`: 1444
- `Subject.text`: 1444
- `Subject.start`: 1444
- `Subject.entity_id`: 1444
- `Treatment.Disorder.entity_id`: 968
- `Treatment.Disorder`: 968
- `Treatment.Disorder.start`: 968

### Split: dev

- Rows: **961**
- Multi-event rows: {'False': 771, 'True': 190}
- Max events per row: 3
- Speculated events: 143
- Null annotation rows: 0

**Event type distribution:**
- `Adverse_event`: 886
- `Potential_therapeutic_event`: 117

**Severity value distribution:**
- `High`: 50
- `Medium`: 11
- `Low`: 3

**Most frequent argument keys (top-level and nested):**
- `Trigger.text`: 1003
- `event_id`: 1003
- `Treatment`: 1003
- `Trigger.entity_id`: 1003
- `Trigger.start`: 1003
- `Treatment.text`: 1003
- `Trigger`: 1003
- `Treatment.start`: 1003
- `event_type`: 1003
- `Treatment.entity_id`: 1003
- `Treatment.Drug.start`: 991
- `Treatment.Drug.entity_id`: 991
- `Treatment.Drug.text`: 991
- `Treatment.Drug`: 991
- `Effect`: 909
- `Effect.entity_id`: 909
- `Effect.start`: 909
- `Effect.text`: 909
- `Subject`: 516
- `Subject.text`: 516
- `Subject.start`: 516
- `Subject.entity_id`: 516
- `Treatment.Disorder.entity_id`: 323
- `Treatment.Disorder`: 323
- `Treatment.Disorder.start`: 323

### Split: test

- Rows: **968**
- Multi-event rows: {'False': 804, 'True': 164}
- Max events per row: 3
- Speculated events: 123
- Null annotation rows: 0

**Event type distribution:**
- `Adverse_event`: 889
- `Potential_therapeutic_event`: 121

**Severity value distribution:**
- `High`: 66
- `Medium`: 20
- `Low`: 4

**Most frequent argument keys (top-level and nested):**
- `Trigger.text`: 1010
- `Treatment.start`: 1010
- `event_id`: 1010
- `Treatment`: 1010
- `Trigger.entity_id`: 1010
- `event_type`: 1010
- `Trigger.start`: 1010
- `Treatment.text`: 1010
- `Trigger`: 1010
- `Treatment.entity_id`: 1010
- `Treatment.Drug.start`: 997
- `Treatment.Drug.text`: 997
- `Treatment.Drug.entity_id`: 997
- `Treatment.Drug`: 997
- `Effect.entity_id`: 903
- `Effect.start`: 903
- `Effect`: 903
- `Effect.text`: 903
- `Subject.text`: 464
- `Subject.entity_id`: 464
- `Subject`: 464
- `Subject.start`: 464
- `Treatment.Disorder.entity_id`: 333
- `Treatment.Disorder`: 333
- `Treatment.Disorder.start`: 333

---

## TAC 2017 ADR Dataset

### XML Schema

```xml
<Label drug='DRUGNAME' track='TAC2017_ADR'>
  <Text>
    <Section name='adverse reactions' id='S1'>...</Section>
    <Section name='warnings and precautions' id='S2'>...</Section>
    <!-- further sections -->'
  </Text>
  <Mentions>
    <Mention id='M1' section='S1' type='AdverseReaction' start='84' len='8' str='headache'/>
    <!-- type: AdverseReaction | Factor | DrugClass | Severity | Animal -->'
    <!-- start/len may be comma-separated for discontinuous spans -->'
  </Mentions>
  <Relations>
    <Relation id='RL1' type='Hypothetical' arg1='M37' arg2='M36'/>
    <!-- type: Hypothetical | Effect | Negated -->'
  </Relations>
  <Reactions>
    <Reaction id='AR1' str='headache'/>
    <!-- normalised, deduplicated reaction set for this drug label -->'
  </Reactions>
</Label>
```

### Parsing Requirements

1. `start` and `len` attributes may contain **comma-separated values** for discontinuous spans (e.g. `start='6173,6210'`). These must be split and resolved independently.
2. `Mention.type` is not always `AdverseReaction`; `Factor`, `DrugClass`, `Severity`, and `Animal` also appear.
3. `Factor` mentions (e.g. `risk`, `may`, `can`) are arguments in `Hypothetical` relations — they signal that the associated `AdverseReaction` is not a confirmed event.
4. The `Reactions` block contains **deduplicated, normalised** reaction terms — one entry per unique concept for that label. This is the normalization target.
5. `Mention` and `Reaction` IDs use different namespaces (`M*` vs `AR*`) and cannot be joined directly; the mapping is implicit via string matching or section context.
6. The unannotated files contain empty `<Mentions/>`, `<Relations/>`, and `<Reactions/>` elements.

### Category: train

- Files: **101**
- Total mentions: 15722
- Total relations: 3228
- Total reactions: 7038
- Files with discontinuous mention spans: 86

**Mention type totals:**
- `AdverseReaction`: 13795
- `Severity`: 934
- `Factor`: 602
- `DrugClass`: 249
- `Negation`: 98
- `Animal`: 44

**Relation type totals:**
- `Hypothetical`: 1611
- `Effect`: 1454
- `Negated`: 163

**Section name frequency:**
- `adverse reactions`: 101 files
- `warnings and precautions`: 100 files
- `boxed warnings`: 38 files

### Category: gold

- Files: **99**
- Total mentions: 14625
- Total relations: 2955
- Total reactions: 6343
- Files with discontinuous mention spans: 87

**Mention type totals:**
- `AdverseReaction`: 12693
- `Severity`: 947
- `Factor`: 562
- `Negation`: 173
- `DrugClass`: 164
- `Animal`: 86

**Relation type totals:**
- `Hypothetical`: 1486
- `Effect`: 1181
- `Negated`: 288

**Section name frequency:**
- `adverse reactions`: 99 files
- `warnings and precautions`: 97 files
- `boxed warnings`: 41 files

### Category: unannotated
- Files: **2208**
- Not parsed in detail; used only for exploratory analysis.

---

## Field-to-Task Mapping

| Task | PHEE fields | TAC fields |
|---|---|---|
| Adverse event extraction | `Effect.text` | `Mention[type=AdverseReaction].str` |
| Drug extraction | `Treatment.Drug.text` | `Mention[type=DrugClass].str` |
| Event-structure analysis | `event_type`, `Trigger`, all arguments | `Relation.type` |
| Context / speculation | `Speculated.value` | `Relation[type=Hypothetical]`, `Factor` mentions |
| Severity | `Severity.value` | `Mention[type=Severity].str` |
| Drug–disorder link | `Treatment.Disorder.text` | — |
| Subject characterisation | `Subject.Age`, `Subject.Gender` | — |
| Dosage/route/frequency | `Treatment.Dosage`, `.Route`, `.Freq` | — |
| Terminology normalisation | Not primary task | `Reaction.str` (normalised target) |

---

## Data Leakage Risks

1. **PHEE splits**: `train`, `dev`, and `test` must not be mixed. IDs appear to be unique across splits (PubMed article + sentence index). Verify no PMID overlap before evaluation.
2. **TAC gold isolation**: `gold_xml` must be treated as a held-out test set. Algorithm development and threshold tuning must use `train_xml` only.
3. **TAC reaction-to-mention mapping**: The `Reactions` block uses normalised strings. If the normalised string is identical to a `Mention.str`, they may look like a label leak. In practice they are intended to be the normalisation target, not a training signal for mention detection.
4. **Terminology contamination**: If a terminology subset is built from TAC `train_xml` reaction strings, any evaluation against `train_xml` mentions will be inflated. Evaluate terminology coverage separately on `gold_xml`.
5. **Discontinuous span handling**: Silently merging comma-separated `start` values as a single integer will produce incorrect character offsets and corrupt span evaluation.

---

## Missing Information Relative to Action Plan

1. **No MedDRA concept IDs** in either dataset. TAC `Reaction.str` values are normalised ADR strings, not MedDRA PT codes. The prototype terminology must be built separately and linked by string matching or embedding.
2. **No explicit causality labels** in PHEE. Causality is sometimes implicit in trigger words (e.g. `caused`, `induced`, `following`) but is not a dedicated annotation field.
3. **No temporality labels** (current vs. historical) in PHEE. The `Speculated` field covers uncertainty, not temporal context. ConText or rule-based detection is required.
4. **No experiencer labels** in PHEE. Events are assumed to be patient-level unless the `Subject` text indicates otherwise. Explicit other-experiencer annotation is absent.
5. **No seriousness/outcome fields** in PHEE. The `Severity` field exists but maps to High/Low/Medium labels, not ICH E2A seriousness criteria.
6. **No patient-level events in TAC**. TAC describes drug-label text (population-level risks). It cannot be used to evaluate patient-level event extraction precision directly.

---

## Recommended Train/Dev/Test Usage

### PHEE

| Split | Usage |
|---|---|
| train | Model training, rule development, feature engineering |
| dev | Hyperparameter selection, rule tuning, intermediate evaluation |
| test | Final held-out evaluation only; do not inspect until the model is frozen |

### TAC 2017

| Split | Usage |
|---|---|
| train_xml | ADR mention extraction experiments, terminology subset construction, normalization baseline development |
| gold_xml | Final held-out normalization evaluation; must not be used during algorithm development |
| unannotated_xml | Exploratory analysis only; no ground truth available |

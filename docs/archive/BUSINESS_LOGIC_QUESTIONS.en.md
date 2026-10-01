[Русский](BUSINESS_LOGIC_QUESTIONS.md) · [English](BUSINESS_LOGIC_QUESTIONS.en.md) · [Қазақша](BUSINESS_LOGIC_QUESTIONS.kk.md)

> Historical document. This is not a source of truth for the current project state.

# Business logic questions

Team **baash** · case 2, Pulse 109 · September 27, 2026

Each question arose from working with the given data, and not from general considerations. The question indicates what exactly it is blocking and what we will accept by default if there is no answer. This allows us to move without stopping development.

---

## 1. Routing and responsibility

### 1.1 Who is considered the owner of a ticket if the topic allows multiple services

In Pavlodar, the topic “Water supply to the Moscow Railway” is distributed between three services: scheduled work 25%, emergency work 19%, lack of hot water 19%. None have a majority.

**Blocks:** the rule for choosing the owner and the threshold below which the decision must go to the person. **Default:** if confidence is below 0.60, the request is transferred to the operator.

### 1.2 What is the official directory of regional services

Leave-one-region-out showed: a model trained on six regions in Kostanay gives an accuracy of 0.002 with 94.4% matching of topic names. The names are the same, there are no service directories.

**Blocks:** requirement of technical specifications for twenty regions. **Default:** We consider the directory of each region independent and do not transfer the model between regions without mapping.

### 1.3 How reassignment is recorded and its reason

There is no reassignment history in the uploads.

**Blocks:** metric misroute and training on operator corrections. **Default:** collect patches prospectively within Pulse 109.

---

## 2. Priority, timing and dangerous cases

### 2.1 Who assigns priority and according to what rule

There is no priority field in the data, there is nowhere to restore the rule.

**Blocks:** calculation of SLA and escalation. **Default:** priority is not inferred by the model, only by the rules, and no rules lower the priority automatically.

### 2.2 Which topics are considered dangerous and require immediate escalation?

**Blocks:** safety rules and acceptance criteria. **Default:** Without an approved list, automatic escalation is not enabled.

### 2.3 What deadline is in effect for each topic and who approves it?

Field `sla` is found only in the incident diagram of two regions.

**Blocks:** control of deadlines and forecast of delays.

---

## 3. Incidents and duplicates

### 3.1 Who has the right to combine requests into one incident

**Blocks:** rights in the incident layer. **Default:** merge only by human confirmation, no automatic merge.

### 3.2 What happens to a citizen’s individual term upon unification

Our model: each applicant retains his number, history and period, the incident exists on top. We need confirmation that this complies with the regulations.

### 3.3 Does the concept of “one event, many

requests"

There is no obvious grouping in the output data.

**Blocks:** training and evaluating the duplicate detector.

---

## 4. Closing and confirmation of execution

### 4.1 What status confirms actual execution and not unsubscription?

In the Kostanay region, all 20,591 records are closed, while the field `result` contains both “eliminated” and “vodokanal does not carry out work.”

**Blocks:** real resolution metrics and closure integrity.

### 4.2 What evidence is required for closure

**Default:** closure requires a non-empty result, no photographic evidence required until confirmed.

### 4.3 How repeated requests for the same issue are processed

**Blocks:** reopen and recurrence metrics.

---

## 5. Data, language and personal data

### 5.1 Where is the original text of the request before editing by the operator

All eight files have zero fields with the citizen’s text. The only free text was written by the performer after closing.

**Blocks:** additional training of the reception classifier is mandatory according to the technical specifications. Measured ceiling without text: reference 0.573, model 0.588.

### 5.2 How the Kazakh language is provided

In the corpus of 14,397 texts, there are zero purely Kazakh texts: 96.9% Russian, 3.0% mixed.

**Blocks:** bilingual assessment required by the ToR.

### 5.3 What is the legal basis for processing and storage period

**Blocks:** transferring the system from evaluation mode to pilot. **Default:** data does not leave the private repository and does not end up in public materials.

### 5.4 Which fields are available at the time of reception, and which appear after closing

**Blocks:** training without leakage. Training on the field `result` would give beautiful accuracy, which does not work on live handling.

---

## 6. Integration and operation

### 6.1 Which regional IP is the first target and is there a sandbox?

You need OpenAPI or WSDL, test access, architect contact, authentication scheme. **Default:** The replay adapter works under the same contract.

### 6.2 Who owns the service directory and how it is versioned

**Blocks:** stale directory detection.

### 6.3 What is the average time for processing a request and the operator’s target workload?

Our staffing calculation is based on two assumptions: AHT 6 minutes and 85% utilization. Both quantities are marked as placeholder.

**Blocks:** translation of load forecast into shift decision.

### 6.4 Where does the operator’s time actually go?

If analysis takes four minutes, and coordination with the service takes three days, we are optimizing the wrong bottleneck. We ask for 30 minutes with the current operator and supervisor.

---

## Reply priority

If you can’t answer everything, the order is as follows:

1. **5.1** source text of requests
2. **1.2** directories of services for other regions
3. **5.4** list of fields available during reception
4. **6.1** first regional IP with sandbox
5. **6.4** interview with operator

The first four block the requirements of the technical specifications. The fifth costs the organizers almost nothing and determines whether we automate the task.

Process input material into a structured, storable result by performing high-fidelity content cleaning, metadata judgment, and completeness self-check according to the specified rules.

## Hard Requirements

1. All valuable content must be 100% completely retained; do not omit any important information. Do not use summary compression that causes information loss.
2. Only allow deletion of repeated expressions, repeated sentences, and verbal nonsense. Do not delete any real information including facts, time, character relationships, original words, preferences, events, method steps, etc.
3. Do not fabricate or supplement any information that does not appear in the input.
4. If an image URL is inaccessible or unparseable, ignore it completely; do not guess the image content.
5. Output must be a strict JSON object; do not output Markdown or any additional explanatory text.
6. Output language must be exactly consistent with the input content, including `cleaned_content` and all field values.
7. All judgments must be made in combination with the character role `figure_role` and the original input content `raw_content` (and images if any); do not deviate from the role context.

## Input Definition

Input contains three fields:

- `figure_role`: Character role, selected from the following enumeration: `SELF` | `FAMILY` | `FRIEND` | `MENTOR` | `COLLEAGUE` | `PARTNER` | `PUBLIC_FIGURE` | `STRANGER`
- `raw_content`: Original text content
- `raw_images`: Original image URLs (if any)

## Task Objectives

A. High-fidelity content cleaning: generate `cleaned_content` that is completely faithful, with duplicate and noise removed
B. Metadata judgment: determine `original_source_type`, `confidence`, `included_dimensions`, `approx_date` according to rules
C. Completeness self-check: output `coverage_check` to confirm no key information is omitted

## Judgment Rules

### 1. Content Cleaning Rules

- `cleaned_content` must completely retain all valuable information; do not cause information loss through compression or rewriting.
- Only remove redundant repeated expressions; do not remove real facts.

### 2. Confidence Rule

`confidence` can only be one of the following values:

- `verbatim`: Explicit original words / direct quotation
- `artifact`: Objective material or verifiable statement
- `impression`: Subjective impression, speculation, or evaluation

### 3. Included Dimensions Rule

`included_dimensions` can select multiple values, limited to the following enumeration:

- `personality`: values, stable tendencies, preferences, motivations, boundaries
- `interaction_style`: speaking style, response style, conflict/feedback behavior
- `procedural_info`: methods, steps, tools, execution patterns, decision criteria
- `memory`: life events, stories, time markers, milestones, shared experiences
- `other`: content that cannot be reliably mapped to any category above

#### Dimension Decision

##### A. `personality`

Tag when the segment describes relatively stable inner orientation or tendency, such as:

- value priorities (e.g., fairness over speed, safety first)
- long-term preferences/dislikes
- recurring motivation/avoidance pattern
- explicit personal boundaries or principles

Do **not** tag `personality` for a one-off action unless the text explicitly states it as a stable pattern/value.

##### B. `interaction_style`

Tag when the segment describes **how the person communicates or reacts to others**, such as:

- tone, wording style, directness, politeness, emotional expression style
- how they ask questions, challenge, refuse, negotiate, give feedback
- behavior in disagreement/conflict situations
- channel/response rhythm if framed as communication habit

##### C. `procedural_info`

Tag when the segment provides actionable “how to do” knowledge, such as:

- explicit steps, workflow, checklist, sequence
- tool/stack/environment usage tied to that person’s method
- acceptance criteria, quality bar, delivery standard
- decision process (“because X, choose Y”), escalation boundaries

Do **not** tag `procedural_info` for generic industry common sense unless text ties it to this person’s own practice.

##### D. `memory`

Tag when the segment is about experiences/events with temporal or narrative context, such as:

- specific life/work events, turning points, incidents
- time nodes (year, period, before/after, phase)
- repeatedly told stories, shared memories, contextual episodes

##### E. `other`

Use only if none of the above can be assigned with confidence, including:

- pure metadata/noise (IDs, links, boilerplate without semantic content)
- vague statements with no clear personality/interaction/procedure/memory signal
- content outside task scope that cannot be mapped reliably

#### Rules

- Classify by **information type in the text itself**, not by what you guess the figure "is like".
- A segment can belong to **multiple dimensions** if it contains multiple information types.
- `included_dimensions` MUST include **all** matched dimensions; never force single-label.
- Typical co-occurrence:
    - event + method => `memory` + `procedural_info`
    - value + communication behavior => `personality` + `interaction_style`
    - event + value reflection => `memory` + `personality`
- If any matched dimension exists, do **not** add `other`.

### 4. Approximate Date Rule

- If there is explicit time or inductive time in the text, fill in the time as a string
- Otherwise output `null`

### 5. Original Source Type Rule

Classify the original source type of given content following strict unique matching rules, based on figure_role and the content perspective of cleaned_content. The core principle is: first determine "who wrote/said this content", then determine "content form".

#### Steps

1. First, perform the highest priority source perspective judgment:
    - If the content is the user describing the person/relationship/event (even if detailed and long), always classify as `NARRATIVE_FROM_USER` and end the judgment. This applies to:
        - Content that begins with words like "I think / he is / she usually / we used to / he once..."
        - Content that is paraphrase, summary, evaluation, memory, not original output
        - Content that includes quotes of the other person's words embedded in the user's narration, not original records
        - Any content that is not the original text written by the figure personally, even if it has a complete structure similar to an article
    - Only proceed to the next step of detailed classification if the content is original output directly produced by the figure personally. This requires meeting at least one of the following:
        - Explicitly first-person original text (not user paraphrase)
        - Explicitly chat screenshot/chat text (not paraphrase)
        - Explicitly original carrier content such as documents, articles, code
2. If the content is confirmed to be original output from the figure, classify into the unique matching type based on figure_role and content form:
    - **When figure_role = COLLEAGUE / MENTOR (work relationship):**
        - `WORK_RELATION_LONG_FORM`: Complete long text written by the figure personally, e.g. design documents, technical solutions, review reports, oncall records; features strong structure (complete titles/paragraphs/logic)
        - `WORK_RELATION_EDIT_TRACE`: The figure's modification traces on others' content, e.g. code review comments, document annotations, inline comments; features fragmented, comments on specific content
        - `WORK_RELATION_GUIDANCE`: Guidance content from the figure to you/others, e.g. mentoring records, instructive statements (not casual chat); features clear intention to "teach/guide/advise"
        - `WORK_RELATION_ARTIFACT`: The output artifact of the figure, e.g. code, design drafts, configuration files; features primarily non-natural language or strong tool attributes
    - **When figure_role = FAMILY / FRIEND / PARTNER (close relationship):**
        - `CLOSE_RELATION_LONG_FORM`: Long text written by the figure, e.g. letters, long messages, articles; features continuous expression, complete emotional or opinion expansion
        - `CLOSE_RELATION_PRIVATE_CHAT`: Original private chat records, e.g. WeChat/SMS conversations; features conversational structure (you say one sentence, I say one sentence)
        - `CLOSE_RELATION_SOCIAL_EXPRESSION`: Public expression from the figure, e.g. WeChat Moments, social media posts; features intended for public/friend circles
        - `CLOSE_RELATION_ARTIFACT`: Creative works from the figure, e.g. photos, works, handicrafts (text description of the content is also acceptable)
    - **When figure_role = SELF (yourself):**
        - `SELF_LONG_FORM`: Long text written by yourself, e.g. blog/diary/notes
        - `SELF_CHAT_MESSAGE`: Chat content sent by yourself
        - `SELF_SOCIAL_EXPRESSION`: Your own public expression on social media
        - `SELF_ARTIFACT`: Your own creative works, e.g. code/design
    - **When figure_role = PUBLIC_FIGURE (public figure):**
        - `PUBLIC_FIGURE_ARTICLE_BLOG`: Articles/blogs published by the figure personally
        - `PUBLIC_FIGURE_INTERVIEW_SPEECH_TRANSCRIPT`: Text transcripts of interviews or speeches
        - `PUBLIC_FIGURE_SOCIAL_EXPRESSION`: Social media statements
        - `PUBLIC_FIGURE_NEWS_REPORT`: Media reports (third-party, not user narration)
        - `PUBLIC_FIGURE_ARTIFACT`: Creative works, e.g. works/code

#### Notes

- You must make only one unique matching classification, do not output multiple labels
- Always follow the priority: first check if it is user narration, if yes output `NARRATIVE_FROM_USER` immediately, do not proceed to further classification
- As long as it is user perspective narration, it is strictly forbidden to misclassify as any LONG_FORM / CHAT / ARTIFACT type
- If the content is not original output from the figure personally, always fall back to `NARRATIVE_FROM_USER`

## Output Format

Output a strictly valid JSON object that conforms to the following schema, no extra content allowed:
{
"cleaned_content": "string",
"metadata": {
"original_source_type": "string",
"confidence": "verbatim|artifact|impression",
"included_dimensions": ["personality|interaction_style|procedural_info|memory|other"],
"approx_date": "string|null"
},
"coverage_check": {
"removed_as_redundant": ["list of content removed as redundant repetition/nonsense; empty array if no content removed"],
"completeness_pass": true
}
}

## Notes

- All field values must strictly follow the enumeration requirements; do not use custom values that are not in the given enumeration
- Do not add any explanatory text outside the JSON object
- Ensure all valuable information is retained; only true redundant content is removed
- Output language is exactly consistent with the input language
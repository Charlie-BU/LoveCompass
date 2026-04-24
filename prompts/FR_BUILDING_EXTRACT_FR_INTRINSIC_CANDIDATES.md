Act as a high-precision structured information extractor. Your task is to extract intrinsic field candidates of FigureAndRelation from the given text, and only return a strict JSON that follows all rules below.

## Extraction Target

You can only extract the following allowed keys from the input text:

- figure_mbti
- figure_birthday
- figure_occupation
- figure_education
- figure_residence
- figure_hometown
- figure_likes
- figure_dislikes
- figure_appearance
- words_figure2user
- words_user2figure
- exact_relation

## Input

Two input parameters will be provided:

- figure_name: the explicit name of the target figure in this extraction task; use this value when you need to disambiguate references like "he/she/they" in analysis, but never fabricate a new name if it is missing in `original_source_content`
- figure_role: one of `SELF` | `FAMILY` | `FRIEND` | `MENTOR` | `COLLEAGUE` | `PARTNER` | `PUBLIC_FIGURE` | `STRANGER`
- user_name: the canonical name of the user/narrator in this task; in scenarios requiring role-title normalization, never output labels such as "说话人", "我", "本人", etc., and use the provided `user_name` value instead
- original_source_content: the raw text to extract information from

## Core Principles: High Precision First

1. Only extract information that is **explicitly mentioned** or **can be obviously inferred**. Prefer missing a field over including an uncertain one.
2. If information is uncertain, semantically vague, or only reachable through weak association, do not include the field in the output.
3. Forbid fabricating information, filling in common sense, or outputting content just to complete the field list.
4. If multiple pieces of information exist for one field, you can merge them into a single string or keep them as separate items in a list, following the field format rules.
5. Never ignore negative words like "He's not ...", "She doesn't ...". Keep them.

## Definition of "Obvious Inference" (Strict Standard)

Inference is only allowed when there is strong unambiguous evidence in the text, for example:

- "He is a lawyer / practices at a law firm" → can infer `figure_occupation` = "lawyer"
- "She is a postgraduate at Tsinghua University / graduated from Fudan University with a bachelor's degree" → can extract the corresponding education information into `figure_education`
- "He lives in Shanghai permanently / currently resides in Beijing" → can extract into `figure_residence`

The following do NOT count as obvious inference:

- Guessing MBTI only from tone of text
- Inferring long-term personality from only one preference statement
- Inferring specific relationship details only from figure_role

## Field Caliber and Format

1. `figure_mbti`

- Only output this field when an explicit MBTI type (e.g. INTJ / ENFP) appears in the text
- Output must be a capital string of one of the 16 types: ISTJ, ISFJ, INFJ, INTJ, ISTP, ISFP, INFP, INTP, ESTP, ESFP, ENFP, ENTP, ESTJ, ESFJ, ENFJ, ENTJ
- Do not include the key if uncertain

2. String fields (output as `string` type):

- `figure_birthday`: birthday / date of birth text (keep the original information from the text, do not fabricate a standardized date)
- `figure_occupation`: occupation / job position
- `figure_education`: educational background
- `figure_residence`: permanent residence
- `figure_hometown`: hometown
- `figure_appearance`: external characteristics of the figure
- `exact_relation`: precise description of the relationship between the user and the target figure (only output when explicitly stated in the text; do not force-generate from figure_role)

3. List fields (output as `list[string]` type):

- `figure_likes`: things the figure likes
- `figure_dislikes`: things the figure dislikes
- `words_figure2user`: original verbatim words the figure said to the user (only extract if it is exact original words, do not modify)
- `words_user2figure`: original verbatim words the user said to the figure (only extract if it is exact original words, do not modify)

Requirements for all list fields:

- Only keep non-empty strings
- Remove duplicate items
- Each entry should be short and semantically complete
- Use array format even if there is only one entry
- Do not include the key if there is no valid information

## Role-Specific Hard Constraint

- If `figure_role` is `SELF`, never extract or output the following fields:
    - `words_figure2user`
    - `words_user2figure`
    - `exact_relation`
- This constraint has higher priority than other extraction rules.

# Output Format

- Only output a single JSON object, no Markdown, no explanation, no extra text
- The top level can only have one key: `fr_intrinsic_candidates`
- The value of `fr_intrinsic_candidates` is an object that only contains fields you are confident about; do not include uncertain fields
- Do not output any keys that are not in the allowed target list

# Notes

- Do not add any content outside of the JSON structure
- Strictly follow the "宁缺毋滥" rule: when in doubt, leave the field out

# Examples

Example 1:
Input:
figure_role: PARTNER
original_source_content: My girlfriend Lisa is ENFP, she was born on March 12, 1998, works as a graphic designer in Guangzhou where we live now. She likes matcha latte and hiking, hates coriander. She told me yesterday: "I'm so happy we're moving to a bigger apartment next month."
Output:
{
"fr_intrinsic_candidates": {
"figure_mbti": "ENFP",
"figure_birthday": "March 12, 1998",
"figure_occupation": "graphic designer",
"figure_residence": "Guangzhou",
"figure_likes": ["matcha latte", "hiking"],
"figure_dislikes": ["coriander"],
"words_figure2user": ["I'm so happy we're moving to a bigger apartment next month."]
}
}

Example 2:
Input:
figure_role: PUBLIC_FIGURE
original_source_content: [Celebrity Name] was born in Chengdu, graduated from the Central Academy of Drama, and is an actor now.
Output:
{
"fr_intrinsic_candidates": {
"figure_hometown": "Chengdu",
"figure_education": "graduated from the Central Academy of Drama",
"figure_occupation": "actor"
}
}

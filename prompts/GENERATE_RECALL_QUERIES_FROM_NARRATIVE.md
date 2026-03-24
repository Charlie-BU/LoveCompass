Generate a text query for vector database retrieval based on the provided narrative of the user's interaction with another person. The query will be used to retrieve relevant context about the relationship between the two people from the vector database.

The retrieval scope includes: past shared experiences between the user and the other person, historical conversation topics between the two parties, and existing derived insights related to the relationship between the two people.

Input narrative:
{{narrative}}

# Generation Rules
- Generate strictly based on the context understandable from the provided narrative, do not fabricate plots or add non-existent facts.
- Clearly distinguish between "the user" and "the other person": use "我" to refer to the user themself, and "对方" to refer to the other person in the narrative.
- Do not generate an empty string; even if the available information is minimal, generate a reasonable retrieval direction based on the existing context.

# Output Format
{"query": "[generated query string here]"}

# Notes
Only output valid JSON with one top-level field `query` whose value is the generated query string. Do not output any explanations, descriptions, or additional text.

# Settings
locale: zh_CN
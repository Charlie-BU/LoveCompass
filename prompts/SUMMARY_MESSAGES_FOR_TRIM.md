Compress earlier chat records into a short-term memory summary that retains the most contextually valuable information for future continuation of the conversation, rather than retelling the full original chat content. The summary should allow the system to still understand the current conversation relationship, factual background, and outstanding matters after the original chat history is forgotten.

Comply strictly with the following rules:

1. Output language must be exactly the same as the main language of the input content: output in Chinese if the input is mainly Chinese, output in English if the input is mainly English; do not switch languages without permission, and do not mix languages.
2. Use concise and accurate expressions; do not use JSON, Markdown headings or additional explanatory text.
3. Only retain information with sustained value for future conversation, including: confirmed facts, settings, preferences, identity information; the relationship between the two parties, address habits, tone preferences; unfinished topics, to-dos, agreements, plans; recent emotional status, interaction trend, obvious attitude changes.
4. Delete uninformative pleasantries, polite small talk, repeated expressions, one-off details and content that does not affect subsequent replies.
5. If the old summary duplicates content from new messages, merge and deduplicate, retaining the more complete expression.
6. If the old summary conflicts with new messages, prioritize retaining newer, more specific, clearer information.
7. Do not guess when there is uncertainty; only retain content that can be clearly supported by the input messages.
8. Limit output to no more than 6 lines, each line starts with "- ", do not use numbering.

# Steps

1. First organize all input content, including any existing old summary and newly added chat messages.
2. Screen and filter information according to the retention and deletion rules above, remove content that has no lasting value for subsequent conversation.
3. Handle duplicates and conflicts: merge duplicate content, resolve conflicts by retaining the latest and most specific information.
4. Do not add any guessed or unconfirmed content.
5. Format the retained information according to the required output format.

# Output Format

Output no more than 6 lines, each line is an independent information point starting with "- ", no other formatting, no additional text.

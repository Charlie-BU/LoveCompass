## How to run a single python file

- use `uv run -m <python_file_path>` to run a single python file
- e.g. `uv run -m test.agent`

## About Prompts

- Prompt content is stored in a remote repository and fetched at runtime via `getPrompt()` in `src/agents/prompt.py`.
- The mapping between prompt keys and URLs is maintained in `.env`.
- All prompts are also backed up in the project’s `prompts/` directory.
- A prompt key maps directly to a backup filename; to locate a prompt, find the corresponding `.md` file in `prompts/`.

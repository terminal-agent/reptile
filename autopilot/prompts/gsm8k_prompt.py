GSM8K_PROMPT = """You need to answer the question in one step with deep thinking, and only output the answer, no other text.

{question}

Attention:
1. Only output the answer, no other text.
2. Use `echo` to output the answer to `answer.txt` file.
"""

# https://github.com/volcengine/verl/blob/01eeb49e27622af69bf74269b89c34ddb7fefb7f/examples/data_preprocess/gsm8k.py#L57
GSM8K_PROMPT_VERL_VERSION = """{question} Let's think step by step and output the final answer after "####"."""

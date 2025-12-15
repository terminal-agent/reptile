MMLU_PRO_PROMPT = """You are an expert multiple-choice question answerer.
You can write code snippets in Python if necessary.
Write your answer (only with the option letter) to a file named 'answer.txt' using `cat` command.
Given a question and several options, choose the correct option.

Question: {question}

Options: {options}

Answer:

"""

# https://github.com/TIGER-AI-Lab/MMLU-Pro/blob/7eca4cee303b85033bf371bb9f00fe9278d0e30d/cot_prompt_lib/initial_prompt.txt#L1
MMLU_PRO_PROMPT_PAPER_VERSION = """
The following are multiple choice questions (with answers). Think step by step and then finish your answer with "the answer is (X)" where X is the correct letter choice.

Question: {question}

Options: {options}

Answer:

"""

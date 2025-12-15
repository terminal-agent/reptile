# This code is for evaluating whether the model output is correct or not
# using an LLM judge.
import argparse
import json
import os
import re
from collections import defaultdict

from openai import OpenAI

from autopilot.config import GLOBAL_CONFIG

ACCURACY_PROMPT = """
Your task is to label an answer to a question as ’CORRECT’ or ’WRONG’. You will be given the following data:
    (1) a question (posed by one user to another user),
    (2) a ’gold’ (ground truth) answer,
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label".
"""


def extract_json(text):
  """
  Extracts JSON content from a string, removing enclosing triple backticks and optional 'json' tag if present.
  If no code block is found, returns the text as-is.
  """
  text = text.strip()
  match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
  if match:
    json_str = match.group(1)
  else:
    json_str = text  # assume it's raw JSON
  return json_str


def evaluate_llm_judge(
  question: str, gold_answer: str, generated_answer: str
) -> bool:
  """Evaluate the generated answer against the gold answer using an LLM judge."""
  llm_configs = GLOBAL_CONFIG.models
  target_config = max(llm_configs, key=lambda x: x.priority)

  client = OpenAI(**target_config.credentials.dict())

  _default_parameters = dict(
    temperature=0, response_format={"type": "json_object"}
  )
  _default_parameters.update(target_config.parameters)

  response = client.chat.completions.create(
    messages=[
      {
        "role": "user",
        "content": ACCURACY_PROMPT.format(
          question=question,
          gold_answer=gold_answer,
          generated_answer=generated_answer,
        ),
      }
    ],
    **_default_parameters,
  )
  # print(response)
  label = json.loads(extract_json(response.choices[0].message.content))["label"]
  return True if label == "CORRECT" else False


def llm_judge(question: str, gold_answer: str, generated_answer: str) -> bool:
  # make sure the inputs are converted to strings, and strip leading/trailing spaces
  question = str(question).strip()
  gold_answer = str(gold_answer).strip()
  generated_answer = str(generated_answer).strip()

  eval_result = evaluate_llm_judge(question, gold_answer, generated_answer)

  return eval_result


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("question", type=str, help="The question")
  parser.add_argument("gold_answer", type=str, help="The gold answer")
  parser.add_argument("generated_answer", type=str, help="The generated answer")
  args = parser.parse_args()
  result = llm_judge(args.question, args.gold_answer, args.generated_answer)

  print(result)

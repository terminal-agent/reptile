"""
This is a copy of the gsm8k reward score from https://github.com/volcengine/verl/blob/main/verl/utils/reward_score/gsm8k.py
"""

import re


def extract_solution(solution_str, extract_type, method="strict"):
  assert method in ["strict", "flexible"]

  if extract_type == "gsm8k":
    if method == "strict":
      # this also tests the formatting of the model
      solutions = re.findall("#### (\\-?[0-9\\.\\,]+)", solution_str)
      if len(solutions) == 0:
        final_answer = None
      else:
        # take the last solution
        final_answer = solutions[-1].replace(",", "").replace("$", "")
    elif method == "flexible":
      answer = re.findall("(\\-?[0-9\\.\\,]+)", solution_str)
      final_answer = None
      if len(answer) == 0:
        # no reward is there is no answer
        pass
      else:
        invalid_str = ["", "."]
        # find the last number that is not '.'
        for final_answer in reversed(answer):
          if final_answer not in invalid_str:
            break
  elif extract_type == "mmlu":
    solution_str = solution_str.lower()
    if "the answer is" in solution_str:
      solution_str = solution_str.split("the answer is")[-1].strip()
      if solution_str.startswith("(") and ")" in solution_str:
        solution_str = solution_str[1 : solution_str.index(")")]
      else:
        solution_str = solution_str.split()[0]
      final_answer = solution_str.upper()
    else:
      final_answer = None
  return final_answer


if __name__ == "__main__":
  check_list = [
    "24 rooms",
    r"""To find out how many geckos Brandon has sold in the last two years, we need to follow these steps:

1. **Determine the number of geckos sold the previous year**: According to the problem, Brandon sold 86 geckos last year.
2. **Calculate the number of geckos sold this year**: The problem states that he sold twice as many geckos the year before. Therefore, if he sold 86 geckos last year, then this year he sold \( 2 \times 86 = 172 \) geckos.

### Final Answer:
Brandon has sold a total of 172 geckos over the past two years.""",
  ]
  for solution_str in check_list:
    final_answer = extract_solution(
      solution_str, extract_type="gsm8k", method="flexible"
    )
    print(final_answer)

  check_list_mmlu = [
    "After careful consideration, the answer is (C) Paris.",
    "The answer is B.",
    "Thus, the correct choice is (A).",
    "Therefore, the answer is D",
  ]
  for solution_str in check_list_mmlu:
    final_answer = extract_solution(
      solution_str, extract_type="mmlu", method="strict"
    )
    print(final_answer)

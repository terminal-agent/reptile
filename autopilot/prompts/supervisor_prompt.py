SUPERVISOR_PROMPT = """I'm showing you a conversation between a user and an LLM. It starts with the user asking the LLM to perform a task. Then the user runs the commands suggested by the LLM in a terminal, and pastes back the output from the terminal. Based on the feedback information, the LLM proposes another round of commands.

{history}

The above is what already happened, and now the LLM propose the following:


{last_round}


Do you think it is a legit next step? Or do you have suggestions to make? Reasoning through it,

- If you think it is good to proceed, generate a LGTM at the end of your response.
- Otherwise, give feedback.
- You don't need to try to come up with a complete alternative code, just give feedbacks or ideas.
- Don't try to be too much forward looking and reason into what future steps should be taken, just focus on the current step, if it is legit, say LGTM.

"""

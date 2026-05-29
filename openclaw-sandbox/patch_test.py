import re

with open("tests/test_task_queue.py") as f:
    content = f.read()
content = content.replace(
    "assert mock_move.call_count == 1",
    "print(mock_move.call_args_list); assert mock_move.call_count == 1",
)
with open("tests/test_task_queue.py", "w") as f:
    f.write(content)

from random import randint

q_version = "Lorem Ipsum"
q_text = "" \
"Lorem ipsum dolor sit amet consectetur adipiscing\n" \
"elit. Amet consectetur adipiscing elit quisque\n" \
"faucibus ex sapien. Quisque faucibus ex sapien\n" \
"vitae pellentesque sem placerat."
q_answer = {"name": "Thinker", "sprite":"assets/test/thinker.png", "genus": "Thinker"}
q_non_answer = {"name": "Viewer", "sprite":"assets/test/viewer.png", "genus": "Viewer"}

def get_pkg():
    choices = [q_non_answer for _ in range(3)]
    answer_idx = randint(0, 3)
    choices.insert(answer_idx, q_answer)
    return {
        "version": q_version,
        "dex_entry": q_text,
        "choices": choices,
        "answer": answer_idx
    }
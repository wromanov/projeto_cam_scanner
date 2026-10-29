"""Model input and navigation use separate terminal prompts."""
from cam_scanner.domain.enums import MainMenuChoice
from cam_scanner.terminal.ui import TerminalUI


def test_numeric_model_hint_one_does_not_replace_post_query_menu() -> None:
    answers = iter(("1", "3"))
    prompts: list[str] = []
    outputs: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    ui = TerminalUI(input_fn=read, output_fn=outputs.append)
    hint = ui.prompt_model_hint()
    assert hint is not None and hint.normalized == "1"
    assert not ui.has_pending_post_query_choice
    assert ui.post_query_menu() is MainMenuChoice.EXIT
    assert len(prompts) == 2
    assert prompts[0].startswith("Modelo")
    assert prompts[1].startswith("Escolha")

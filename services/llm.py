import anthropic


class LLMService:
    _SYSTEM = (
        "Du korrigierst diktierten deutschen Text minimal. "
        "Erlaubt: Groß-/Kleinschreibung, Zeichensetzung, offensichtliche "
        "Rechtschreib-/Grammatikfehler und das Entfernen reiner Füllwörter "
        "(ähm, äh) sowie unmittelbarer Wortwiederholungen. "
        "VERBOTEN: umformulieren, Synonyme wählen, Satzbau ändern, kürzen, "
        "zusammenfassen oder Inhalt hinzufügen. "
        "Behalte die exakte Wortwahl und Satzreihenfolge des Sprechers bei — "
        "es soll klingen wie das, was er gesagt hat, nur sauber geschrieben. "
        "Antworte ausschließlich mit dem korrigierten Text, ohne Erklärungen."
    )

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def improve_text(self, text: str) -> str:
        response = self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=self._SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        return response.content[0].text.strip()

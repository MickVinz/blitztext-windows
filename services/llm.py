import anthropic


class LLMService:
    _SYSTEM = (
        "Du bist ein präziser Text-Editor. "
        "Schreibe diktierten Text zu sauberem, natürlichem Deutsch um. "
        "Korrigiere Grammatik, Zeichensetzung und Satzstruktur. "
        "Behalte Inhalt und Ton bei. "
        "Antworte ausschließlich mit dem verbesserten Text, ohne Erklärungen."
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

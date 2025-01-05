import json

from django.conf import settings
from openai import OpenAI

class OpenAiService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.translation_assistant_id = settings.OPENAI_TRANSLATION_ASSISTANT_ID
        self.translation_assistant = self.client.beta.assistants.retrieve(assistant_id=self.translation_assistant_id)
        self.instructions = """
        Translate product auction titles and/or descriptions from Polish to German, focusing on common terms used in German auction markets for aftermarket car parts.

# Steps

1. **Understand the Context**: Identify that the content pertains to aftermarket car parts and should adhere to typical terminology used in German auctions.
2. **Title Translation**: Translate the product auction's title from Polish to German, ensuring it aligns with typical auction phrasing in Germany.
3. **Description Translation**: Translate the auction's description, maintaining clarity and using appropriate automotive terms common in German markets.
4. **Verification**: Ensure that translated terms accurately represent the Polish content while adopting commonly used German market language.

# Output Format

Provide the translated title or/and description in plain text. Each title and corresponding description should contain one or both:

- **Title**: [Translated Title]
- **Description**: [Translated Description]

# Notes

- Ensure the translation uses specific aftermarket car part vocabulary commonly recognized in the German auction market.
- Maintain the structural layout found in typical auction listings to ensure consistency and understandability in the intended market.

Response in JSON format. Below is a JSON SCHEMA for the response:
{
  "name": "translation_request",
  "strict": false,
  "schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Translated title."
      },
      "description": {
        "type": "string",
        "description": "Translated description."
      }
    },
    "additionalProperties": false,
    "required": []
  }
}

And here is an example of the JSON response:
{
  "title": "Translated Title",
  "description": "Translated Description"
}
"""
        self.default_model = "gpt-4o-mini"

    def translate_assistant(self, title=None, description=None):
        thread = thread = self.client.beta.threads.create()
        message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            content=f"Title: {title}\nDescription: {description}",
            role="user",
        )
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=self.translation_assistant.id,
            instructions=(f"Translate given example"),
        )

        # messages = self.client.beta.threads.messages.list(
        #     thread_id=thread.id,
        # )
        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            print(messages.data[0].content[0].text.value)

        else:
            print(run.status)

    def translate_completion(self, title=None, description=None):
        completition = self.client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": f"Title: {title}\nDescription: {description}"},
            ],
        )
        response_translation = json.loads(completition.choices[0].message.content)
        return response_translation
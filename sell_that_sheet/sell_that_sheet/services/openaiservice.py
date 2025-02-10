import json

from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from ..models.keyword_translation import KeywordTranslation

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

# Translation Dictionary
While translating, consider the following common terms used in German auctions for aftermarket car parts. In polish to german translation:
{translation_dictionary}

# Notes

- Ensure the translation uses specific aftermarket car part vocabulary commonly recognized in the German auction market.
- Maintain the structural layout found in typical auction listings to ensure consistency and understandability in the intended market.
- Make sure the capitalization and punctuation are accurate in the translated content. You can assume the input might be incorrect in terms of capitalization and punctuation.
- Make sure to use the translation dictionary provided to ensure consistency with the terms used in the German auction market.

Response in JSON format. Below is a JSON SCHEMA for the response:
{{
  "name": "translation_request",
  "strict": false,
  "schema": {{
    "type": "object",
    "properties": {{
      "title": {{
        "type": "string",
        "description": "Translated title."
      }},
      "description": {{
        "type": "string",
        "description": "Translated description."
      }}
    }},
    "additionalProperties": false,
    "required": []
  }}
}}

And here is an example of the JSON response:
{{
  "title": "Translated Title",
  "description": "Translated Description"
}}
"""
        self.default_model = "gpt-4o-mini"
        self.parameter_translation_instructions = """
        Translate a list of car parts parameters. Your job is to translate from Polish to German. You will be given pairs parameter-parameter_value and you should respond with translated pairs.

Input will be given in json and you should respond with json. Dont output anything else beside json with translated pairs.

When parameter values are split using pipe "|" character, you should translate each value separately and join them with pipe "|" character as well. Except for the parameters named "Numer katalogowy oryginału"/"OE/OEM Referenznummer(n)" where you should translate each value separately and join them with comma "," character.

When there are standalone numbers in the parameter value, you should translate them as they are. Leave them as they are.

If something is already translated and seems correct, leave it as it is.

example input: 
[
"Strona zabudowy": "lewa",
"Rodzaj świateł mijania": "Laserowe",
"Jakość części (zgodnie z GVO)" : "Q - oryginał z logo producenta części (OEM, OES)",
"Otwory": "dla haka holowniczego | do czujnika parkowania",
"Numer katalogowy oryginału": "123456 | 789012",
]

example output: 
[
"Einbauposition": "Links",
"Beleuchtungstechnik": "Laserlicht",
"Teilequalität (gemäß GVO)" : "Q – Originalteil mit Logo des Teileherstellers (OEM, OES)",
"Stoßstangenausschnitt": "Ausschnitt für Abschlepphaken| Ausschnitt für Parksensoren",
"OE/OEM Referenznummer(n)": "123456, 789012",
]
"""

    def translate_assistant(self, title=None, description=None, category=None):
        thread = thread = self.client.beta.threads.create()
        message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            content=f"Title: {title.lower()}\nDescription: {description.lower()}",
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

    def translate_completion(self, title=None, description=None, category=None):
        translation_dictionary = KeywordTranslation.objects.filter(Q(category=category) | Q(shared_across_categories=True)).values_list('original', 'translated')
        translation_dictionary = {original.lower(): translation.lower() for original, translation in translation_dictionary}

        instructions = self.instructions.format(translation_dictionary=json.dumps(translation_dictionary, indent=2))
        completion = self.client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Title: {title.lower()}\nDescription: {description.lower()}"},
            ],
        )
        response_translation = json.loads(completion.choices[0].message.content)
        return response_translation

    def translate_parameters(self, parameters):
        completion = self.client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": self.parameter_translation_instructions},
                {"role": "user", "content": json.dumps(parameters)},
            ],
        )
        response_translation = json.loads(completion.choices[0].message.content)
        return response_translation
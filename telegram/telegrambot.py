#!/usr/bin/env python

# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

import json
import logging
import os
from dataclasses import asdict

from db import load_db, save_db
from google.api_core import client_options
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud.translate_v3.services.translation_service import (
    TranslationServiceClient,
)
from migrations import ChatConfig, migrate
from openai import OpenAI

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ReactionEmoji
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

openai_client = OpenAI()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
# https://cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages
LANGUAGE_CODES = {"de-DE", "en-US", "uk-UA"}


serialized_config = load_db("config")
config = migrate(serialized_config)
print(config)


# https://cloud.google.com/translate/docs/advanced/translate-text-advance
# https://cloud.google.com/python/docs/reference/translate/latest/google.cloud.translate_v3.services.translation_service.TranslationServiceClient
def google_translate_text(
    text: str, project_id: str, source_language_code: str, target_language_code: str
) -> str:
    """Translating Text."""

    client = TranslationServiceClient()

    parent = f"projects/{project_id}"

    # Translate text from English to French
    # Detail on supported types can be found here:
    # https://cloud.google.com/translate/docs/supported-formats
    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",  # mime types: text/plain, text/html
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
        }
    )

    return response.translations[0].translated_text


# https://cloud.google.com/speech-to-text/v2/docs/chirp-model
async def google_speech_to_text(
    project_id: str,
    audio_data: bytes,
    language_codes: list[str] = ["de-DE"],
) -> cloud_speech.RecognizeResponse:
    """Transcribe an audio file."""
    # regional endpoint for more features for uk-UA
    # https://cloud.google.com/speech-to-text/docs/endpoints
    _client_options = client_options.ClientOptions(
        api_endpoint="europe-west4-speech.googleapis.com"
    )

    # Instantiates a client
    client = SpeechClient(client_options=_client_options)

    features = cloud_speech.RecognitionFeatures(enable_automatic_punctuation=True)

    recognitionConfig = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=language_codes,
        model="chirp",
        features=features,
    )

    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/europe-west4/recognizers/_",
        config=recognitionConfig,
        content=audio_data,
    )

    # Transcribes the audio into text
    response = client.recognize(request=request)

    # Concatenate the recognized text
    recognized_text = ""
    for result in response.results:
        recognized_text += result.alternatives[0].transcript + "\n"

    return recognized_text


def get_config(chat_id: int) -> ChatConfig:
    if not chat_id in config.chats:
        config.chats[chat_id] = ChatConfig()
    return config.chats[chat_id]


class ConfigureChat:
    def __init__(self, update: Update):
        self.update = update
        self.chat = get_config(update.effective_chat.id)
        args = update.message.text.split(" ")
        if len(args) < 2:
            self.value = None
        else:
            self.value = args[1]
        self.chat.trainer_id = update.message.from_user.id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"A{exc_type.__name__}: {exc_val}")
            await self.update.message.set_reaction(ReactionEmoji.SHRUG)
        else:
            save_db("config", asdict(config))
            await self.update.message.set_reaction(ReactionEmoji.OK_HAND_SIGN)


async def lang_command(update: Update, context):
    async with ConfigureChat(update) as configure:
        if not configure.value in LANGUAGE_CODES:
            raise ValueError("Invalid language code")
        configure.chat.trainer_language = configure.value


async def otherlang_command(update: Update, context):
    async with ConfigureChat(update) as configure:
        if not configure.value in LANGUAGE_CODES:
            raise ValueError("Invalid language code")
        configure.chat.learner_language = configure.value


async def suggestions_command(update: Update, context):
    async with ConfigureChat(update) as configure:
        if configure.value == "on":
            configure.chat.suggestions = True
        elif configure.value == "off":
            configure.chat.suggestions = False
        else:
            raise ValueError("Invalid value")


async def config_command(update: Update, context):
    # show current config
    config = get_config(update.effective_chat.id)
    pretty_config = json.dumps(asdict(config), indent=4)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"<blockquote>{pretty_config}</blockquote>",
        parse_mode="HTML",
    )


async def translate_command(update: Update, context):
    print("button pressed!")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="...")
    try:
        # get text
        text = update.message.text.split(" ", 1)[1]
        # translate
        translated = text
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=translated
        )
    except Exception as e:
        print("\033[33m" + str(e) + "\033[0m")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✘")


async def readout(update: Update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔉...")


async def help_command(update: Update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
/lang de-DE
/otherlang de-DE
/suggestions on|off
/config
Languages: {" ".join(LANGUAGE_CODES)}
""",
    )


def render_button(text: str, data: str):
    keyboard = [[InlineKeyboardButton(text, callback_data=data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


# transcribe
async def transcribe_and_translate(update: Update, context: CallbackContext):
    print("voice")
    chat_config = get_config(update.effective_chat.id)
    is_trainer = update.message.from_user.id == chat_config.trainer_id
    from_language = (
        chat_config.trainer_language if is_trainer else chat_config.learner_language
    )
    to_language = (
        chat_config.learner_language if is_trainer else chat_config.trainer_language
    )
    bot_message = await context.bot.send_message(
        chat_id=update.effective_chat.id, text="🎙..."
    )
    try:
        # get audio
        voice = await update.message.voice.get_file()
        voice_data: bytearray = await voice.download_as_bytearray()

        # transcribe
        voice_language = from_language
        transcribed = await google_speech_to_text(
            project_id=project_id,
            audio_data=bytes(voice_data),
            language_codes=[voice_language],
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=f"<blockquote>{transcribed}</blockquote>",
            parse_mode="HTML",
        )

        # translate
        bot_message = await context.bot.send_message(
            chat_id=update.effective_chat.id, text="文A ..."
        )
        translated = google_translate_text(
            transcribed,
            project_id,
            from_language,
            to_language,
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=f"<blockquote>{translated}</blockquote>",
            parse_mode="HTML",
        )

        # provide the learner with possible answers to the trainer's message
        if chat_config.suggestions and is_trainer:
            bot_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✏️...",
            )
            completion = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a teacher in the ${from_language} language and particiapte in a group chat between a native speaker and an immigrant who learns the language and culture. The trainer speaks voice messages in ${from_language} and you want to provide the learner with three possible answers to the trainer's message. You provide them in ${from_language} to provide translations and explanations in ${to_language}.",
                    },
                    {"role": "assistant", "content": transcribed},
                    {
                        "role": "system",
                        "content": "Provide the learner with possible answers to the trainer's message. Try to be short and concise.",
                    },
                ],
            )
            suggestions = completion.choices[0].message.content

            # print(completion.choices[0].message)
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=bot_message.message_id,
                text=f"<blockquote>{suggestions}</blockquote>",
                parse_mode="HTML",
            )

    except Exception as e:
        print(e)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text="✘",
        )


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    # if query.data == "translate":
    #     print("translate")
    #     await translate(update, context)
    if query.data == "readout":
        print("readout")
        print(query.message.text)
        await readout(update, context)
        await query.answer()


if __name__ == "__main__":
    print("Starting bot...")

    # # transcribe ~/s.flac
    # audio_data = open(os.path.expanduser("~/s.flac"), "rb").read()
    # transcribed = google_speech_to_text("deutsch-training-413809", audio_data)
    # print(transcribed)
    # exit()

    # # translate "Hello, world!"
    # text_data = "Hello, world!"
    # translated = google_translate_text(
    #     text_data, project_id, "en", "de"
    # )
    # print(translated)
    # exit()

    # chatgpt complete
    # completion = openai_client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {
    #             "role": "user",
    #             "content": "Write a haiku about recursion in programming.",
    #         },
    #     ],
    # )

    # print(completion.choices[0].message)
    # exit()

    application = (
        ApplicationBuilder().token(telegram_bot_token).concurrent_updates(True).build()
    )

    application.add_handler(CommandHandler("translate", translate_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("otherlang", otherlang_command))
    application.add_handler(CommandHandler("suggestions", suggestions_command))
    application.add_handler(CommandHandler("config", config_command))

    application.add_handler(CallbackQueryHandler(button))

    voice_handler = MessageHandler(filters.VOICE, transcribe_and_translate, block=False)
    application.add_handler(voice_handler)

    application.run_polling()

# fotos übersetzen
# test
# conversation, comment on lanugage -> let them speak german
#     -> chatgpt: translate if learner language, comment if german
# test

#!/usr/bin/env python

# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

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
    if chat_id in config.chats:
        return config.chats[chat_id]
    return config.default


async def config_command(update: Update, context):
    # set language codes like "/config de-DE en-US"
    if update.message.text == "/config":
        # show current config
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=asdict(get_config(update.effective_chat.id)),
        )
    else:
        try:
            (trainer_language, learner_language) = update.message.text.split(" ")[1:]
            if (
                not trainer_language in LANGUAGE_CODES
                or not learner_language in LANGUAGE_CODES
            ):
                raise ValueError("Invalid language codes")
            config.chats[update.effective_chat.id] = ChatConfig(
                trainer_language=trainer_language, learner_language=learner_language
            )
            save_db("config", asdict(config))
            await update.message.set_reaction(ReactionEmoji.OK_HAND_SIGN)
        except ValueError as e:
            print(e)
            await update.message.set_reaction(ReactionEmoji.SHRUG)


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
        text="/config\n/config [trainer] [learner]",
    )


def render_button(text: str, data: str):
    keyboard = [[InlineKeyboardButton(text, callback_data=data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


# transcribe
async def transcribe_and_translate(update: Update, context):
    print("voice")
    chat_config = get_config(update.effective_chat.id)
    bot_message = await context.bot.send_message(
        chat_id=update.effective_chat.id, text="🎙..."
    )
    try:
        # get audio
        voice = await update.message.voice.get_file()
        voice_data: bytearray = await voice.download_as_bytearray()
        # transcribe
        transcribed = await google_speech_to_text(
            project_id=project_id,
            audio_data=bytes(voice_data),
            language_codes=[chat_config.learner_language],
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=transcribed,
        )
        # translate
        bot_message = await context.bot.send_message(
            chat_id=update.effective_chat.id, text="文A ..."
        )
        translated = google_translate_text(
            transcribed,
            project_id,
            chat_config.learner_language,
            chat_config.trainer_language,
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=translated,
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

    # # translate "Hello, world!"
    # text_data = "Hello, world!"
    # translated = google_translate_text(
    #     text_data, project_id, "en", "de"
    # )
    # print(translated)

    application = (
        ApplicationBuilder().token(telegram_bot_token).concurrent_updates(True).build()
    )

    translate_handler = CommandHandler("translate", translate_command)
    application.add_handler(translate_handler)
    help_handler = CommandHandler("help", help_command)
    application.add_handler(help_handler)
    config_handler = CommandHandler("config", config_command)
    application.add_handler(config_handler)

    application.add_handler(CallbackQueryHandler(button))

    voice_handler = MessageHandler(filters.VOICE, transcribe_and_translate, block=False)
    application.add_handler(voice_handler)

    application.run_polling()

# german dictation
# second test

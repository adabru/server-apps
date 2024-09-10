#!/usr/bin/env python

# https://cloud.google.com/speech-to-text/v2/docs/chirp-model
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

import logging
import os

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud.translate_v3.services.translation_service import (
    TranslationServiceClient,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
languages = ["de-DE", "en-US"]


# https://cloud.google.com/translate/docs/advanced/translate-text-advance
# https://cloud.google.com/python/docs/reference/translate/latest/google.cloud.translate_v3.services.translation_service.TranslationServiceClient
def google_translate_text(
    text: str, project_id: str, source_language_code: str, target_language_code: str
) -> str:
    """Translating Text."""

    client = TranslationServiceClient()

    parent = f"projects/{project_id}"
    print(parent)

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


async def google_speech_to_text(
    project_id: str,
    audio_data: bytes,
) -> cloud_speech.RecognizeResponse:
    """Transcribe an audio file."""
    # Instantiates a client
    client = SpeechClient()

    features = cloud_speech.RecognitionFeatures(enable_automatic_punctuation=True)

    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=languages,
        model="long",
        features=features,
    )

    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/global/recognizers/_",
        config=config,
        content=audio_data,
    )

    # Transcribes the audio into text
    response = client.recognize(request=request)

    # Concatenate the recognized text
    recognized_text = ""
    for result in response.results:
        recognized_text += result.alternatives[0].transcript + "\n"

    return recognized_text


async def translate(update: Update, context):
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


async def help(update: Update, context):
    keyboard = [[InlineKeyboardButton("Translate", callback_data="translate")]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!",
        reply_markup=reply_markup,
    )


async def echo(update: Update, context):
    # show typing status
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )
    # Echo the user's message back to them
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text
    )


def render_button(text: str, data: str):
    keyboard = [[InlineKeyboardButton(text, callback_data=data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


# transcribe
async def transcribe_and_translate(update: Update, context):
    print("voice")
    # # show typing status
    # await context.bot.send_chat_action(
    #     chat_id=update.effective_chat.id, action="typing"
    # )
    bot_message = await context.bot.send_message(
        chat_id=update.effective_chat.id, text="🎙..."
    )
    try:
        # get audio
        voice = await update.message.voice.get_file()
        voice_data: bytearray = await voice.download_as_bytearray()
        # transcribe
        transcribed = await google_speech_to_text(project_id, bytes(voice_data))
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
            transcribed, project_id, languages[0], languages[1]
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=translated,
            reply_markup=render_button("🔉", "readout"),
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
    #     text_data, project_id, languages[1], languages[0]
    # )
    # print(translated)

    application = (
        ApplicationBuilder().token(telegram_bot_token).concurrent_updates(True).build()
    )

    translate_handler = CommandHandler("translate", translate)
    application.add_handler(translate_handler)
    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)

    application.add_handler(CallbackQueryHandler(button))

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    voice_handler = MessageHandler(filters.VOICE, transcribe_and_translate, block=False)
    application.add_handler(voice_handler)

    application.run_polling()

# command to set language codes
# first test
# run pyinfra
# google_text_to_speech
# -->

# cutoffs:
# - hardcode languages
# - show button every time

#!/usr/bin/env python

# https://cloud.google.com/speech-to-text/v2/docs/chirp-model
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

import asyncio
import logging
import os

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


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
        language_codes=["de-DE"],
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


async def start(update: Update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
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


# transcribe
async def transcribe(update: Update, context):
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
        transcribed = await google_speech_to_text(
            "deutsch-training-413809", bytes(voice_data)
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text=transcribed,
        )
    except Exception as e:
        print(e)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=bot_message.message_id,
            text="✘",
        )


if __name__ == "__main__":
    print("Starting bot...")

    # # transcribe ~/s.flac
    # audio_data = open(os.path.expanduser("~/s.flac"), "rb").read()
    # transcribed = google_speech_to_text("deutsch-training-413809", audio_data)
    # print(transcribed)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).concurrent_updates(True).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    # echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    voice_handler = MessageHandler(filters.VOICE, transcribe, block=False)
    application.add_handler(voice_handler)

    application.run_polling()

# button translate + speak
# run pyinfra
# -->

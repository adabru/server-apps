```bash
python -m venv .pyinfra
# vscode will auto-select the venv

pip install pyinfra

# setup server; enter sudo password when asked
pyinfra adabru deploy.py
# to run selected tasks
TAGS=filesharing,webhooks pyinfra adabru deploy.py
```

To share a file, run `scp shared.zip adabru:/home/adaburu/filesharing/shared.zip` and download from adabru.de/d/shared.zip.

Issues: https://github.com/pyinfra-dev/pyinfra/issues/1043

### Telegram Bot

Initial source is this: https://medium.com/@fourlastor/captioning-telegrams-voice-messages-part-1-d90b26b03616

Open botfather at t.me/botfather

```
/newbot
transcribe
adabru_de_transcribe_bot
```

Store API token in .env.

Edit the bot in the chat, "Allow Groups?" -> "Turn groups on", "Groups Privacy" -> "Turn off", "Edit Botpic".

Repeat with for transcribe_dev, adabru_de_transcribe_dev_bot, store token in dev.env .

Enable google APIs: https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com,cloudresourcemanager.googleapis.com,speech.googleapis.com

Create google service account (api key equivalent):

```bash
# install and init gcloud
trizen -S google-cloud-cli
gcloud init
gcloud auth application-default login

# create service account
gcloud config set project deutsch-training-413809
gcloud iam service-accounts create deutsch-training-service \
    --description="API access to transcription and translation." \
    --display-name="Deutsch Training Service"
# add speech api permission
gcloud projects add-iam-policy-binding deutsch-training-413809 \
    --member="serviceAccount:deutsch-training-service@deutsch-training-413809.iam.gserviceaccount.com" \
    --role="roles/speech.client"
# generate private key
gcloud iam service-accounts keys create ./telegram/private-key.json \
    --iam-account deutsch-training-service@deutsch-training-413809.iam.gserviceaccount.com
```

For local development:

```bash
# initial setup
python -m venv .telegram
# "select interpreter" in vscode
pip install google-cloud-speech google-cloud-translate python-telegram-bot
pip freeze > telegram/requirements.txt

# start bot
set -a && . telegram/dev.env && set +a && pymon ./telegram/telegrambot.py
# open at t.me/adabru_de_transcribe_bot
```

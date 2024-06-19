from getpass import getuser
import os
from pyinfra.operations import pacman, systemd, files, server, pip
from pyinfra import config

# load .env
with open(".env", "r") as fh:
    env = dict(
        tuple(line.replace("\n", "").split("="))
        for line in fh.readlines()
        if not line.startswith("#")
    )

config.SUDO = True
config.USE_SUDO_PASSWORD = env["SUDO_PASSWORD"]
admin = getuser()


def base():
    pacman.packages(name="Install packages.", packages=["nginx", "webhook", "acme.sh"])

    # .bashrc
    files.put(name="Update .bashrc.", src="bashrc", dest=f"/home/{admin}/.bashrc")


def nginx():
    # nginx
    server.user(name="Add http to admin group.", user="http", groups=[admin])
    files.put(
        name="Update nginx.config.",
        src="nginx/nginx.conf",
        dest="/etc/nginx/nginx.conf",
        user="root",
        group="root",
        mode="644",
    )
    systemd.service(
        name="Update nginx service.",
        service="nginx",
        running=True,
        enabled=True,
        reloaded=True,
    )
    files.directory(
        name="Open home-directory to group/nginx.", path=f"/home/{admin}", mode="750"
    )

    # acme.sh
    files.put(
        name="Update acme.service.",
        src="acme.sh/acme.service",
        dest="/etc/systemd/system/acme.service",
        user="root",
        group="root",
        mode="644",
    )
    files.put(
        name="Update acme.timer.",
        src="acme.sh/acme.timer",
        dest="/etc/systemd/system/acme.timer",
        user="root",
        group="root",
        mode="644",
    )
    systemd.service(
        name="Update acme service.",
        service="acme.timer",
        running=True,
        enabled=True,
    )


def filesharing():
    # filesharing
    files.sync(
        name="Create folder for filesharing.",
        dest=f"/home/{admin}/filesharing",
        src="filesharing",
    )


def webhooks():
    # webhooks
    files.template(
        name="Update webhook config.",
        src="webhook/hooks.json.j2",
        dest="/etc/webhook/hooks.json",
        user="root",
        group="root",
        mode="644",
        __admin=admin,
        __env=env,
    )
    systemd.service(
        name="Update webhook service.",
        service="webhook",
        running=True,
        enabled=True,
        restarted=True,
    )


def telegram():
    # telegram bot
    files.template(
        name="Update telegrambot service.",
        src="telegram/telegrambot.service.j2",
        dest="/etc/systemd/system/telegrambot.service",
        user="root",
        group="root",
        mode="644",
        __admin=admin,
    )
    files.sync(
        name="Copy folder for telegram.",
        dest=f"/home/{admin}/telegram",
        src="telegram",
    )
    pip.packages(
        name="Install Python packages from requirements.txt",
        packages=f"/home/{admin}/telegram/requirements.txt",
        virtualenv=f"/home/{admin}/.venv/telegram",
        virtualenv_kwargs={"venv": True},
        present=True,
    )
    # systemd.service(
    #     name="Update telegrambot service.",
    #     service="telegrambot",
    #     running=True,
    #     enabled=True,
    #     reloaded=True,
    # )

def nextcloud():
    # i docker

tags = os.environ.get("TAGS", "base,nginx,filesharing,webhooks,telegram").split(",")
print(f"Running tasks: {tags}")
for tag in tags:
    # run the function with the same name as the argument
    globals()[tag]()

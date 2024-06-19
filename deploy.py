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
    pacman.packages(name="Install packages.", packages=["caddy", "webhook"])

    # .bashrc
    files.put(name="Update .bashrc.", src="bashrc", dest=f"/home/{admin}/.bashrc")


def caddy():
    # caddy
    server.user(
        name="Add caddy user, include in admin group.", user="caddy", groups=[admin]
    )
    files.put(
        name="Update Caddyfile.",
        src="caddy/Caddyfile",
        dest="/etc/caddy/Caddyfile",
        user="caddy",
        group="caddy",
        mode="644",
    )
    files.directory(
        name="Allow home-directory to group access (caddy is in admin group).",
        path=f"/home/{admin}",
        mode="750",
    )
    files.put(
        name="Update file caddy.service.",
        src="caddy/caddy.service",
        dest="/etc/systemd/system/caddy.service",
        user="root",
        group="root",
        mode="644",
    )
    systemd.service(
        name="Reload caddy service.",
        service="caddy.service",
        running=True,
        enabled=True,
        reloaded=True,
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
    pass


tags = os.environ.get("TAGS", "base,caddy,filesharing,webhooks,telegram").split(",")
print(f"Running tasks: {tags}")
for tag in tags:
    # run the function with the same name as the argument
    globals()[tag]()

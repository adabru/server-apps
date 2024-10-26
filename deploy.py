import os
from getpass import getuser

from pyinfra import config, host
from pyinfra.api import operation
from pyinfra.facts.hardware import Ipv4Addresses
from pyinfra.operations import files, pacman, pip, server, systemd

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
    pacman.packages(
        name="Install packages.",
        packages=[
            "caddy",
            "webhook",
            "docker",
            "python",
            "pacman-contrib",
            "transmission-cli",
        ],
    )

    # .bashrc
    files.put(name="Update .bashrc.", src="bashrc", dest=f"/home/{admin}/.bashrc")

    server.user(
        name="Add admin to transmission group.",
        user=admin,
        groups=[admin, "sudo", "transmission"],
    )


def caddy():
    # caddy
    server.user(
        name="Add caddy user, include in admin and transmission group.",
        user="caddy",
        groups=[admin, "transmission"],
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
    # filesharing via caddy
    files.sync(
        name="Create folder for filesharing.",
        dest=f"/home/{admin}/filesharing",
        src="filesharing",
        user=admin,
        group=admin,
    )

    # filesharing via torrent
    # https://wiki.archlinux.org/title/Transmission
    # /var/lib/transmission/.config/transmission-daemon/settings.json

    systemd.service(
        name="Start transmission service.",
        service="transmission",
        running=True,
        enabled=True,
    )
    # prepare transmission data dir as service might not have created it yet
    files.directory(
        name="Create folder for transmission.",
        path="/var/lib/transmission",
        mode="750",
        user="transmission",
        group="transmission",
    )
    files.directory(
        name="Create folder for transmission Downloads.",
        path="/var/lib/transmission/Downloads",
        mode="775",
        user="transmission",
        group="transmission",
    )
    files.directory(
        name="Create folder for transmission torrents.",
        path="/var/lib/transmission/torrents",
        mode="775",
        user="transmission",
        group="transmission",
    )
    files.link(
        name="Link filesharing/transmission to transmission Downloads folder.",
        path=f"/home/{admin}/filesharing/transmission",
        target="/var/lib/transmission/Downloads",
    )
    files.link(
        name="Link filesharing/torrents to transmission torrents folder.",
        path=f"/home/{admin}/filesharing/torrents",
        target="/var/lib/transmission/torrents",
    )


def webhooks():
    # webhooks
    # https://github.com/adnanh/webhook/blob/master/docs/Hook-Definition.md
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
        exclude_dir=["db"],
    )
    pip.packages(
        name="Install Python packages from requirements.txt",
        requirements=f"/home/{admin}/telegram/requirements.txt",
        virtualenv=f"/home/{admin}/.venv/telegram",
        virtualenv_kwargs={"venv": True},
        present=True,
    )
    systemd.service(
        name="Update telegrambot service.",
        service="telegrambot",
        running=True,
        enabled=True,
        restarted=True,
    )


def nextcloud():
    @operation()
    def Log(msg):
        host.noop(msg)
        if False:
            yield

    ip_addresses = host.get_fact(Ipv4Addresses)
    public_ip = None
    for interface, ip in ip_addresses.items():
        if not ip.startswith(("127.", "172.")):
            public_ip = ip
            break
    Log(
        "Instructions are available at https://github.com/nextcloud/all-in-one/blob/main/reverse-proxy.md"
    )
    Log(f"Nextcloud aio-setup will run on https://{public_ip}:8080")
    server.shell(
        name="Run Nextcloud Docker container",
        commands="""
        docker run \
        --init \
        --sig-proxy=false \
        --name nextcloud-aio-mastercontainer \
        --restart always \
        --publish 8080:8080 \
        --env APACHE_PORT=11000 \
        --env APACHE_IP_BINDING=127.0.0.1 \
        --volume nextcloud_aio_mastercontainer:/mnt/docker-aio-config \
        --volume /var/run/docker.sock:/var/run/docker.sock:ro \
        nextcloud/all-in-one:latest
        """,
    )


tags = os.environ.get("TAGS", "base,caddy,filesharing,webhooks,telegram").split(",")
print(f"Running tasks: {tags}")
for tag in tags:
    # run the function with the same name as the argument
    globals()[tag]()

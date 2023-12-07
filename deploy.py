from getpass import getuser
from pyinfra.operations import pacman, systemd, files, server
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


pacman.packages(name="Install packages.", packages=["nginx", "webhook", "acme.sh"])

# .bashrc
files.put(name="Update .bashrc.", src="bashrc", dest="/home/{admin}/.bashrc")

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
    reloaded=True,
)

# filesharing
files.sync(
    name="Create folder for filesharing.",
    dest=f"/home/{admin}/filesharing",
    src="filesharing",
)

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

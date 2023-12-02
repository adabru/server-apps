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


pacman.packages(name="Install packages.", packages=["nginx", "webhook"])

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

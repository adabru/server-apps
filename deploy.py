from getpass import getuser
from pyinfra.operations import pacman, systemd, files, server
from pyinfra import config


config.SUDO = True
admin = getuser()


pacman.packages(name="Install nginx.", packages=["nginx"])
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

files.directory(name="Open home-directory to group.", path=f"/home/{admin}", mode="750")


# filesharing
files.sync(
    name="Create folder for filesharing",
    dest=f"/home/{admin}/filesharing",
    src="filesharing",
)

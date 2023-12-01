```bash
pipx install pyinfra
# setup server; enter sudo password when asked
pyinfra adabru deploy.sh
```

This vscode cofiguration is for pyinfra installed via pipx. If autocompletion doesn't work try to delete the `"python.defaultInterpreterPath"` setting or checkout `head $(which pyinfra)`.

To share a file, run `scp shared.zip adabru:/home/adaburu/filesharing/shared.zip` and download from adabru.de/d/shared.zip.

Issues: https://github.com/pyinfra-dev/pyinfra/issues/1043

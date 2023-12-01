from pyinfra.operations import files

files.file("/test", present=True, _sudo=True)

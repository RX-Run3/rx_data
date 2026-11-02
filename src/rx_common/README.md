[TOC]

# $R_X$ common

This project holds tools that can be shared by multiple $R_X$ analyses, e.g. enums.

## Transfer of outputs

To transfer outputs from the `$ANADIR` at CERN or IHEP from to your local `$ANADIR` do:

```bash
rx_sync -s IHEP -t LOCAL -p DB/fitter
```

which will transfer the `fitter` directory from `IHEP` to this machine.
When the directory transfered contains many small files use

```bash
rx_sync -s IHEP -t LOCAL -p DB/fitter -S
```

to run it in streaming mode, e.g.

- Make a tarball from the directory
- Put the tarball in stdout and pick it in stdin before untarring

[Note]: To allow local machine to authenticate to SSH server use control master sockets



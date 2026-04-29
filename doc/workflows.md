# Description

This documentation explains:

- What workflows are available
- How to run them in a computing cluster
- How to setup a dashboard with [flowo](https://github.com/zhanghaomiao/flowo)

# HTCondor plugin

This should allow snakemake to run workflows through HTCondor jobs. For this follow 
the instructions [here](https://github.com/htcondor/snakemake-executor-plugin-htcondor)

# FLOWO dashboard

Once the instructions below be followed one should be able to do something like:

```bash
snakemake -s snakemake/rules/ntuples/friends.smk \
          --configfile snakemake/configs/ntuples/friends.yaml \
          --profile ihep \                      # Change this to the HTCondor executor you use 
          --logger=flowo \
          --logger-flowo-name=friend-trees \
          --keep-going                          # This will allow next jobs to be submitted even if there are failures
```

Access to a computing cluster, e.g. something to login with `ssh user@lxplus.cern.ch` 

## First-Time Setup (pulling images)

Only needed if images are not cached locally (`podman images`).

```bash
podman pull docker.1ms.run/library/postgres:15-alpine
podman pull ghcr.io/zhanghaomiao/flowo:latest
```

> Note: standard Docker Hub and most Alibaba mirrors are blocked in China. Use `docker.1ms.run` as the mirror.

---

## Starting Flowo

### 1. Kill any stale processes from previous sessions

```bash
pkill -9 caddy
pkill -9 fastapi
```

### 2. Start the database

```bash
podman run -d --network host \
              --env-file flowo/.env \
              --name flowo_db \
  docker.1ms.run/library/postgres:15-alpine
```

### 3. Start the app

```bash
podman run -d --network  host \
              --env-file flowo/.env \
              --name     flowo_app \
              -e POSTGRES_HOST=127.0.0.1 \
              -e POSTGRES_PORT=5432 \
              -v /publicfs/ucas/user/campoverde:/publicfs/ucas/user/campoverde:ro \
              ghcr.io/zhanghaomiao/flowo:latest
```

### 4. Copy the Caddyfile and restart

```bash
podman cp flowo/Caddyfile flowo_app:/etc/caddy/Caddyfile
podman restart flowo_app
```

### 5. Verify both containers are running

```bash
podman ps
```

You should see `flowo_db` and `flowo_app` both with status `Up`.

---

## Connecting from Your Laptop

Open an SSH tunnel:

```bash
ssh -L 3100:localhost:80 campoverde@lxlogin002.ihep.ac.cn
```

Then open your browser at `http://localhost:3100`.

> 80 is the port Caddy listens on on the server 3100 is the local port on your laptop (chosen to avoid conflicts — you can use any free port).

---

## Restarting After a Session (containers already exist)

If containers exist but are stopped:

```bash
pkill -9 caddy
pkill -9 fastapi
podman start flowo_db
podman start flowo_app
```

---

## Architecture Overview

```
You (browser)
    │  port 3100 (laptop) → port 80 (server, SSH tunnel)
    ▼
Caddy  (inside flowo_app, port 80)
    │  port 8000
    ▼
FastAPI  (inside flowo_app, port 8000)
    │  port 5432
    ▼
Postgres  (flowo_db, port 5432)
```

Caddy and FastAPI both run inside the `flowo_app` container, managed by `supervisord`.

---

## Notes

- Container image storage is configured in `~/.config/containers/storage.conf` to use `/tmp/$USER/containers/storage`. This path may be wiped on node reboots, requiring images to be re-pulled.
- Port 3100 is exposed on the host network. Access is protected by flowo's login, but use the SSH tunnel to avoid exposing it to other users on the cluster.

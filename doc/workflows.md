[TOC]

# Description

This documentation explains:

- What workflows are available
- How to run them in a computing cluster
- How to setup a dashboard with [flowo](https://github.com/zhanghaomiao/flowo)

# Available workflows

## Friend trees

For this run:

```bash
snakemake -s snakemake/rules/ntuples/friends.smk --configfile snakemake/configs/ntuples/friends.yaml -c 10
```

where the trees are:

- `mass`: The candidates masses are recalculated assuming that the two leptons are pions and kaons. Needed for misID studies.

- `swp_jpsi_misid`: Branches corresponding to lepton kaon swaps that make the resonant mode leak into rare modes. Where the swap is inverted and the $J/\psi$ mass provided

- `swp_cascade`: Branches corresponding to $D\to K\pi$ with $\pi\to\ell$ swaps, where the swap is inverted and the $D$ mass provided.

- `hop`: With the $\alpha$ and mass branches calculated

- `brem_track_2`: This will calculate branches associated to the brem correction. 
    The branches will include:
    - Masses of B and Jpsi.
    - Momenta of mesons and electrons.
    - Derived quantities like `DIRA` or the `brem` categories.

- `mva`: With the BDT branches 
- `smear`: This will calculate the smeared masses `B_Mass_smr` and `Jpsi_Mass_smr` and `q2_smr`.

and they depend on each other as:

```mermaid
graph TD
  mass([mass])
  swp_jpsi_misid([swp_jpsi_misid])
  swp_cascade([swp_cascade])
  hop([hop])
  brem_track_2([brem_track_2])
  smear([smear])
  mva([mva])

  brem_track_2 -->|needs corrected masses| smear
  brem_track_2 -->|training on brem features| mva
  hop -->|required by mva| mva
  smear -->|q² wise models from smeared q²| mva
```

The workflow will take care of everything. The user should only have to check the `yaml` config file
and update it.

## Ntuple transfers

Run:

```bash
snakemake -s snakemake/rules/ntuples/transfer.smk --configfile snakemake/configs/ntuples/transfer.yaml -c 4
```

to run the ntuple tranfer from a remote server. The transfer will run:

- Without password authentication but instead public keys
- To transfer a specific set of files from a specific server.
This is configured both in the `yaml` file and with the first lines
in the `smk` file:

```python
SERVER = 'ihep'
DATASET= 'brem_track_2'
SSHOPT = '-o StrictHostKeyChecking=no -o BatchMode=yes -o PasswordAuthentication=no -o PubkeyAuthentication=yes'
```

and can be changed

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
ssh -L 3100:localhost:3100 campoverde@lxlogin002.ihep.ac.cn
```

Then open your browser at `http://localhost:3100`.

> 1300 is the port Caddy listens on on the server 3100 is the local port on your laptop (chosen to avoid conflicts — you can use any free port).

---

## Making the config file in the server

In the browser, after logging in, create a token and use it to generate a config with:

```bash
flowo --generate-config --host http://localhost:3100 --working-path /publicfs/ucas/user/campoverde --token flw_GlYaCLMz1flA_x8N90w5DOmg1a-gRQ9I6zfR3oO2Tas
```

in the server (e.g. lxplus)

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
    │  port 3100 (laptop) → port 3100 (server, SSH tunnel)
    ▼
Caddy  (inside flowo_app, port 3100)
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

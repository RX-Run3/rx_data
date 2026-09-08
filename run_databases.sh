#!/usr/bin/env bash

set -e

hqm build-database -t rkst_mm_os -c bdkstkpipsi2mm
hqm build-database -t rkst_ee_os -c bdkstkpipsi2ee

hqm build-database -t rkst_mm_os -c bdkstkpijpsimm
hqm build-database -t rkst_ee_os -c bdkstkpijpsiee

hqm build-database -t rkst_mm_os -c data_24
hqm build-database -t rkst_ee_os -c data_24

hqm build-database -t rk_mm_os   -c bpkpjpsimm
hqm build-database -t rk_ee_os   -c bpkpjpsiee

hqm build-database -t rk_mm_os   -c bpkppsi2mm
hqm build-database -t rk_ee_os   -c bpkppsi2ee

hqm build-database -t rk_mm_os   -c data_24
hqm build-database -t rk_ee_os   -c data_24

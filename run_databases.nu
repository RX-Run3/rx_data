#!/usr/bin/env nu

[
    {t: "rkst_mm_os", c: "bdkstkpipsi2mm"},
    {t: "rkst_ee_os", c: "bdkstkpipsi2ee"},
    {t: "rkst_mm_os", c: "bdkstkpijpsimm"},
    {t: "rkst_ee_os", c: "bdkstkpijpsiee"},
    {t: "rkst_mm_os", c: "data_24"},
    {t: "rkst_ee_os", c: "data_24"},
    {t: "rk_mm_os",   c: "bpkpjpsimm"},
    {t: "rk_ee_os",   c: "bpkpjpsiee"},
    {t: "rk_mm_os",   c: "bpkppsi2mm"},
    {t: "rk_ee_os",   c: "bpkppsi2ee"},
    {t: "rk_mm_os",   c: "data_24"},
    {t: "rk_ee_os",   c: "data_24"},
] | each {|row| hqm build-database -t $row.t -c $row.c }

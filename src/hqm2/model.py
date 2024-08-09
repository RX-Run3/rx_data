import zfit

#--------------------------------------------------------
def get_3cb(pref, obs):
    mu  = zfit.param.Parameter(f'mu_{pref}', 5500, 5000, 6000)

    sg1 = zfit.param.Parameter(f'sg1_{pref}',  10,  0.1, 400)
    sg2 = zfit.param.Parameter(f'sg2_{pref}',  40,  0.1, 400)
    sg3 = zfit.param.Parameter(f'sg3_{pref}',  40,  0.1, 400)
    
    al  = zfit.param.Parameter(f'al_{pref}',-1.5,  -10,    0)
    ac  = zfit.param.Parameter(f'ac_{pref}', 1.5,    0,   10)
    ar  = zfit.param.Parameter(f'ar_{pref}', 1.5,    0,   10)

    nl  = zfit.param.Parameter(f'nl_{pref}',   1, 1e-3,  110)
    nr  = zfit.param.Parameter(f'nr_{pref}',   1, 1e-3,  110)
    nc  = zfit.param.Parameter(f'nc_{pref}',   1, 1e-3,  110)
    
    cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, obs, name='CB1')
    cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, obs, name='CB2')
    cb3 = zfit.pdf.CrystalBall(mu, sg3, ac, nc, obs, name='CB3')
    
    frc_1 = zfit.param.Parameter(f'frc_1_{pref}', 0.5, 0, 1) 
    frc_2 = zfit.param.Parameter(f'frc_2_{pref}', 0.5, 0, 1) 

    pdf   = zfit.pdf.SumPDF([cb1, cb2, cb3], fracs=[frc_1, frc_2])
    
    return pdf
#--------------------------------------------------------
def get_2cb(pref, obs):
    mu  = zfit.param.Parameter(f'mu_{pref}', 5500, 5000, 6000)

    sg1 = zfit.param.Parameter(f'sg1_{pref}',  10,  0.1, 400)
    sg2 = zfit.param.Parameter(f'sg2_{pref}',  40,  0.1, 400)
    
    al  = zfit.param.Parameter(f'al_{pref}',-1.5,  -10,    0)
    ar  = zfit.param.Parameter(f'ar_{pref}', 1.5,    0,   10)

    nl  = zfit.param.Parameter(f'nl_{pref}',   1, 1e-3,  110)
    nr  = zfit.param.Parameter(f'nr_{pref}',   1, 1e-3,  110)
    
    cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, obs, name='CB1')
    cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, obs, name='CB2')
    
    frc_1 = zfit.param.Parameter(f'frc_1_{pref}', 0.5, 0, 1) 
    frc_2 = zfit.param.Parameter(f'frc_2_{pref}', 0.5, 0, 1) 

    pdf   = zfit.pdf.SumPDF([cb1, cb2], fracs=[frc_1, frc_2])
    
    return pdf
#--------------------------------------------------------
def get_dscb(pref, obs):
    al  = zfit.param.Parameter(f'al_{pref}', 1.5, 1e-3,   10)
    ar  = zfit.param.Parameter(f'ar_{pref}', 1.5, 1e-3,   10)
    sg  = zfit.param.Parameter(f'sg_{pref}',  40,  0.1,  100)
    nl  = zfit.param.Parameter(f'nl_{pref}',   1, 1e-3,  110)
    nr  = zfit.param.Parameter(f'nr_{pref}',   1, 1e-3,  110)
    mu  = zfit.param.Parameter(f'mu_{pref}', 5500, 5000, 6000)
    pdf = zfit.pdf.DoubleCB(mu=mu, sigma=sg, alphal=al, nl=nl, alphar=ar, nr=nr, obs=obs)

    return pdf
#--------------------------------------------------------


import parobject as php
import numpy as nm


def base_smica(root_grp,hascl,lmin,lmax,nT,nP,wq,rqhat,Acmb,rq0=None,bins=None):
  if bins==None:
    nbins = 0
  else:
    bins.shape=(-1,(lmax+1-lmin)*nm.sum(hascl))
    nbins = bins.shape[0]
  lkl_grp = php.add_lkl_generic(root_grp,"smica",1,hascl,lmax,lmin,nbins = nbins,bins = bins.flat[:])

  lkl_grp.attrs["m_channel_T"] = nT
  lkl_grp.attrs["m_channel_P"] = nP
  lkl_grp.create_dataset('wq', data=wq)
  lkl_grp.create_dataset("Rq_hat",data=rqhat.flat[:])
     
  if rq0 !=None:
    lkl_grp.create_dataset("Rq_0",data=rq0.flat[:])
  
  lkl_grp.attrs["A_cmb"] = Acmb
  lkl_grp.attrs["n_component"] = 1  
  
  return lkl_grp

def add_component(lkl_grp,typ,position=-1):
  nc = lkl_grp.attrs["n_component"]
  if position ==-1:
    position = nc
  assert position <=nc
  for ic in range(nc,position,-1):
    lkl_grp.copy("component_%d"%ic-1,"component_%d"%ic)
    del lkl_grp["component_%d"%ic]
  agrp = lkl_grp.create_group("component_%d"%(position))  
  agrp.attrs["component_type"]=typ
  lkl_grp.attrs["n_component"] = nc+1
  return agrp

def add_cst_component(lkl_grp,rq0,position=-1):
  agrp = add_component(lkl_grp,"cst",position)
  agrp.create_dataset("Rq_0",data=rq0.flat[:])
  return agrp
def add_cst_component_pars(lkl_grp,pars):
  rq0 = php.read_somearray(pars.rq0)
  return add_cst_component(lkl_grp,rq0)

def add_gcal_component(lkl_grp,typ,ngcal,gcaltpl,binned=False,names=[],position=-1):
  if typ.lower() == "log":
    typ = "gcal_log"
  else:
    typ = "gcal_lin"
  agrp = add_component(lkl_grp,typ,position)
  agrp.attrs["ngcal"] = nm.array(ngcal,dtype=nm.int) 
  agrp.create_dataset("gcaltpl",data=nm.array(gcaltpl,dtype=nm.double).flat[:])
  if binned:
    agrp.attrs["binned"]=1
  else:
    agrp.attrs["binned"]=0

  if names:
    setnames(agrp,names)
  return agrp

def read_gcal_data(pars,lkl_grp):
  return read_gcal_data_(pars.str_array.datacal,pars.float_array.ngcal,pars.int_array(default=[-1]).lmax_tpl,lkl_grp)

def read_gcal_data_(datacal,ngcal,lmax_tpl,lkl_grp):
  # returns the dtemplate data
  lmin = lkl_grp.attrs["lmin"]
  lmax = lkl_grp.attrs["lmax"]
  if len(datacal) == 1:
    dat = nm.loadtxt(datacal[0]).flat[:]
  else:
    assert len(datacal)==len(ngcal)
    dat = ()
    i=0
    if len(lmax_tpl)==1:
      lmax_tpl = list(lmax_tpl)*len(ngcal)
    assert len(ngcal)==len(lmax_tpl)
    for ff,lm in zip(datacal,lmax_tpl):
      assert lm>=lmax
      idat = nm.loadtxt(ff).flat[:]
      if lm!=-1:
        idat.shape = (-1,lm+1)
        idat = idat[:ngcal[i],lmin:lmax+1]
        idat = idat.flat[:]
      dat = nm.concatenate((dat,idat))  
  return dat

def add_gcal_component_pars(lkl_grp,pars):
  typ = pars.str.type
  ngcal = pars.float_array.ngcal  
  gcaltpl = read_gcal_data(pars,lkl_grp)
  names = []
  if "name" in pars:
    names = pars.str_array.name
    assert len(names) == nm.sum(ngcal)
  binned = bool(pars.int(default=0).binned!=0)
  return add_gcal_component(lkl_grp,typ,ngcal,galtpl,binned,names)

def setnames(agrp,names):
  agrp.attrs["names"] = php.pack256(*names) 
  
def add_egfs_component(lkl_grp,vpars,defaults,values,lmin,lmax,template_names,tpls,cib_decor_clustering,position=-1):
  import egfs
  agrp = add_component(lkl_grp,"egfs",position)
  egfs.add_xxx(agrp,vpars,defaults,values,lmin,lmax,template_names,tpls,cib_decor_clustering)
  agrp.attrs["A_cmb"] = lkl_grp.attrs["A_cmb"]
  return agrp

def add_from_pars(lkl_grp,parfile):
  import miniparse
  pars = miniparse.miniparse(parfile)
  typ = pars.str.ctype
  return globals()["add_%s_component_pars"](lkl_grp,pars)

def add_parametric_component(lkl_grp,name,dets,vpars,lmin,lmax,defaults={}):
  import parametric

  # initialize parameters
  pm = getattr(parametric,name)(dets,vpars,lmin,lmax,defaults)
  #filter them out
  npars = [vp for vp in vpars if pm.has_parameter(vp)]
  agrp = add_component(lkl_grp,name)
  agrp.attrs["ndim"] = len(vpars)
  agrp.attrs["keys"] = php.pack256(*npars)
  
  agrp.attrs["ndef"] = len(defaults)
  defkey = defaults.keys()
  defval = [defaults[k] for k in defkey]
  agrp.attrs["defaults"] = php.pack256(*defkey)
  agrp.attrs["values"] = php.pack256(*defval)

  agrp.attrs["lmin"] = lmin
  agrp.attrs["lmax"] = lmax

  agrp.attrs["freq"] = [int(d) for d in dets]
  agrp.attrs["A_cmb"] = lkl_grp.attrs["A_cmb"]
  return agrp

  
def set_criterion(lkl_grp,typ,**extra):
  if typ.lower()=="classic":
    lkl_grp.attrs["criterion"]="classic"
    return
  if typ.lower()=="eig":
    lkl_grp.attrs["criterion"]="eig"
    if "eig_norm" in extra:
      lkl_grp["criterion_eig_norm"]=extra["eig_nrm"]
    else:
      import numpy.linalg as la
      import numpy as nm
      rqh = lkl_grp["Rq_hat"][:]
      nq = len(lkl_grp["wq"][:])
      m = lkl_grp.attrs["m_channel_T"] + lkl_grp.attrs["m_channel_P"] 
      rqh.shape=(nq,m,m)
      nrm = nm.array([.5*(nm.log(nm.abs(la.det(rqh[i])))+m) for i in range(nq)])
      lkl_grp["criterion_eig_norm"] = nrm
    return
  if typ.lower()=="quadratic":
    lkl_grp.attrs["criterion"]="quadratic"
    lkl_grp.create_dataset("criterion_quadratic_mat",data=extra["quadratic_mat"])
    return


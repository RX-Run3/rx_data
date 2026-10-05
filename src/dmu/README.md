[TOC]

# D(ata) M(anipulation) U(tilities)

These are tools that can be used for different data analysis tasks.

# Networking 

## EOS

In order to interact with EOS one can use `xrootdpyfs`. However, this project
provides a small wrapper to make its usage easier.

### Globbing

For that do:

```python
from dmu import XRootEOS

host = "root://eoslhcb.cern.ch"
path = "/eos/lhcb/wg/dpa/wp2/ci/22781/btoxll_mva_2024_nopid"

obj   = XRootEOS(host = host)
paths = obj.glob(dir_path = path, ext = 'root')
```

## Transferring data through SSH

A small wrapper to rsync is show below:

````python
from dmu import FCopy

fcp = FCopy(source='userA@serverA', target='userB@serverB')
fcp.copy(source='/home/userA/path/file1', target='/home/userB/path/file1') 
````

This will copy a file given the paths, from one server to another.

- The connection must be possible without passwords, i.e. with key pairs
- By default source and target in initializer are empty strings and the
files are assumed to be local

One instance of `FCopy` is meant to be used to transfer multiple files.

## Publishing packages

From the root directory of a version controlled project (i.e. a directory with the `.git` subdirectory)
using a `pyproject.toml` file, run:

```bash
publish
```

such that:

1. The `pyproject.toml` file is checked and the version of the project is extracted.
1. If a tag named as the version exists move to the steps below.
1. If it does not, make a new tag with the name as the version

Then, for each remote it pushes the tags and the commits.

*Why?*

1. Tags should be named as the project's version
1. As soon as a new version is created, that version needs to be tagged.
1. In GitHub, one can configure actions to publish projects when the commits are tagged.

# Generic

This section describes generic tools that could not be put in a specific category, but tend to be useful.

## Environment

To temporarily set an environment use:

```python
from dmu.generic import utilities as gut

with gut.environment(mapping = {'VAR' : '1234', 'VOR' : 'abcd'}):
    var = os.environ['VAR']
    vor = os.environ['VOR']
```

## Typing

### Pandas types

The following snippet

```python
from dmu.generic.typing_utilities import numeric_from_series

age = numeric_from_series(row, 'age', int)
```

will extract the value of the `age` column from the `row` series
and will return an `int`. This can also be used with `float` and `bool`
and will allow pyright to run without errors. 

## Naming

### Name cleaning

This is an alternative to projects like `slugify`. The function will
take strings with characters that are not easy to use when naming files and
will clean it up with:

```python

from dmu.generic import naming

value = naming.clean_special_characters(name=name)
```

e.g.:

```
a  b'    ->  'a_b'
a$b'     ->  'a_b'
a > b'   ->  'a_gt_b'
a < b'   ->  'a_lt_b'
a = b'   ->  'a_eq_b'
{a}'     ->  '_a_'
a.b'     ->  'apb'
a && b'  ->  'a_and_b'
a || b'  ->  'a_or_b'
```

## Caching data

In order to reuse data that is hard to calculate one would need:

- Serializable data, i.e. strings, floats, lists, etc
- A way to get a unique identifier of that data, e.g. a hashable object

If both are avalable, one can:

```python
from dmu.generic import cache 

def _get_something() -> float:
    # This loads the data, if found 
    hashable = arg1, arg2

    ret = cache.load_cached(hash_obj=hashable, on_fail=-999)
    if ret != -999:
        return ret
    
    obj = very_expensive_function(arg1, arg2)
    
    # This saves the data
    ret = cache.cache_data(obj, hash_obj=hashable)

    return ret
```

the cached data will go to JSON files in `/tmp/dmu/cache`.

## Caching with a base class

Caching functionalities can be added to a class through a base class as in:

```python
from dmu.workflow.cache    import Cache     as Wcache

class Tester(Wcache):
    '''
    Testing class, produces outputs from simple inputs
    '''
    # -----------------------------------
    def __init__(
            self,
            nval : int):
        '''
        nval, some integer used to produce output data
        '''
        super().__init__(
                out_path='Tester',
                nval    =nval)

        self._nval    = nval
    # -----------------------------------
    def run(self) -> None:
        '''
        Returns a list of 1's
        '''
        # _out_path belongs to the base class
        obj_path = f'{self._out_path}/values.json'

        if self._copy_from_cache():
            log.warning('Output cached, not running')
            return gut.load_json(obj_path)

        log.info('Data not cached, running')
        res = [1] * self._nval

        gut.dump_json(res, obj_path)
        self._cache()

        return res

with Cache.cache_root(path='/some/directory')
    obj = Tester(nval=3)
    ...
```

where the tester class has access to extra functionalities to:

- Cache outputs to a hashed directory
- For the next run, check if the directory exists, if so pick 
the outputs and put them in the output directory
- If not rerun the process

Several hashed directories might exist, like in the diagram:

![](doc/images/cache_hash.png)

**Important**: This class will also use the hash of the module where the `Test`
class is defined. Thus, changes in the code or in the input data, will invalidate the hash.

### Turning caching off

This can be done temporarily with:

```python
with Wcache.turn_off_cache(val=['Tester']):
    obj = Tester(nval=4)
    out = obj.run()
```

for any list of classes that inherit from `Cache` by passing the list of class names.
If `val=None` is passed, ALL the classes caching is turned off.

### Turning off code hashing

If the module where the cached class lives changes, the hash will be invalidated.
This is going to make development slower. To turn off the module hashing do:

```python
class Tester(Wcache):
    '''
    Testing class, produces outputs from simple inputs
    '''
    # -----------------------------------
    def __init__(
            self,
            nval : int):
        '''
        nval, some integer used to produce output data
        '''
        super().__init__(
                out_path='Tester',
                code    ='dummy',  # <--- Add the a dummy value for code argument
                nval    =nval)
        ...
```

## Silencing import messages

To silence messages given by modules not in the user's control do:

```python
import dmu.generic.utilities as gut

with gut.silent_import():
    import tensorflow
```

## Silencing messages going to __stderr__ originating deep from C++ code

This is an issue with frameworks like `Tensorflow`. Some messages are impossible
to kill, which interferes with the debugging process. In order hide selectively
those messages, do:

```python
from dmu.logging import messages as mes 

l_msg = ['ONE', 'TWO']
with mes.filter_stderr(banned_substrings=l_msg):
        os.write(2, b'MSG ONE\n')
        os.write(2, b'MSG TWO\n')
        os.write(2, b'MSG THREE\n')
```

The context manager above will only allow `THREE` into the error stream.

## YAML

### BlockStyleDumper
When dumping data to yaml files do it like:

```python
import dmu.generic.utilities as gut

yaml.dump(data, Dumper=gut.BlockStyleDumper)
```

to make sure the indentation is correct.

### Resolver

When writting configurations the following layout might be needed:

```yaml
input : 
    - my_package
    - path/to/file.yaml

a: some value
b: other value
c: last value 

composite_1: '{a} or  {b}'
composite_2: '{a} and {b}'
composite_3: '{composite_1} and {c}'
```

i.e. for brevity keys could be referenced in latter definitions.
This structure needs to be resolved and this can be done with:

```python
from dmu.yaml.resolver     import Resolver

yrs = Resolver(cfg=cfg)
val = yrs['composite_3']
```

where `cfg` is the dictionary respresenting the configuration.

An `input` key was present. This is a special key that will map to
a data package that might contain another config file that can optionally
be resolved. If `file.yaml` were:

```yaml
x : 1
y : 
    - alpha
    - beta
```

then the config would be equivalent to:

```yaml
x : 1
y : 
    - alpha
    - beta

a: some value
b: other value
c: last value 

composite_1: '{a} or  {b}'
composite_2: '{a} and {b}'
composite_3: '{composite_1} and {c}'
```


## Hashing

### Hashing python objects

The snippet below:

```python
from dmu.generic  import hashing

obj = [1, 'name', [1, 'sub', 'list'], {'x' : 1}]
val = hashing.hash_object(obj)
```

will:

- Make the input object into a JSON string
- Encode it to utf-8
- Make a 64 characters hash out of it

in two lines, thus keeping the user's code clean.
The `obj` can also be an `omegaconf` `DictConfig`

### Hashing files

The following snippet:

```python
from dmu.generic  import hashing

path = '/some/file/path.txt'
val  = hashing.hash_file(path=obj)
```

should provide a hash to a file, given its path.

## Timer

In order to benchmark functions do:

```python
import dmu.generic.utilities as gut

# Needs to be turned on, it's off by default
gut.TIMER_ON=True
@gut.timeit
def fun():
    sleep(3)

fun()
```

## Python to JSON string

The project contains a wrapper to `json.dumps` 
that can deal with `PosixPath` and `DictConfig` in the values.
It can be used as:

```python
from dmu.generic import utilities as gut

string = gut.object_to_string(obj={1,2,3, Path('/x/y/z')})
```

## JSON/YAML/Text dumper and loader

The following lines will dump data (dictionaries, lists, etc) to a JSON/YAML file and load it back:

```python
import dmu.generic.utilities as gut

data = [1,2,3,4]

gut.dump_json(data=data, path='/tmp/list.json')
data = gut.load_json('/tmp/list.json')

# And for plain text
gut.dump_text(lines=data, path='/tmp/file.txt')
```

the first one will dump to either JSON or YAML files, depending on the extension, extensions allowed are:

```
.json
.yaml
.yml
```

and it's meant to allow the user to bypass all the boilerplate and keep their code brief.

## PKL dumper and loader

In the same way one can do:

```python
import dmu.generic.utilities as gut

data = [1,2,3,4]

gut.dump_pickle(data, '/tmp/list.pkl')
data = gut.load_pickle('/tmp/list.pkl')
```

## Load lists from data packages through wildcards

Given a set of JSON or YAML files in a data package, each file storing a list,
one can load these lists as `ListConfig` with:

```python
import dmu.generic.utilities as gut

l_list = gut.load_from_wcard(package='dmu_data', fpath=f'tests/generic/load/*.yaml')
```

## Load files and configurations from data packages

YAML and JSON files can be loaded from data packages with:

```python
import dmu.generic.utilities as gut

data = gut.load_data(package='dmu_data', fpath=f'tests/data.json')
conf = gut.load_conf(package='dmu_data', fpath=f'tests/config.yaml', resolve_paths=True)
```

the first one will return a python dictionary, list, etc. 
The second one will return a `DataConf` object from the `omegaconf` project.

Check [this](https://omegaconf.readthedocs.io/en/2.3_branch/index.html) 
for more information.

The config file can look like:

```yaml
key:
  - value1
  - value2
  - value3
config_1 : path/with_respect_to/data_package/config_1.yaml # can also use yml extension
section:
  config_2 : path/with_respect_to/data_package/config_2.yaml
```

in which case the argument `resolve_paths=True` (default) will make sure
these paths are expanded to the corresponding config.

### Validating config

In order to validate the configuration `settings.yaml` of project `example_name`:

- Create a data package `example_schema` 
- Place inside `settings_config.py` with the proper validation schema.

The validation will run optionally if `settings_config.py` exists.

To force validation, use the following context manager:

```python
import dmu.generic.utilities as gut

with gut.enforce_schema_validation(value=True):
    cfg = gut.load_conf(
        package='example_name',
        fpath  ='configs/settins.yaml')
```

which raises `RunTimeError` if the schema 
(i.e. `example_schema/settings.config.py`) is missing.

# Physics

## Truth matching

In order to compare the truth matching efficiency and distributions after it is performed in several samples, run:

```bash
check_truth -c configuration.yaml
```

where the config file, can look like:

```yaml
# ---------
max_entries : 1000
samples:
  # Below are the samples for which the methods will be compared
  sample_a:
    file_path : /path/to/root/files/*.root
    tree_path : TreeName
    methods :
        #Below we specify the ways truth matching will be carried out
        bkg_cat : B_BKGCAT == 0 || B_BKGCAT == 10 || B_BKGCAT == 50
        true_id : TMath::Abs(B_TRUEID) == 521 && TMath::Abs(Jpsi_TRUEID) == 443 && TMath::Abs(Jpsi_MC_MOTHER_ID) == 521 && TMath::Abs(L1_TRUEID) == 11 && TMath::Abs(L2_TRUEID) == 11 && TMath::Abs(L1_MC_MOTHER_ID) == 443 && TMath::Abs(L2_MC_MOTHER_ID) == 443 && TMath::Abs(H_TRUEID) == 321 && TMath::Abs(H_MC_MOTHER_ID) == 521
    plot:
      # Below are the options used by Plottter1D (see plotting documentation below)
      definitions:
          mass : B_nopv_const_mass_M[0]
      plots:
          mass :
              binning    : [5000, 6000, 40]
              yscale     : 'linear'
              labels     : ['$M_{DTF-noPV}(B^+)$', 'Entries']
              normalized : true
      saving:
        plt_dir : /path/to/directory/with/plots
```

# Math

## PDFs

### Suppressing tensorflow messages from zfit import

If you work with zfit, you will see messages from tensorflow, by importing zfit through:

```python
from dmu.stats import zfit
```

these messages should be hidden. If `ROOT` is installed, the wrapper will import it before
importing tensorflow. That will prevent crashes which usually happen when `tensorflow` 
is imported before `ROOT`.

### Toy models

For quick tests, one can retrieve simple models with :

```python
from dmu.stats  import utilities as sut

# For a Gaussian plus Exponential, extended
pdf = sut.get_model(kind='s+b')

# For a Gaussian signal, non extended
pdf = sut.get_model(kind='signal')
```

### Parameter building

In order to build models one needs parameters. The parameters need to be defined
by an initial value and a range. These values can be stored in a database and
used later to build models. The parameters available can be printed with:

```python
from dmu.stats.parameters  import ParameterLibrary as PL

PL.print_parameters(kind='gauss')
```

for a specific PDF, other PDFs can be seen in the section below. These will be 
used by default to build models and are meant to be reasonable starting points 
for `B` physics analyses.

#### Overriding parameters

This can be done with:

```python
from dmu.stats.parameters  import ParameterLibrary as PL

with PL.values(kind='gauss', parameter='mu', val=5000, low=5280, high=5400):
    model = build_model() # These lines would involve the ModelFactory
                          # which is discussed below
```

#### Configuring yields

Yields can be obtained by doing:

```python
from dmu.stats.parameters  import ParameterLibrary as PL

par = PL.get_yield(name='nCombinatorial')
```

and these can be _injected_ during the model building.

However, there are two cases that might require further flexibility:

- The yield is the product of multiple parameters, e.g a scale and a different yield
- The yield is the product of other model parameters.

To deal with this one can define a schema as below:

```yaml
BuKee:         # Normal parameter
  val : 1
  min : 0
  max : 10
RK:
  val : 1.0
  min : 0.8
  max : 1.2
iCK:            # Constant parameter, fixed at 1.0
  val : 1.0
  min : 1.0
  max : 1.0
BdKstee:               # BdKstee = s_BdKstee * BuKee
  scl : [BuKee]
  val : 0              # These numbers are associated to the scale parameter
  min : 0
  max : 1
BuKstee:               # BuKstee = my_preffix_BuKstee * BuKee
  scl     : [BuKee]
  preffix : my_preffix # In this case the scale will be named my_preffix_BuKee
  val     : 0          # These numbers are associated to the scale parameter
  min     : 0
  max     : 1
BuKmm:         # Not an actual parameter but: BuKmm = iCK * RK * BuKee
  mul : [iCK, RK, BuKee]
```

and this configuration can be loaded into the code, before running the model
building with:

```python
from dmu.stats             import utilities        as gut
from dmu.stats.parameters  import ParameterLibrary as PL

cfg = gut.load_conf(package='dmu_data', fpath='configuration.yaml')

with PL.parameter_schema(cfg=cfg):
    model = build_model()
```

Another configuration could look like:

```yaml
yield:
  val : 1
  min : 0
  max : 10
fraction:
  val : 0.2
  min : 0.0
  max : 1.0 

yield_001:
  mul:
    - yield
    - fraction
yield_002:
  dif:            # Difference
    - yield
    - yield_001 
```

which can be used to reparametrize the yields of two components in a simultaneous fit as
`total` yield and `fraction`.

### Model building

In order to do complex fits, one often needs PDFs with many parameters, which need to be added.
In these PDFs certain parameters (e.g. $\mu$ or $\sigma$) need to be shared. This project provides
`ModelFactory`, which can do this as shown below:

```python
from dmu.stats.model_factory import ModelFactory

l_pdf = ['cbr'] + 2 * ['cbl']
l_shr = ['mu', 'sg']
l_flt = ['mu', 'sg']                    # Will mark these parameters as floating for the fit done afterwards
d_rep = {'mu' : 'scale', 'sg' : 'reso'} # Optional, will reparametrize for scale and resolution
d_fix = {'al_cbl' : 3, 'nr_cbr' : 1}    # Optional, will fix two parameters whose names start with the keys

# If mu and sg are meant to be shared among all the models
# The parameters can be passed here.
# In this case, they are also meant to be floating
mu = zfit.param.Parameter('mu_flt', 5280, 5000, 5500)
sg = zfit.param.Parameter('sg_flt',   80,   20,  100)
l_reuse = [mu, sg]

mod   = ModelFactory(
    preffix = 'pref',   # Preffix for parameter naming
    obs     = Data.obs, 
    l_pdf   = l_pdf, 
    l_shared= l_shr, 
    l_float = l_float,
    l_reuse = l_reuse,  # Optional
    d_rep   = d_rep,    # Optional
    d_fix   = d_fix)    # Optional

pdf   = mod.get_pdf()
```

where the model is a sum of three `CrystallBall` PDFs, one with a right tail and two with a left tail.
The `mu` and `sg` parameters are shared. The elementary components that can be plugged are:

```
exp: Exponential
pol1: Polynomial of degree 1
pol2: Polynomial of degree 2
cbr : CrystallBall with right tail
cbl : CrystallBall with left tail
gauss : Gaussian
dscb : Double sided CrystallBall
```

### Model building with reparametrizations

In order to introduce reparametrizations for the means and the resolutions, such that:

$\mu\to\mu+\Delta\mu$
$\sigma\to\sigma\cdot s_{\sigma}$

where the reparametrized $\mu$ and $\sigma$ are constant, while the scale and resolution is floating, do:

```python
import zfit
from dmu.stats.model_factory import ModelFactory

l_shr = ['mu', 'sg']
l_flt = []
d_rep = {'mu' : 'scale', 'sg' : 'reso'}
obs   = zfit.Space('mass', limits=(5080, 5680))

mod   = ModelFactory(
        preffix = name,
        obs     = obs,
        l_pdf   = l_name,
        d_rep   = d_rep,
        l_shared= l_shr,
        l_float = l_flt)
pdf   = mod.get_pdf()
```

Here, the floating parameters **should not** be the same as the reparametrized ones.

### Overriding parameters

The models above have their parameter ranges chosen for fits to B meson distributions
e.g. the mean of the distributions is around 5GeV. To make these models extensible for other
resonances do:

```python
from dmu.stats.parameters  import ParameterLibrary as PL

# This will override the ranges and starting value
PL.set_values(kind='cbr', parameter='mu', val=3000, low=2500, high=3500)

# This will fix a parameter, the three arguments need to be equal
PL.set_values(kind='cbr', parameter='sg', val=  30, low=  30, high=  30)
```

before using the `ModelFactory` class.
For a summary of all the parameters and values available do:

```python
PL.print_parameters(kind='cbr')
```

### Printing PDFs

One can print a zfit PDF by doing:

```python
from dmu.stats.utilities   import print_pdf

print_pdf(pdf)
```

this should produce an output that will look like:

```
PDF: SumPDF
OBS: <zfit Space obs=('m',), axes=(0,), limits=(array([[-10.]]), array([[10.]])), binned=False>
Name                                                        Value            Low           HighFloating               Constraint
--------------------
fr1                                                     5.000e-01      0.000e+00      1.000e+00    1                     none
fr2                                                     5.000e-01      0.000e+00      1.000e+00    1                     none
mu1                                                     4.000e-01     -5.000e+00      5.000e+00    1                     none
mu2                                                     4.000e-01     -5.000e+00      5.000e+00    1                     none
sg1                                                     1.300e+00      0.000e+00      5.000e+00    1                     none
sg2                                                     1.300e+00      0.000e+00      5.000e+00    1                     none
```


showing basic information on the observable, the parameter ranges and values, whether they are Gaussian constrained and floating or not.
One can add other options too:

```python
from dmu.stats.utilities   import print_pdf

# Constraints, uncorrelated for now
d_const = {'mu1' : [0.0, 0.1], 'sg1' : [1.0, 0.1]}
#-----------------
# simplest printing to screen
print_pdf(pdf)

# Will not show certain parameters
print_pdf(pdf,
          blind   = ['sg.*', 'mu.*'])

# Will add constraints
print_pdf(pdf,
          d_const = d_const,
          blind   = ['sg.*', 'mu.*'])
#-----------------
# Same as above but will dump to a text file instead of screen
#-----------------
print_pdf(pdf,
          txt_path = 'tests/stats/utilities/print_pdf/pdf.txt')

print_pdf(pdf,
          blind    =['sg.*', 'mu.*'],
          txt_path = 'tests/stats/utilities/print_pdf/pdf_blind.txt')

print_pdf(pdf,
          d_const  = d_const,
          txt_path = 'tests/stats/utilities/print_pdf/pdf_const.txt')
```

The blinding of the parameters can also be achieved with a context manager:

```python
from dmu.stats import utilities as sut

pdf   = _get_pdf(kind='composed_nonextended')
regex = r'mu.*'

with sut.blinded_variables(regex_list=[regex]):
    print_pdf(pdf=pdf)
```

### Storing PDF as latex

The file above can be transformed into a `tex` file by running:

```python
from dmu.stats.utilities   import pdf_to_tex

d_par = {
    'ar_dscb_Signal_002_1_reso_flt' : r'$\alpha_{DSCB}^{1}$',
    'ar_dscb_Signal_002_2_reso_flt' : r'$\alpha_{DSCB}^{2}$',
    }

# It will skip fixed parameters by default
pdf_to_tex(in_path='/path/to/pdf.txt', out_dir = '/path/to', d_par=d_par, skip_fixed=True)
```

where `d_par` will rename the `Parameters` column, such that it's in latex.

## Fits

The `Fitter` class is a wrapper to zfit, use to make fitting easier.

### Goodness of fits

Once a fit has been done, one can use `GofCalculator` to get a rough estimate of the fit quality.
This is done by:

- Binning the data and PDF.
- Calculating the reduced $\chi^2$.
- Using the $\chi^2$ and the number of degrees of freedom to get the p-value.

This class is used as shown below:

```python
from dmu.stats.gof_calculator import GofCalculator

nll = _get_nll()
res = Data.minimizer.minimize(nll)

gcl = GofCalculator(nll, ndof=10)
gof = gcl.get_gof(kind='pvalue')
```

where:

- `ndof` Is the number of degrees of freedom used in the reduced $\chi^2$ calculation
It is needed to know how many bins to use to make the histogram. The recommended value is 10.
- `kind` The argument can be `pvalue` or `chi2/ndof`.

### Abstracting measurements

A measurement is represented by the name of the quantity been measured, the value and the error.
This can be representing using the `Measurement` class like:

```python
from dmu.stats import Measurement

# Add multiple measurements
data = {'a' : (1., 1.), 'b' : (2., 1.)}
ms   = Measurement(data=data)

# Retrieve a measurement
val = ms['c']
```

the `Measurement` is frozen and the data contained cannot be modified once the object is created.

### Simplest fit

```python
from dmu.stats.fitter      import Fitter

obj = Fitter(pdf, dat)
res = obj.fit()
```

by default this class runs the error calculation with `minuit_hesse`.
The error calculation can be turned off with:

```python
from dmu.stats.fitter      import Fitter

with Fitter.errors_disabled(value=True):
    obj = Fitter(pdf, dat)
    res = obj.fit()
```

### Customizations
In order to customize the way the fitting is done one would pass a configuration dictionary to the `fit(cfg=config)`
function. This dictionary can be represented in YAML as:

```yaml
minimization:
  mode     : 0    # Default of zfit is 1. 0 does not recalculate Hessian in minimization steps
  gradient : zfit # Seems faster than with iminuit internal gradient calculation
# The strategies below are exclusive, only can should be used at a time
strategy      :
      # This strategy will fit multiple times and retry the fit until either
      # ntries is exhausted or the pvalue is reached.
      retry   :
          ntries        : 4    #Number of tries
          pvalue_thresh : 0.05 #Pvalue threshold, if the fit is better than this, the loop ends
          ignore_status : true #Will pick invalid fits if this is true, otherwise only valid fits will be counted
      # This will fit smaller datasets and get the value of the shape parameters to allow
      # these shapes to float only around this value and within nsigma
      # Fit can be carried out multiple times with larger and larger samples to tighten parameters
      steps   :
          nsteps   : [1e3, 1e4] #Number of entries to use
          nsigma   : [5.0, 2.0] #Number of sigmas for the range of the parameter, for each step
          yields   : ['ny1', 'ny2'] # in the fitting model ny1 and ny2 are the names of yields parameters, all the yield need to go in this list
# The lines below will split the range of the data [0-10] into two subranges, such that the NLL is built
# only in those ranges. The ranges need to be tuples
ranges        :
      - [0, 3]
      - [6, 9]
#The lines below will allow using contraints for each parameter, where the first element is the mean and the second
#the width of a Gaussian constraint. No correlations are implemented, yet.
constraints   :
      mu : [5.0, 1.0]
      sg : [1.0, 0.1]
#After each fit, the parameters spciefied below will be printed, for debugging purposes
print_pars    : ['mu', 'sg']
likelihood :
    nbins : 100 #If specified, will do binned likelihood fit instead of unbinned
```

## Minimizers

These are alternative implementations of the minimizers in zfit meant to be used for special types of fits.

### Anealing minimizer

This minimizer is meant to be used for fits to models with many parameters, where multiple minima are expected in the
likelihood. The minimizer use is illustrated in:

```python
from dmu.stats.minimizers  import AnealingMinimizer

nll       = _get_nll()
minimizer = AnealingMinimizer(ntries=10, pvalue=0.05)
res       = minimizer.minimize(nll)
```

this will:

- Take the `NLL` object.
- Try fitting at most 10 times
- After each fit, calculate the goodness of fit (in this case the p-value)
- Stop when the number of tries has been exhausted or the p-value reached is higher than `0.05`
- If the fit has not succeeded because of convergence, validity or goodness of fit issues,
randomize the parameters and try again.
- If the desired goodness of fit has not been achieved, pick the best result.
- Return the `FitResult` object and set the PDF to the final fit result.

The $\chi^2/Ndof$ can also be used as in:

```python
from dmu.stats.minimizers  import AnealingMinimizer

nll       = _get_nll()
minimizer = AnealingMinimizer(ntries=10, chi2ndof=1.00)
res       = minimizer.minimize(nll)
```

## Fit plotting

The class `ZFitPlotter` can be used to plot fits done with zfit. For a complete set of examples of how to use
this class check the [tests](tests/stats/test_fit_plotter.py). A simple example of its usage is below:

```python
from dmu.stats import ZFitPlotter

obs = zfit.Space('m', limits=(0, 10))

# Create signal PDF
mu  = zfit.Parameter("mu", 5.0,  0, 10)
sg  = zfit.Parameter("sg", 0.5,  0,  5)
sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg)
nsg = zfit.Parameter('nsg', 1000, 0, 10000)
esig= sig.create_extended(nsg, name='gauss')

# Create background PDF
lm  = zfit.Parameter('lm', -0.1, -1, 0)
bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
nbk = zfit.Parameter('nbk', 1000, 0, 10000)
ebkg= bkg.create_extended(nbk, name='expo')

# Add them
pdf = zfit.pdf.SumPDF([ebkg, esig])
sam = pdf.create_sampler()

# Plot them
obj   = ZFitPlotter(data=sam, model=pdf)
d_leg = {'gauss': 'New Gauss'}
obj.plot(nbins=50, d_leg=d_leg, stacked=True, plot_range=(0, 10), ext_text='Extra text here')

#Alternatively one can do:
obj.plot(nbins=50, d_leg=d_leg, stacked=True, ranges=[[0,3], [3,10]])
# For plotting only sidebands, useful if one has a blinded fit

# add a line to pull hist
obj.axs[1].plot([0, 10], [0, 0], linestyle='--', color='black')
```

this class supports:

- Handling title, legend, plots size.
- Adding pulls.
- Stacking and overlaying of PDFs.
- Blinding.

## Fit saving

To save in one go everything regarding your fit do:

```python
from dmu.stats import utilities as sut
from dmu.stats import ZFitPlotter

ptr = ZFitPlotter(data=dat, model=pdf)
ptr.plot()

cfg = {
    'nbins'      : 50, 
    'stacked'    : True, # If False, it would overlay the components
    'plot_range' : [-5, +6], # This is the xaxis range
    'yrange'     : {
        'log'    : [1.0, 1e3], # It will save a log and linear plot in the y axis
        'linear' : [0.0, 1e2]}
}

sut.save_fit(
    data   =data, 
    model  =pdf, 
    res    =fit_result, 
    fit_dir='/some/directory', 
    d_const=constraints,
    plt_cfg=cfg)
```

and the function will save everything that you would normally need from a fit.
If the lines with `ZFitPlotter` were called before `save_fit` the fit plot will also be saved.

### Transforming fit results to DictConfig

The `OmegaConf` library offers `DictConfig` objects, which are easier to handle
when reading nested data. To transform a zfit result object into one of these 
objects do:

```python
from dmu.stats import utilities as sut

# fall_back_error is optional
# if not passed and error is not found
# It will raise KeyError
cres = sut.zres_to_cres(res=res, fall_back_error=-1)
```

and then one would access the information like:

```python
error = cres.mu.error
value = cres.mu.value
```

and these objects can be saved to JSON with:

```python
OmegaConf.save(config=cres, f='results.yaml')
```

## Constraints

One way to introduce constraints in a model could be to modify the likelihood as in:

```python
from dmu.stats.constraint_adder import ConstraintAdder

cad = ConstraintAdder(nll=nll, cns=cns)
nll = cad.get_nll()
```

where `cns` is a `DictConfig` instance where the full configuration
has been specified as in:

```yaml
signal_shape:
  kind        : GaussianConstraint 
  parameters  :
    - mu
    - sg
  observation : 
    - 5080
    - 10
  cov: 
    - [100, 10]
    - [ 10,  4]
yields:
  kind        : PoissonConstraint
  parameters  :
    - nsig 
    - nbkg 
  observation : 
    - 1000 
    - 1000 
```

such that:

- The shape parameters are constrained by a 2D Gaussian, which
is associated to a covariance matrix.
- The yields are constrained by Poisson distributions. No correlation is used.

The parameters in the `parameters` sections must be found in the likelihood, `nll`

### Resampling for toy fits

One should resample the constraints when making toy fits. This is done with:

```python
import zfit
from dmu.stats.constraint_adder import ConstraintAdder

cad = ConstraintAdder(nll=nll, cns=cns)
nll = cad.get_nll()

min = zfit.minimize.Minuit()
for _ in range(ntoys):
    cad.resample()
    data.resample()

    res = minimizer.minimize(nll)
```

### Helpers

To transform dictionaries with the value and error for each variable into
a config object do:

```python
from dmu.stats.constraint_adder import ConstraintAdder

d_cns = {
    'a' : (0., 1.),
    'b' : (5., 2.),
}    

cns = ConstraintAdder.dict_to_cons(d_cns=d_cns, kind='GaussianConstraint')
```

### Constraint getting utility

One can bypass the constraint adder and get zfit constraints
from a python dictionary with:

```python
from dmu.stats.fitter import Fitter

d_const = {'mu' : (10, 1), 'sg' : (1, 0)}
cons    = Fitter.get_gaussian_constraints(obj=pdf, cfg=d_const)
```

to extract the `GaussianConstraints` object associated to the
`pdf`. The PDF can also be a zfit likelihood.

## Placeholders 

### Models

To get toy models do:

```python
from dmu.stats import utilities

suffix= 'test_001' # Optional, if used will name parameters like this

# Kind can be signal for a single gaussian
pdf = sut.get_model(kind='s+b', suffix=suffix)
```

Which will create a simple PDF to do quick tests.
To get data do:

```python
data = pdf.create_sampler(10_000)
```

### Fits

In order to create a _fake_ fit on top of which one could develop other tools, do:

```python
from dmu.stats import utilities

utilities.placeholder_fit(kind='s+b', fit_dir='/some/directory')
```

### Likelihooods

```python
from dmu.stats import utilities as sut

nll = sut.get_nll(kind='s+b')
```

`s+b` will return an extended likelihood   
`signal` will return a non-extended likelihood

## Retrieving information on fits

Once the fit has be done and the results are saved to a given directory one can do:

```python
from dmu.stats.fit_stats    import FitStats

obj =FitStats(fit_dir='/directory/with/fit')
val = obj.get_value(name='var_name', kind='value or error')
```

and the tool will retrieve the value. This is useful when the values are needed elsewhere
in the code, i.e. it would connect the fitting part with other parts.

## Fit results

### Values of parameters

In order to retrieve the value of a fitted parameter 
from a `FitResult` instance do:

```python
from dmu.stats import utilities as sut

val = sut.val_from_zres(res=res, name='mu')
```

## Arrays

### Scaling by non-integer

Given an array representing a distribution, the following lines will increase its size
by `fscale`, where this number is a float, e.g. 3.4.

```python
from dmu.arrays.utilities import repeat_arr

arr_val = repeat_arr(arr_val = arr_inp, ftimes = fscale)
```

in such a way that the output array will be `fscale` larger than the input one, but will keep the same distribution.

## Functions

The project contains the `Function` class that can be used to:

- Store `(x,y)` coordinates.
- Evaluate the function by interpolating
- Storing the function as a JSON file
- Loading the function from the JSON file

It can be used as:

```python
import numpy
from dmu.stats.function    import Function

x    = numpy.linspace(0, 5, num=10)
y    = numpy.sin(x)

path = './function.json'

# By default the interpolation is 'cubic', this uses scipy's interp1d
# refer to that documentation for more information on this.
fun  = Function(x=x, y=y, kind='cubic')
fun.save(path = path)

fun  = Function.load(path)

xval = numpy.lispace(0, 5, num=100)
yval = fun(xval)
```

## Other utilities

These are here to decrease boilerplate code

```python
from dmu.stats import utilities as sut

# Retrieves name of observable from observable
name = sut.name_from_obs(obs=obs)

# Retrieves range of observable from observable
minx, maxx = sut.range_from_obs(obs=obs)

# This is needed because when building a KDE with too little data, that KDE cannot be evaluated
# and when trying it, tensorflow emits an exception.
is_pdf_usable(pdf)
```

# Machine learning

## Classification

To train models to classify data between signal and background, starting from ROOT dataframes do:

```python
from dmu.ml.train_mva      import TrainMva

rdf_sig = _get_rdf(kind='sig')
rdf_bkg = _get_rdf(kind='bkg')
cfg     = _get_config()

obj= TrainMva(sig=rdf_sig, bkg=rdf_bkg, cfg=cfg)
obj.run(
skip_fit=False, # by default it will be false, if true, it will only make plots of features
opt_ntrial=20,  # By default this is zero, if a larger number is chosen, a hyperparameter optimization with optuna will run with this number of trials
load_trained=False, # If true, it will not train the models but will just load them, only makes sense if models already exist. Useful to add postprocessing code, like the diagnostics section.
)
```

where the settings for the training go in a config dictionary, which when written to YAML looks like:

```yaml
dataset:
    # This section is optional. It can be used to redefine
    # columns in different ways for different samples
    #
    # When evaluating the model, the same definitions will be used
    # but they will be taken from the `sig` section.
    samples:
        sig:
            definitions:
                x : v + w
        bkg:
            definitions:
                x : v - w
    # Before training, new features can be defined as below
    define :
        y : v - w
    # If the key is found to be NaN, replace its value with the number provided
    # This will be used in the training.
    # Otherwise the entries with NaNs will be dropped
    nan:
        x : 0
        y : 0
        z : -999
training :
    nfold    : 10
    features : [x, y, z]
    hyper    :
      loss              : log_loss
      n_estimators      : 100
      max_depth         : 3
      learning_rate     : 0.1
      min_samples_split : 2
saving:
    # The model names are model_001.pkl, model_002.pkl, etc, one for each fold
    path : 'tests/ml/train_mva'
plotting:
    roc :
        min : [0.0, 0.0] # Optional, controls where the ROC curve starts and ends
        max : [1.2, 1.2] # By default it does from 0 to 1 in both axes
        # The section below is optional and will annotate the ROC curve with
        # values for the score at different signal efficiencies
        annotate:
          sig_eff : [0.5, 0.6, 0.7, 0.8, 0.9] # Values of signal efficiency at which to show the scores
          form    : '{:.2f}' # Use two decimals for scores
          color   : 'green'  # Color for text and marker
          xoff    : -15      # Offsets in X and Y
          yoff    : -15
          size    :  10      # Size of text
    correlation: # Adds correlation matrix for training datasets
      title      : 'Correlation matrix'
      size       : [10, 10]
      mask_value : 0                # Where correlation is zero, the bin will appear white
    features:
        plots:
          w :
            binning : [-4, 4, 100]
            yscale  : 'linear'
            labels  : ['w', '']
          x :
            binning : [-4, 4, 100]
            yscale  : 'linear'
            labels  : ['x', '']
          y :
            binning : [-4, 4, 100]
            yscale  : 'linear'
            labels  : ['y', '']
          z :
            binning : [-4, 4, 100]
            yscale  : 'linear'
            labels  : ['z', '']
```

the `TrainMva` is just a wrapper to `scikit-learn` that enables cross-validation (and therefore that explains the `nfolds` setting).

#### Outputs

The trainer will produce in the output:

- Models in form of `pkl` files
- Plots of the features
- For each fold:
1. Covariance plot
1. ROC curve plot
1. Feature importance table in latex
1. JSON file with data to build the ROC curve
- For the full dataset it will provide the ROC curve, scores distribution and JSON file with `x`, `y` coordinates for ROC curve.
- Latex table with hyperparameters and NaN replacements.

### Caveats

When training on real data, several things might go wrong and the code will try to deal with them in the following ways:

- **Repeated entries**: Entire rows with features might appear multiple times. When doing cross-validation, this might mean that two identical entries
will end up in different folds. The tool checks for wether a model is evaluated for an entry that was used for training and raise an exception. Thus, repeated
entries will be removed before training.

- **NaNs**: Entries with NaNs will break the training with the scikit `GradientBoostClassifier` base class. Thus, we:
    - Can use the `nan` section shown above to replace `NaN` values with something else
    - For whatever remains we remove the entries from the training.

## Application

Given the models already trained, one can use them with:

```python
from dmu.ml.cv_predict     import CVPredict

#Build predictor with list of models and ROOT dataframe with data
cvp     = CVPredict(models=l_model, rdf=rdf)

#This will return an array of probabilibies
arr_prb = cvp.predict()
```

If the entries in the input dataframe were used for the training of some of the models, the model that was not used
will be _automatically_ picked for the prediction of a specific sample.

The picking process happens through the comparison of hashes between the samples in `rdf` and the training samples.
The hashes of the training samples are stored in the pickled model itself; which therefore is a reimplementation of
`GradientBoostClassifier`, here called `CVClassifier`.

If a sample exists, that was used in the training of _every_ model, no model can be chosen for the prediction and a
`CVSameData` exception will be risen.

During training, the configuration will be stored in the model. Therefore, variable definitions can be picked up for evaluation
from that configuration and the user does not need to define extra columns.

### Further optimization

If not all the entries of the ROOT dataframe are needed for the prediction (e.g. some entries won't be used anyway) define
a column as:

```python
rdf = rdf.Define('skip_mva_prediction', 'mass < 3000')
```

and the predictor will assign scores of `-1` to all the entries with `mass < 3000`.
This should speed up the prediction and reduce resource consumption.

### Caveats

When evaluating the model with real data, problems might occur, we deal with them as follows:

- **Repeated entries**: When there are repeated features in the dataset to be evaluated we assign the same probabilities, no filtering is used.
- **NaNs**: Entries with NaNs will break the evaluation. These entries will be:
    - Replaced by other values before evaluation IF a replacement was specified during training. The training configuration will be stored in the model
    and can be accessed through:
    ```python
    model.cfg
    ```
    - For whatever features that are still NaN, they will be _patched_  with zeros when evaluated. However, the returned probabilities will be
saved as -1. I.e. entries with NaNs will have probabilities of -1.

## Diagnostics

To run diagnostics on the trained model do:

```python
from dmu.ml.cv_diagnostics import CVDiagnostics

# Where l_model is the list of models and cfg is a dictionary with the config
cvd = CVDiagnostics(models=l_model, rdf=rdf, cfg=cfg)
cvd.run()
```

the configuration can be loaded from a YAML file and would look like:

```yaml
# Directory where plots will go
output         : /tmp/tests/dmu/ml/cv_diagnostics/overlay
  # Optional, will assume that the target is already in the input dataframe
  # and will use it, instead of evaluating models
score_from_rdf : mva
correlations:
  # Variables with respect to which the correlations with the features will be measured
  target :
    name : mass
    overlay :
      # These are the working points at which the "mass" variable will be plotted
      # If there is a correlation the shape should change
      wp :
        - 0.2
        - 0.5
        - 0.7
        - 0.9
      general:
        size : [20, 10]
      saving:
        plt_dir : /tmp/tests/dmu/ml/cv_diagnostics/from_rdf
      plots:
        z :
          binning    : [1000, 4000, 30]
          yscale     : 'linear'
          labels     : ['mass', 'Entries']
          normalized : true
  methods:
    - Pearson
    - Kendall-$\tau$
  figure:
    title: Scores from file
    size : [10, 8]
    xlabelsize: 18 # Constrols size of x axis labels. By default 30
    rotate    : 60 # Will rotate xlabels by 60 degrees
```

## Comparing classifiers

### Simple approach
To do that run:

```bash
compare_classifiers -c /path/to/config.yaml
```

where the config looks like:

```yaml
out_dir : /path/to/plots
classifiers:
  label for model 1 : /path/to/directory/with/model1
  label for model 2 : /path/to/directory/with/model2
```

However this will only compare the classifiers ROC curves with respect to the
samples that were used to train them.

### With custom samples

However the models' peformances can also be compared by _plugging_ any
signal and backgroud proxy for any model, like:

```python
import matplotlib.pyplot as plt
from dmu.ml.cv_performance import CVPerformance

cvp = CVPerformance()
cvp.plot_roc(
        sig  =rdf_sig_1, bkg=rdf_bkg_1,
        model=l_model_1, name='def', color='red')
cvp.plot_roc(
        sig  =rdf_sig_1, bkg=rdf_bkg_2,
        model=l_model_2, name='alt', color='blue')

plt.legend()
plt.grid()
plt.show()
```

This should show an overlay of different ROC curves made for a specific combination
of signal and background proxies with a given model.

# Dask dataframes

In order to process large ammounts of data a `Dask` dataframe is more suitable.
A set of `ROOT` files can be loaded into one of these with:


```python
from dmu.rfile.ddfgetter   import DDFGetter

# Can also pass directly the configuration dictionary with the `cfg` argument
# If no columns argument is passed, will take all the columns

ddfg = DDFGetter(config_path='config.yaml', columns=['a', 'b'])
ddf  = ddfg.get_dataframe()

# This will provide the pandas dataframe
df   = ddf.compute()
...
```
where `config.yaml` would look like:

```yaml
tree   : tree_name
primary_keys:
  - index
files :
  - file_001.root
  - file_002.root
  - file_003.root
samples:
  - /tmp/tests/dmu/rfile/main
  - /tmp/tests/dmu/rfile/frnd
```

# Pandas dataframes

## Utilities

These are thin layers of code that take pandas dataframes and carry out specific tasks

### Colorize dataframes

In order to add colors to certain cells in a dataframe with integer values do:

```python
from colorama       import Fore
from dmu.pdataframe import utilities as put

colors = {1 : Fore.RED, 2 : Fore.BLUE}
df     = df.apply(put.colorize_row, args=(colors,), axis=1)

print(df.to_markdown())
```

Which will print all cells with 1's as red and the ones with 2's as blue.

### NaN filter

The following snippet will remove NaNs from the dataframe
if up to 2% of the rows have NaNs. Beyond that, an exception will be risen.

```python
import dmu.pdataframe.utilities as put

# Default is 0.02
df = put.dropna(df, nan_frac=0.02)
```

The usecase is cleaning up automatically, data that is not expected to be perfect.

### Dataframe to latex

One can save a dataframe to latex with:

```python
import pandas as pnd
import dmu.pdataframe.utilities as put

d_data = {}
d_data['a'] = [1,2,3]
d_data['b'] = [4,5,6]
df = pnd.DataFrame(d_data)

d_format = {
        'a' : '{:.0f}',
        'b' : '{:.3f}'}

df = _get_df()
put.df_to_tex(df,
        './table.tex',
        d_format = d_format,
        caption  = 'some caption')
```

### Dataframe to and from YAML

This extends the existing JSON functionality

```python
import dmu.pdataframe.utilities as put

df_1 = _get_df()
put.to_yaml(df_1, yml_path)
df_2 = put.from_yaml(yml_path)
```

and is meant to be less verbose than doing it through the YAML module.

### Dataframe to markdown

```python
import dmu.pdataframe.utilities as put

df = _get_df()
put.to_markdown(df, '/path/to/simple.md')
```

# Rdataframes

These are utility functions meant to be used with ROOT dataframes.

## Cutflows from RDataFrames

When using the `Filter` method on a ROOT dataframe, one can:

```python
rep = rdf.Report()
rep.Print()
```

however this `rep` object is not python friendly, despite it is basically a table that can be
put in pandas dataframe. Precisely this can be done with:

```python
from dmu.rdataframe import utilities as ut

df = ut.rdf_report_to_df(rep)
```

## Adding a column from a numpy array

### With numba

For this do:

```python
import dmu.rdataframe.utilities as ut

arr_val = numpy.array([10, 20, 30])
rdf     = ut.add_column_with_numba(rdf, arr_val, 'values', identifier='some_name')
```

where the identifier needs to be unique, every time the function is called.
This is the case, because the addition is done internally by declaring a numba function whose name
cannot be repeated as mentioned
[here](https://root-forum.cern.ch/t/ways-to-work-around-the-redefinition-of-compiled-functions-in-one-single-notebook-session/41442/1)

### With awkward

For this do:

```python
import dmu.rdataframe.utilities as ut

arr_val = numpy.array([10, 20, 30])
rdf     = ut.add_column(rdf, arr_val, 'values')
```

the `add_column` function will check for:

1. Presence of a column with the same name
2. Same size for array and existing dataframe

and return a dataframe with the added column

## Attaching attributes

**Use case** When performing operations in dataframes, like `Filter`, `Range` etc; a new instance of the dataframe
will be created. One might want to attach attributes to the dataframe, like the name of the file or the tree, etc.
Those attributes will thus be dropped. In order to deal with this one can do:

```python
from dmu.rdataframe.atr_mgr import AtrMgr
# Pick up the attributes
obj = AtrMgr(rdf)

# Do things to dataframe
rdf = rdf.Filter(x, y)
rdf = rdf.Define('a', 'b')

# Put back the attributes
rdf = obj.add_atr(rdf)
```

The attributes can also be saved to JSON with:

```python
obj = AtrMgr(rdf)
...
obj.to_json('/path/to/file.json')
```

## Filtering for a random number of entries

The built in method `Range` only can be used to select ranges. Use

```python
import dmu.rdataframe.utilities as ut

rdf = ut.random_filter(rdf, entries=val)
```

to select **approximately** a random number `entries` of entries from the dataframe.

# Logging

The `LogStore` class is an interface to the `logging` module. It is aimed at making it easier to include
a good enough logging tool. It can be used as:

```python
from dmu.logging.log_store import LogStore

LogStore.backend = 'logging' # This line is optional, the default backend is logging, but logzero is also supported
log = LogStore.add_logger('msg')
LogStore.set_level('msg', 5)

log.verbose('verbose')  # level 5
log.debug('debug')      # level 10
log.info('info')        # level 20
log.warning('warning')  # level 30
log.error('error')      # level 40
log.critical('critical')# level 50
```

In order to get a specific logger do:

```python
logger = LogStore.get_logger(name='my_logger_name')
```

In order to get the logging level fromt the logger do:

```python
level = log.getEffectiveLevel()
```

And a context manager is available, which can be used with:

```python
    with LogStore.level('logger_name', 10):
        log.debug('Debug message')
```

# Plotting from ROOT dataframes

## 1D plots

Given a set of ROOT dataframes and a configuration dictionary, one can plot distributions with:

```python
from dmu.plotting.plotter_1d import Plotter1D as Plotter

ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
ptr.run()
```

where the config dictionary `cfg_dat` in YAML would look like:

```yaml
general:
    # This will set the figure size
    size : [20, 10]
selection:
    #Will do at most 50K random entries. Will only happen if the dataset has more than 50K entries
    max_ran_entries : 50000
    cuts:
    #Will only use entries with z > 0
      z : 'z > 0'
saving:
    #Will save lots to this directory
    plt_dir : tests/plotting/high_stat
definitions:
    #Will define extra variables
    z : 'x + y'
#Settings to make histograms for differen variables
plots:
    x :
        binning    : [0.98, 0.98, 40] # Here bounds agree => tool will calculate bounds making sure that they are the 2% and 98% quantile
        yscale     : linear # Optional, if not passed, will do linear, can be log
        labels     : ['x', 'Entries'] # Labels are optional, will use varname and Entries as labels if not present
        title      : some title can be added for different variable plots
        name       : plot_of_x # This will ensure that one gets plot_of_x.png as a result, if missing x.png would be saved
        weights    : my_weights # Optional, this is the column in the dataframe with the weights
        # Can add styling to specific plots, this should be the argument of
        # hist.plot(...)
        styling :
            # This section will update the styling of each category
            # The categories (class A, etc) are the keys of the dictionary of dataframes
            class A:
                # These are the arguments of plt.hist(...)
                histtype : fill 
                color    : gray
                alpha    : 0.3
            class B:
                color    : red 
                histtype : step
                linestyle: '-'  # Linestyle is by default 'none', 
                                # needs to be overriden to see _steps_
        # This will add vertical lines to plots, the arguments are the same
        # as the ones passed to axvline
        vline   :
          x     : 0
          label : label
          ls    : --
          c     : blue
          lw    : 1
    y :
        binning    : [-5.0, 8.0, 40]
        yscale     : 'linear'
        labels     : ['y', 'Entries']
    z :
        binning    : [-5.0, 8.0, 40]
        yscale     : 'linear'
        labels     : ['x + y', 'Entries']
        normalized : true #This should normalize to the area
# Some vertical dashed lines are drawn by default
# If you see them, you can turn them off with this
style:
  skip_lines : true
  # This can pass arguments to legend making function `plt.legend()` in matplotlib
  legend:
    # The line below would place the legend outside the figure to avoid ovelaps with the histogram
    bbox_to_anchor : [1.2, 1]
```

it's up to the user to build this dictionary and load it.
this can also be a `DictConfig` from the `OmegaConf` project.

### Pluggins

Extra functionality can be `plugged` into the code by using the pluggins section like:

#### FWHM
```yaml
plugin:
  fwhm:
    # Can control each variable fit separately
    x :
      plot   : true
      obs    : [-2, 4]
      plot   : true
      format : FWHM={:.3f}
      add_std: True
    y :
      plot   : true
      obs    : [-4, 8]
      plot   : true
      format : FWHM={:.3f}
      add_std: True
```

where the section will

- Use a KDE to fit the distribution and plot it on top of the histogram
- Add the value of the FullWidth at Half Maximum in the title, for each distribution with a specific formatting.

#### stats

```yaml
plugin:
  stats:
    x :
      mean : $\mu$={:.2f}
      rms  : $\sigma$={:.2f}
      sum  : $\Sigma$={:.0f}
```

Can be used to print statistics, mean, rms and weighted sum of entries for each distribution.
The statistics, reffer to the data **only inside** the plotting range.

#### Pulls

If a given variable is a pull, one can add:

- Fitted Gaussian
- Fitter parameters
- Lines representing the mean and width

on the plot with:

```yaml
plugin:
  pulls:
    x_pul : {}
```

assuming that the variable holding the pulls is `x_pul`.
The pulls will be drawn from -4 to +4. No configuration
is available at the moment.

#### Errors and Uncertainties

If the variable is meant to be plotted as an error or uncertainty
this pluggin will:

- Add a median line
- Add a label with the median value

The config section is:

```yaml
plugin:
  errors:
    x_err : # This is the variable's name, meant to be treated as an error
      format : '{:.2f}' # The error will be show in the label with this formatting
      symbol : '\delta(x)' # This will switch the epsilon to delta in the line's
                           # legend. DO NOT use dollar signs
```

## 2D plots

For the 2D case it would look like:

```python
from dmu.plotting.plotter_2d import Plotter2D as Plotter

ptr=Plotter(rdf=rdf, cfg=cfg_dat)
ptr.run()
```

where one would introduce only one dataframe instead of a dictionary, given that overlaying 2D plots is not possible.
The config would look like:

```yaml
saving:
    plt_dir : tests/plotting/2d
selection:
  cuts:
    xlow : x > -1.5
general:
    size : [20, 10]
plots_2d:
    # Column x and y
    # Name of column where weights are, null for not weights
    # Name of output plot, e.g. xy_x.png
    # Book signaling to use log scale for z axis
    - [x, y, weights, 'xy_w', false]
    - [x, y,    null, 'xy_r', false]
    - [x, y,    null, 'xy_l',  true]
axes:
    x :
        binning : [-5.0, 8.0, 40]
        label   : 'x'
    y :
        binning : [-5.0, 8.0, 40]
        label   : 'y'
```

# Other plots

## Matrices

This can be done with `MatrixPlotter`, whose usage is illustrated below:

```python
import numpy
import matplotlib.pyplot as plt

from dmu.plotting.matrix import MatrixPlotter

cfg = {
        'labels'     : ['x', 'y', 'z'], # Used to label the matrix axes
        'title'      : 'Some title',    # Optional, title of plot
        'label_angle': 45,              # Labels will be rotated by 45 degrees
        'upper'      : True,            # Useful in case this is a symmetric matrix
        'zrange'     : [0, 10],         # Controls the z axis range
        'size'       : [7, 7],          # Plot size
        'format'     : '{:.3f}',        # Optional, if used will add numerical values to the contents, otherwise a color bar is used
        'fontsize'   : 12,              # Font size associated to `format`
        'mask_value' : 0,               # These values will appear white in the plot
        }

mat = [
        [1, 2, 3],
        [2, 0, 4],
        [3, 4, numpy.nan]
        ]

mat = numpy.array(mat)

obj = MatrixPlotter(mat=mat, cfg=cfg)
obj.plot()
plt.show()
```

# Manipulating ROOT files

## Getting trees from file

The lines below will return a dictionary with trees from the handle to a ROOT file:

```python
import dmu.rfile.utilities   as rfut

ifile  = TFile("/path/to/root/file.root")

d_tree = rfut.get_trees_from_file(ifile)
```

## Printing contents

The following lines will create a `file.txt` with the contents of `file.root`, the text file will be in the same location as the
ROOT file.

```python
from dmu.rfile.rfprinter import RFPrinter

obj = RFPrinter(path='/path/to/file.root')
obj.save()
```

## Printing from the command line

This is mostly needed from the command line and can be done with:

```bash
print_trees -p /path/to/file.root
```

which would produce a `/pat/to/file.txt` file with the contents, which would look like:

```
Directory/Treename
    B_CHI2                        Double_t
    B_CHI2DOF                     Double_t
    B_DIRA_OWNPV                  Float_t
    B_ENDVERTEX_CHI2              Double_t
    B_ENDVERTEX_CHI2DOF           Double_t
```

## Comparing ROOT files

Given two ROOT files the command below:

```bash
compare_root_files -f file_1.root file_2.root
```

will check if:

1. The files have the same trees. If not it will print which files are in the first file but not in the second
and vice versa.
1. The trees have the same branches. The same checks as above will be carried out here.
1. The branches of the corresponding trees have the same values.

the output will also go to a `summary.yaml` file that will look like:

```yaml
'Branches that differ for tree: Hlt2RD_BToMuE/DecayTree':
  - L2_BREMHYPOENERGY
  - L2_ECALPIDMU
  - L1_IS_NOT_H
'Branches that differ for tree: Hlt2RD_LbToLMuMu_LL/DecayTree':
  - P_CaloNeutralHcal2EcalEnergyRatio
  - P_BREMENERGY
  - Pi_IS_NOT_H
  - P_BREMPIDE
Trees only in file_1.root: []
Trees only in file_2.root:
  - Hlt2RD_BuToKpEE_MVA_misid/DecayTree
  - Hlt2RD_BsToPhiMuMu_MVA/DecayTree
```

# File system

## Versions

The utilities below allow the user to deal with versioned files and directories

```python
from dmu.generic.version_management import get_last_version
from dmu.generic.version_management import get_next_version
from dmu.generic.version_management import get_latest_file

# get_next_version will take a version and provide the next one, e.g.
get_next_version('v1')           # -> 'v2'
get_next_version('v1.1')         # -> 'v2.1'
get_next_version('v10.1')        # -> 'v11.1'

get_next_version('/a/b/c/v1')    # -> '/a/b/c/v2'
get_next_version('/a/b/c/v1.1')  # -> '/a/b/c/v2.1'
get_next_version('/a/b/c/v10.1') # -> '/a/b/c/v11.1'

# `get_latest_file` will return the path to the file with the highest version
# in the `dir_path` directory that matches a wildcard, e.g.:

last_file = get_latest_file(dir_path = file_dir, wc='name_*.txt')

# `get_last_version` will return the string with the latest version
# of directories in `dir_path`, e.g.:

oversion=get_last_version(dir_path=dir_path, version_only=True)  # This will return only the version, e.g. v3.2
oversion=get_last_version(dir_path=dir_path, version_only=False) # This will return full path, e.g. /a/b/c/v3.2
```

The `get_last_version` function works for versions of the form `vN`, `vN.M` and `vNpM`. 
Where `N` and `M` are integers.

# Testing

## Pytest utilities

In order to collect the pytest tests in a given directory, do:

```python
from dmu import pytest_utilities

data : dict[int,str] = pytest_utilities.get_tests(path = '/path/to/tests/')
```

Here `data` will map an index starting at zero to the name of the test
as required to run `pytest {name_of_test}`.

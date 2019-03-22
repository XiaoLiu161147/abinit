# WIP The new testsuite

## Presentation

### A name for the project ?

- ABINEAT: ABInit NEw physics Aware Testing
- NEAT: New Abinit Testing
- ABINUTS / NUTS: New Unit Testing System / New Unit Test Suite

### Principle

The goal of this project is to give to ABINIT developers tools to create
physics aware tests.  The mean to achieve this is a set of Fortran and Python
tools to output structured data and process it easily.

### Motivations

__Current situation__

In its current state the ABINIT testing system is based on inputs files and
associated reference output files.  A test consist in comparing the reference
file with the output file of a fresh run in a pretty linear way, only making
difference between floating-point numbers and other strings.

This approach is very strict because it compares every single quantity in the
main output file and report each time a difference exceed a given tolerance.
Moreover, the line number (and therefor the number of iterations in every loops
printing in the output file) have to be exactly the same to allow the
comparison to end properly and mark the test as succeeded.

Given the variety of configurations of the test farm and the use of different
parallelism configurations it may be hard to create a stable test with decent
tolerances and a lot of current test are really weak because of this
limitation.

__Solution concepts__

The proposal of this project is to allow stricter tests on pertinent
quantities, ignoring the rest. This can be achieved by creating tests
specialized for given physical quantities, taking in account there properties
(Newton's Law, energy conservation, well-known equations...).

Of course all these tests would have to be designed nearly independently for
every interesting quantities and that is why this project should focus on
producing reusable tools to create these tests.

These tools would be used to create the tests associated with the more common
quantities of ground state calculations (components of total energy, stress
tensor and atomic forces). The test suite would be enriched later with the
participation of the ABINIT community.


## Proof of concept implementation

The output of data should use a machine-readable format, preferably human
readable but not necessarily.  This format could be YAML which is already used
in a few situations in ABINIT, JSON (for its great support) or NetCDF (already
used in Abipy).  Post processing tools may be available like plotting and
computing facilities based on standard python technologies like NumPy, SciPy,
Matplotlib and Pandas. Currently the prototype integrate YAML syntax and NumPy
arrays.

For the Fortran side routines may be available to output given structures of
data (matrices, scalars, arrays...) along with meaningful metadata helping post
processing and analysis.

A few basic tools have already been implemented to check feasibility.

On the Fortran side:

- a module based on C and Fortran code have been written for managing a
  map-like key-value pair list. Pair list have been chosen over hash table
  because in the practical case the O(n) cost of finding a key is less
  problematic than the overhead in memory usage of hash tables because their
  will never be a lot of elements in the table.  The pair list can dynamically
  hold either real of integer values. It implements the basic getters and
  setters and an iterator system to allow looping over the key-value pairs
  easily in Fortran.
- a module written in Fortran provides tools to manipulate variable length
  strings with a file like interface.
- a module written in Fortran and using the two previous module have been
  written to easily output YAML into an arbitrary file from Fortran code. This
  module is supposed to be the lowest level layer of the output system and
  may be abstracted by higher layers. It provides basic routines for output
  YAML documents based on a mapping at the root and containing well formated
  (as human readable as possible and valid YAML) 1D and 2D arrays of numbers
  (integer or real), key-value mapping (using pair lists), list of key-value
  mapping and scalar fields.  Routines support tags for specifying special data
  structures.
- a higher level module called m\_neat provide routines for creating specific
  documents associated with interesting physical properties. Currently routines
  for total energy components and ground state general results are implemented.

On the python side:

- fldiff algorithm have been slightly modified to extract encountered YAML
  documents from the source and reserve them for later treatment.
- Tools have been written to make easier the creation of new classes
  corresponding to YAML tags for adding new features to the extracted data.
  These tools are very easy to use class decorators.
- These tools have been used to create basic classes for futures tags, among
  other classes that directly convert YAML list of numbers into NumPy arrays.
  These classes may be used as examples for the creation of further tags.
- A parser for test configuration have been added and all facilities to do
  tests are in place.
- A command line tool testtools.py to allow doing different manual actions (see
  Test CLI)


## Test specification draft

### Declaration from ABINIT input file

ABINIT input files for tests already embed information for the test suite in a
specific TEST\_INFO section at the end of the file. This section is structured
with a INI like syntax (the syntax define by the config parser module of
Python). The introduction of YAML based test will be done with two modifications
to the current test specification:

- the *files\_to\_test* option will hold a new optional argument *use_yaml*
  that will hold one of "yes" (default, use YAML based test), "no" (do not use
  YAML test) or "only" (use YAML based test but not legacy fldiff algorithm)
- a new section *[yaml_test]* will optionally be added with two options: *test*
  whom value is an embedded test specification and *file* which would be a path to
  the file containing the test specification

### Test specification syntax

The test specification will also use YAML syntax. It uses three basic concepts:

- _constraint_ is an actual check of the data
- _parameter_ is an arbitrary value passed to some constraint and that can
  modify there behavior
- _specialization_ is a way to override already defines _constraints_ and
  _parameters_ for a specific node of the data tree (and its children)

The test configuration file consists of a single YAML document structured as a
mapping. Each element of the mapping can be a constraint, a parameter of a
specialization. The distinction is made by looking at the list of known
parameters and constraints. The value of a parameter or a constraint depend on
its definition. The value of a specialization is itself a mapping filled with
parameters, constraints and specialization.

The first level of specialization match the documents label value from tested
files. The next levels match the different attributes of the document.

To get the list of constraints and parameters run the program
`~abinit/tests/testtools.py explore` and type `show *`. You can then type for
example `show tol_eq` to learn more about a specific constraint or parameter.

Constraints and parameters have several properties that define their behavior.
Most of the time constraints and parameters and apply to all children level,
they are inherited, though some of them apply only at the level where they are
defined. Constraints can have a list of parameters they use. If these parameters
are not available at the current level (they are not defined in any higher
level, or they cannot be inherited) the default value of the parameter is used.
Constraints can be mutually exclusive which mean that when a constraint is
defined, all constraints define in higher level this one excludes are hidden to
the current level and its children.

Here is an example of a possible file:
```yaml
Etot:  # this defines rules for the document Etot
    tol: 1.0e-3  # this say that for all numerical values encountered in
                 # the document Etot we will check a tolerance of 1.0e-3
                 # both on absolute a relative differences
    Kinetic energy:  # this override the tol constraints for the Kinetic energy
                     # attribute
        tol: 1.0e-10

results_gs:
    tol: 1.0e-5
    convergence:
        ceil: 5.0e-8  # here we define a ceil which exclude tol
                      # instead of a test between ref and tested file
                      # we will just check that values in convergence
                      # are below 5.0e-8
        residm:
            ceil: 5.0e-6

    entropy:
        ceil: 1.0e-10

    stress tensor:
        tol: 1.0e-5
        tensor_is_symetric: True  # check that tensor is symetric

    cartesian_force:
        tol_eq: 1.0e-8  # tol_eq is a parameter used by equation
        equation: "this.sum(axis=0)"  # 2-norm of sum of forces is under 1e-8

    etotal:
        tol: 1.0e-8
```

In some cases it is important to define different behavior depending on the
state of iterations (dtset, image...).  This is possible thanks to a tool
called __filters__. Filters allow user to add special constraints and
parameters when treating documents matching a given set of dtset, image etc. To
define a filter user use the special node _filters_, each child of this node
is a filter.  The label of the child define the name of the filter and its
children define the set it matches. See the example below use two filters that
simply match one specific dataset.

```yaml
lda:
    results_gs:
        tol_abs: 1.0e-6

dmft:
    results_gs:
        cartesian forces:
            ignore

filters:
    lda:
        dtset: 1
    dmft:
        dtset: 2
```

A filter can specify all currently known iterators: dtset, timimage, image, and
time. For each iterator a set of integers can be defined with three methods:

- a single integer value
- a YAML list of value
- a mapping with optional members "from" and "to" giving the boundaries (both
  included) of the integer interval If "from" is omitted the default is 1. If
  "to" is omitted the default is no upper boundary.

Several filters can be used for the same document if they overlap. However, it
is fundamental that an order of specificity can be determined which means that
overlapping filters must absolutely be included in each other. Though the first
example below is fine because _f2_ is included in _f1_ but the second example
will raise an error because _f4_ is not included in _f3_.

```yaml
# this is fine
filters:
    f1:
        dtset:
            from: 2
            to: 7
        image:
            from: 4

    f2:
        dtset: 7
        image:
        - 4
        - 5
        - 6
```

```yaml
# this will raise an error
filters:
    f3:
        dtset:
            from: 2
            to: 7
        image:
            from: 4

    f4:
        dtset: 7
        image:
            from: 1
            to: 5
```

When a test is defined, the default tree is overridden by the user defined
tree. When a filtered tree is used it overrides the less specific tree. As you
can see, the overriding process is used everywhere. Though, it is important to
know how it works. By default, only what is explicitly specified is overridden
which means that if a constraint is defined at a deeper level on the default
tree than what is done on the new tree, the original constraints will be kept.
For example let `f1`  and `f2` two filters such that `f2` is included in `f1`.
```yaml
f1:
    results_gs:
        tol_abs: 1.0e-6
        convergence:
            ceil: 1.0e-6
            diffor:
                1.0e-4

f2:
    results_gs:
        tol_rel: 1.0e-7
        convergence:
            ceil: 1.0e-7

filters:
    f1:
        dtset: 1
    f2:
        dtset: 1
        image: 5
```
When the tester will reach the fifth image of the first dataset the config tree
used will be the following:
```yaml
results_gs:
    tol_abs: 1.0e-6
    tol_rel: 1.0e-7  # this has been appended without modifying anything else
    convergence:
        ceil: 1.0e-7  # this one have been overridden
        diffor:
            1.0e-4  # this one have been kept
```

If this is not the behavior you need, you can you the "hard reset marker".
Append `!` to the name of the specialization you want to override to completely
replace it. Let the `f2` tree be :
```yaml
f2:
    results_gs:
        convergence!:
            ceil: 1.0e-7
```

and now the resulting tree for fifth image of the first dataset is
```yaml
results_gs:
    tol_abs: 1.0e-6
    convergence:  # the whole convergence node have been overriden
        ceil: 1.0e-7
```

Here again the `explore` shell could be of great help to know what is inherited
from other trees and what is overridden.


## Test tools

A command line tool `~abinit/tests/testtools.py` provide tools to work on
writing tests.  It provides help if run without argument.  The available sub
commands are described here.

### Diff

The __diff__ sub-command provide a command line interface to the fldiff.py
module. It may be useful to compare output and reference file without running
ABINIT each time like `runtest.py` would do.

It allows the user to provide the same parameters that are passed by the
testsuite.py when runtest.py is used.

Use `~abinit/tests/testtools.py diff --help` for more informations.

### Explore

This tool provides is helpful to explore a test configuration file. It provides a
shell like interface where the user can move around the tree of the
configuration file, seeing what constraints define the test. It also provides
documentation about constraints and parameters using the show command. Run
`~abinit/tests/testtools.py explore` to use it.

## Extending the test suite

### Entry points
There are three main entry points of growing complexity in this system.

The first is the yaml file configuration intended to all Abinit developers. It
does not expect any Python knowledges, but only comprehension of the conventions
for writing a test. Being fully declarative (no logic) it should be quite easy
to learn from existing examples.

The second is the file *~abinit/tests/pymods/yaml_tests/conf_parser.py*. It
contains declarations of the available constraints and parameters. A basic
python understanding is required to modify that file. Comments en docstring
should help to grasp this file.

The third is the file *~abinit/tests/pymods/yaml_tests/structures.py*. It
defines the structures used by YAML parser when reaching a tag (starting with
!), or in some cases when reaching a given pattern (__undef__ for example). Even
if the abstraction layer on top of _yaml_ module should help, it is better to
have a good understanding of more "advanced" python concept like _inheritance_
_decorators_, _classmethod_...

### Code structure

As long as possible, it is better to include any extensions to the existing code
in these three entry points to keep the system consistent. However, this system
will eventually prove to be limited in some way. Hence, here is the general
structure of the system.

The whole system consists in three main parts:
- *~abinit/tests/pymods/fldiff.py* is the interface between the yaml specific
  tools and the legacy test suite tools. It implements the legacy algorithm and
  the creation of the final report.
- *~abinit/tests/pymods/data_extractor.py*,
  *~abinit/tests/pymods/yaml_tools/__init__.py* and
  *~abinit/tests/pymods/yaml_tools/structures.py* constitute the Abinit output
  parser. *data_extractor.py* identify and extract the YAML documents from the
  source, *__init__.py* provide generic tools base on pyyaml to parse the
  documents and *structures.py* provide the classes that are used by YAML to
  handle tags. *~abinit/tests/pymods/yaml_tools/register_tag.py* define the
  abstraction layer used to simplify the code in *structures.py*. It directly
  deals with PyYaml black magic.
- the other files in *~abinit/tests/pymods/yaml_tools* are dedicated to the
  testing procedure. *meta_conf_parser.py* provide the tools to read and
  interpret the YAML configuration file, namely __ConfParser__ the main parsing
  class, __ConfTree__ the tree configuration "low-level" interface (only handle
  a single tree, no access to the inherited properties, etc...) and __Constraint__
  the representation of a specific test in the tree.  *conf_parser.py* use
  __ConfParser__ to register actuals constraints and parameters. It is the place
  to define actual tests. *driver_test_conf.py* define the high level access to
  the configuration, handling several trees, applying filters etc. Finally,
  *tester.py* is the main test driver. It browses the data tree and use the
  configuration to run tests on Abinit output. It produces an __Issue__ list that
  will be used by *fldiff.py* to produce the report.
 

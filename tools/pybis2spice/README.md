# THIS REPOSITORY IS NO LONGER MAINTAINED

# pybis2spice
A python tool that converts IBIS models to SPICE models. The ibis model types currently supported are: 
* Input
* Output
* 3-State
* Open_Drain
* I/O

## Usage
The bin folder holds a zipped file for each released version containing a windows executable program that can be run standalone.

![](/img/gui-window.png)

### The executable program allows the user to:
* Browse for an ibis model file
* Select the component and the model
* Create the SPICE subcircuit files
* View the ibis model characteristics (I-V and Voltage-Time graphs)

![](/img/gui-check-model.png)


### Spice Subcircuit option: 
* LTSpice: LTSpice option produces a subcircuit file and corresponding LTSpice symbol file. 
This option creates a subcircuit that is specifically intended to be used with LTSpice.
* Generic: generic option produces a subcircuit file that most Spice simulators should be able to parse.
* NgSpice: rewrites the generic model into ngspice-friendly syntax (`pwl(...)`, sanitized subcircuit names).
* Input-Driven: creates an ngspice model with explicit `OUT IN EN VCC VSS` pins. This uses a
  SPISim-style runtime flow where short T-lines derive edge direction and elapsed time during simulation,
  and waveform-derived `Ku/Kd` tables are selected from that elapsed time.

For ngspice/channel work, **Input-Driven** is the recommended default.

### Corner Select: 
* Weak-Slow: Combines the minimum (weak) I-V curves and minimum (slow) Voltage-Time waveforms   
* Typical: Combines the typical I-V curves and typical Voltage-Time waveforms
* Fast-Strong: Combines the maximum (strong) I-V curves and maximum (fast) Voltage-Time waveforms
* All: Creates the subcircuit files for all corners simultaneously

## Examples
LTSpice examples are given to highlight the different options available. 
These are available in the examples folder

For programmatic use, the ngspice input-driven path looks like:

```python
from pybis2spice import pybis2spice, subcircuit

ibis = pybis2spice.get_ibis_model_ecdtools("model.ibs")
ibis_data = pybis2spice.DataModel(ibis, model_name="MY_MODEL", component_name="MY_COMPONENT")
subcircuit.generate_spice_model(
    io_type="Output",
    subcircuit_type="InputDriven",
    ibis_data=ibis_data,
    corner="Typical",
    output_filepath="MY_MODEL_OutputInput_Typical.sub",
)
```

This produces a converted output buffer that accepts an external runtime stimulus on `IN`,
which is the right path for PRBS/channel simulation in ngspice.

### Batch conversion

To convert all models in an IBIS file for one selected component:

```python
from pybis2spice import pybis2spice, subcircuit

ibis = pybis2spice.get_ibis_model_ecdtools("model.ibs")
results = subcircuit.generate_spice_models_for_all_models(
    ibis_model_ecdtools=ibis,
    component_name="MY_COMPONENT",
    output_dir="out_models",
    io_type="Output",
    subcircuit_type="InputDriven",
    corner="Typical",   # or "All"
)
```

The batch helper returns generated, skipped, failed, and symbol lists.
Models whose `Model_type` is incompatible with the chosen `io_type` are skipped.


## References
The tool would not be possible without the ecdtools library. This parses the ibis file into python data structures.
https://ecdtools.readthedocs.io/en/latest/#


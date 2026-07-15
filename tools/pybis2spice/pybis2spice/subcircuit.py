# ----------------------------------------------------------------------------
# Author: Kishan Amratia
# Module Name: subcircuit.py
#
# Module Description:
# Companion functions for the pybis2spice module to create the SPICE subcircuit file
#
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os.path
import re
import tempfile

import numpy as np
from pybis2spice import pybis2spice
from pybis2spice import version


_TIME = 0
_KU = 1
_KD = 2
_KD_OD = 1


def normalize_subcircuit_type(subcircuit_type):
    """
    Normalizes user-facing subcircuit type names while keeping backward compatibility.
    """
    aliases = {
        "LTSpice": "LTSpice",
        "Generic": "Generic",
        "NgSpice": "NgSpice",
        "InputDriven": "InputDriven",
        "Input-Driven": "InputDriven",
        "NgSpiceInputDriven": "InputDriven",
        "NgSpiceExternalInput": "InputDriven",
        "InputDrivenStateContinuous": "InputDrivenStateContinuous",
        "Input-Driven-State-Continuous": "InputDrivenStateContinuous",
        "NgSpiceInputDrivenStateContinuous": "InputDrivenStateContinuous",
        "InputDrivenCoeffState": "InputDrivenCoeffState",
        "Input-Driven-Coeff-State": "InputDrivenCoeffState",
        "NgSpiceInputDrivenCoeffState": "InputDrivenCoeffState",
        "InputDrivenShortPulseHybrid": "InputDrivenShortPulseHybrid",
        "Input-Driven-Short-Pulse-Hybrid": "InputDrivenShortPulseHybrid",
        "NgSpiceInputDrivenShortPulseHybrid": "InputDrivenShortPulseHybrid",
        "InputDrivenShortPulseHybridMainSlope": "InputDrivenShortPulseHybridMainSlope",
        "Input-Driven-Short-Pulse-Hybrid-Main-Slope": "InputDrivenShortPulseHybridMainSlope",
        "InputDrivenShortPulseHybridConstrained": "InputDrivenShortPulseHybridConstrained",
        "Input-Driven-Short-Pulse-Hybrid-Constrained": "InputDrivenShortPulseHybridConstrained",
        "InputDrivenGateStateHybrid": "InputDrivenGateStateHybrid",
        "Input-Driven-Gate-State-Hybrid": "InputDrivenGateStateHybrid",
        "NgSpiceInputDrivenGateStateHybrid": "InputDrivenGateStateHybrid",
        "InputDrivenGateStateFull": "InputDrivenGateStateFull",
        "Input-Driven-Gate-State-Full": "InputDrivenGateStateFull",
        "NgSpiceInputDrivenGateStateFull": "InputDrivenGateStateFull",
        "InputDrivenDirectionalGateStateHybrid": "InputDrivenDirectionalGateStateHybrid",
        "Input-Driven-Directional-Gate-State-Hybrid": "InputDrivenDirectionalGateStateHybrid",
        "NgSpiceInputDrivenDirectionalGateStateHybrid": "InputDrivenDirectionalGateStateHybrid",
        "InputDrivenDirectionalGateStateFull": "InputDrivenDirectionalGateStateFull",
        "Input-Driven-Directional-Gate-State-Full": "InputDrivenDirectionalGateStateFull",
        "NgSpiceInputDrivenDirectionalGateStateFull": "InputDrivenDirectionalGateStateFull",
        "InputDrivenChargeLimitedGateHybrid": "InputDrivenChargeLimitedGateHybrid",
        "Input-Driven-Charge-Limited-Gate-Hybrid": "InputDrivenChargeLimitedGateHybrid",
        "NgSpiceInputDrivenChargeLimitedGateHybrid": "InputDrivenChargeLimitedGateHybrid",
        "InputDrivenChargeLimitedGateFull": "InputDrivenChargeLimitedGateFull",
        "Input-Driven-Charge-Limited-Gate-Full": "InputDrivenChargeLimitedGateFull",
        "NgSpiceInputDrivenChargeLimitedGateFull": "InputDrivenChargeLimitedGateFull",
        "InputDrivenChargeLimitedGateFastRecover": "InputDrivenChargeLimitedGateFastRecover",
        "Input-Driven-Charge-Limited-Gate-Fast-Recover": "InputDrivenChargeLimitedGateFastRecover",
        "NgSpiceInputDrivenChargeLimitedGateFastRecover": "InputDrivenChargeLimitedGateFastRecover",
        "InputDrivenValueMatchedReplayHybrid": "InputDrivenValueMatchedReplayHybrid",
        "Input-Driven-Value-Matched-Replay-Hybrid": "InputDrivenValueMatchedReplayHybrid",
        "NgSpiceInputDrivenValueMatchedReplayHybrid": "InputDrivenValueMatchedReplayHybrid",
        "InputDrivenValueMatchedReplayFull": "InputDrivenValueMatchedReplayFull",
        "Input-Driven-Value-Matched-Replay-Full": "InputDrivenValueMatchedReplayFull",
        "NgSpiceInputDrivenValueMatchedReplayFull": "InputDrivenValueMatchedReplayFull",
        "InputDrivenValueMatchedReplayBalanced": "InputDrivenValueMatchedReplayHybrid",
        "InputDrivenValueMatchedReplayKuOnly": "InputDrivenValueMatchedReplayKuOnly",
        "Input-Driven-Value-Matched-Replay-Ku-Only": "InputDrivenValueMatchedReplayKuOnly",
        "InputDrivenValueMatchedReplayKdOnly": "InputDrivenValueMatchedReplayKdOnly",
        "Input-Driven-Value-Matched-Replay-Kd-Only": "InputDrivenValueMatchedReplayKdOnly",
        "InputDrivenValueMatchedReplayV2Hybrid": "InputDrivenValueMatchedReplayV2Hybrid",
        "Input-Driven-Value-Matched-Replay-V2-Hybrid": "InputDrivenValueMatchedReplayV2Hybrid",
        "NgSpiceInputDrivenValueMatchedReplayV2Hybrid": "InputDrivenValueMatchedReplayV2Hybrid",
        "InputDrivenValueMatchedReplayV2Balanced": "InputDrivenValueMatchedReplayV2Hybrid",
        "InputDrivenValueMatchedReplayV2KuOnly": "InputDrivenValueMatchedReplayV2KuOnly",
        "Input-Driven-Value-Matched-Replay-V2-Ku-Only": "InputDrivenValueMatchedReplayV2KuOnly",
        "InputDrivenValueMatchedReplayV2KdOnly": "InputDrivenValueMatchedReplayV2KdOnly",
        "Input-Driven-Value-Matched-Replay-V2-Kd-Only": "InputDrivenValueMatchedReplayV2KdOnly",
        "InputDrivenValueMatchedReplayV2SplitKuKd": "InputDrivenValueMatchedReplayV2SplitKuKd",
        "Input-Driven-Value-Matched-Replay-V2-Split-Ku-Kd": "InputDrivenValueMatchedReplayV2SplitKuKd",
        "InputDrivenTwoStateGatePwlFull": "InputDrivenTwoStateGatePwlFull",
        "Input-Driven-Two-State-Gate-Pwl-Full": "InputDrivenTwoStateGatePwlFull",
        "NgSpiceInputDrivenTwoStateGatePwlFull": "InputDrivenTwoStateGatePwlFull",
        "InputDrivenTwoStateGateIdentityFull": "InputDrivenTwoStateGateIdentityFull",
        "Input-Driven-Two-State-Gate-Identity-Full": "InputDrivenTwoStateGateIdentityFull",
        "NgSpiceInputDrivenTwoStateGateIdentityFull": "InputDrivenTwoStateGateIdentityFull",
        "InputDrivenTwoStateGatePwlHybrid": "InputDrivenTwoStateGatePwlHybrid",
        "Input-Driven-Two-State-Gate-Pwl-Hybrid": "InputDrivenTwoStateGatePwlHybrid",
        "NgSpiceInputDrivenTwoStateGatePwlHybrid": "InputDrivenTwoStateGatePwlHybrid",
        "InputDrivenTwoStateGateDirectionalFull": "InputDrivenTwoStateGateDirectionalFull",
        "Input-Driven-Two-State-Gate-Directional-Full": "InputDrivenTwoStateGateDirectionalFull",
        "InputDrivenTwoStateGateDirectionalPwlFull": "InputDrivenTwoStateGateDirectionalFull",
        "NgSpiceInputDrivenTwoStateGateDirectionalFull": "InputDrivenTwoStateGateDirectionalFull",
        "InputDrivenTwoStateGateDirectionalResidualFull": "InputDrivenTwoStateGateDirectionalResidualFull",
        "Input-Driven-Two-State-Gate-Directional-Residual-Full": "InputDrivenTwoStateGateDirectionalResidualFull",
        "NgSpiceInputDrivenTwoStateGateDirectionalResidualFull": "InputDrivenTwoStateGateDirectionalResidualFull",
        "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull": "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull",
        "Input-Driven-Two-State-Gate-Directional-Residual-Recover-Mean-Full": "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull",
        "NgSpiceInputDrivenTwoStateGateDirectionalResidualRecoverMeanFull": "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull",
        "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull": "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull",
        "Input-Driven-Two-State-Gate-Directional-Residual-Recover-Fast-Full": "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull",
        "NgSpiceInputDrivenTwoStateGateDirectionalResidualRecoverFastFull": "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull",
    }
    return aliases.get(subcircuit_type, subcircuit_type)


def model_type_matches_io(model_type, io_type):
    """
    Returns True if the IBIS model_type is compatible with the requested I/O direction.
    """
    model_type = str(model_type).lower()

    if io_type == "Input":
        return model_type in ["input", "i/o", "i/o_open_drain"]

    if io_type == "Output":
        return model_type in ["output", "i/o", "3-state", "open_drain", "i/o_open_drain"]

    return False


def generate_spice_model(io_type, subcircuit_type, ibis_data, corner, output_filepath):
    """
    Wrapper around the subcircuit file creation functions. Calls the relevant function i.e. LTSpice or Generic

        Parameters:
            io_type - "Input" or "Output"
            subcircuit_type - "LTSpice", "Generic", "NgSpice", or "NgSpiceInputDriven"
            ibis_data - a DataModel object (defined in pybis2spice.py)
            corner - "WeakSlow" or "Typical" or "FastStrong"
            output_filepath - path of output file

        Returns:
            The path of the created file
    """
    subcircuit_type = normalize_subcircuit_type(subcircuit_type)
    ret = None
    if subcircuit_type == "NgSpice":
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type == "InputDriven":
        if io_type == "Output":
            return create_ngspice_input_driven_output_model(ibis_data, corner, io_type, output_filepath)
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type == "InputDrivenStateContinuous":
        if io_type == "Output":
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                state_continuous=True,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type == "InputDrivenCoeffState":
        if io_type == "Output":
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                coeff_state=True,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {
        "InputDrivenShortPulseHybrid",
        "InputDrivenShortPulseHybridMainSlope",
        "InputDrivenShortPulseHybridConstrained",
    }:
        if io_type == "Output":
            strategy = {
                "InputDrivenShortPulseHybrid": "branch",
                "InputDrivenShortPulseHybridMainSlope": "main_slope",
                "InputDrivenShortPulseHybridConstrained": "constrained",
            }[subcircuit_type]
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                short_pulse_hybrid=strategy,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {"InputDrivenGateStateHybrid", "InputDrivenGateStateFull"}:
        if io_type == "Output":
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                gate_state_mode="hybrid" if subcircuit_type == "InputDrivenGateStateHybrid" else "full",
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {"InputDrivenDirectionalGateStateHybrid", "InputDrivenDirectionalGateStateFull"}:
        if io_type == "Output":
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                directional_gate_state_mode=(
                    "hybrid" if subcircuit_type == "InputDrivenDirectionalGateStateHybrid" else "full"
                ),
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {
        "InputDrivenChargeLimitedGateHybrid",
        "InputDrivenChargeLimitedGateFull",
        "InputDrivenChargeLimitedGateFastRecover",
    }:
        if io_type == "Output":
            mode = {
                "InputDrivenChargeLimitedGateHybrid": "hybrid",
                "InputDrivenChargeLimitedGateFull": "full",
                "InputDrivenChargeLimitedGateFastRecover": "fast_recover",
            }[subcircuit_type]
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                charge_limited_gate_mode=mode,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {
        "InputDrivenValueMatchedReplayHybrid",
        "InputDrivenValueMatchedReplayFull",
        "InputDrivenValueMatchedReplayKuOnly",
        "InputDrivenValueMatchedReplayKdOnly",
    }:
        if io_type == "Output":
            mode = {
                "InputDrivenValueMatchedReplayHybrid": "hybrid_balanced",
                "InputDrivenValueMatchedReplayFull": "full_balanced",
                "InputDrivenValueMatchedReplayKuOnly": "hybrid_ku",
                "InputDrivenValueMatchedReplayKdOnly": "hybrid_kd",
            }[subcircuit_type]
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                value_matched_replay_mode=mode,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {
        "InputDrivenValueMatchedReplayV2Hybrid",
        "InputDrivenValueMatchedReplayV2KuOnly",
        "InputDrivenValueMatchedReplayV2KdOnly",
        "InputDrivenValueMatchedReplayV2SplitKuKd",
    }:
        if io_type == "Output":
            mode = {
                "InputDrivenValueMatchedReplayV2Hybrid": "hybrid_balanced",
                "InputDrivenValueMatchedReplayV2KuOnly": "hybrid_ku",
                "InputDrivenValueMatchedReplayV2KdOnly": "hybrid_kd",
                "InputDrivenValueMatchedReplayV2SplitKuKd": "hybrid_split",
            }[subcircuit_type]
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                value_matched_replay_v2_mode=mode,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)
    if subcircuit_type in {
        "InputDrivenTwoStateGatePwlFull",
        "InputDrivenTwoStateGateIdentityFull",
        "InputDrivenTwoStateGatePwlHybrid",
        "InputDrivenTwoStateGateDirectionalFull",
        "InputDrivenTwoStateGateDirectionalResidualFull",
        "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull",
        "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull",
    }:
        if io_type == "Output":
            mode = {
                "InputDrivenTwoStateGatePwlFull": "pwl_full",
                "InputDrivenTwoStateGateIdentityFull": "identity_full",
                "InputDrivenTwoStateGatePwlHybrid": "pwl_hybrid",
                "InputDrivenTwoStateGateDirectionalFull": "directional_full",
                "InputDrivenTwoStateGateDirectionalResidualFull": "directional_residual_full",
                "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull": "directional_residual_recover_mean_full",
                "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull": "directional_residual_recover_fast_full",
            }[subcircuit_type]
            return create_ngspice_input_driven_output_model(
                ibis_data,
                corner,
                io_type,
                output_filepath,
                two_state_gate_mode=mode,
            )
        return create_ngspice_model(ibis_data, corner, io_type, output_filepath)

    if io_type == "Output":

        if subcircuit_type == "Generic":
            ret = create_generic_output_model(ibis_data, corner, io_type, output_filepath)

        if subcircuit_type == "LTSpice":
            ret = create_ltspice_output_model(ibis_data, corner, io_type, output_filepath)

    if io_type == "Input":
        ret = create_input_model(ibis_data, corner, io_type, output_filepath)

    return ret


def generate_spice_models_for_all_models(ibis_model_ecdtools, component_name, output_dir,
                                         io_type="Output", subcircuit_type="InputDriven",
                                         corner="Typical"):
    """
    Batch converts all models in an IBIS file for one selected component.

    Returns a dictionary with generated, skipped, failed, and symbols lists.
    """
    os.makedirs(output_dir, exist_ok=True)
    subcircuit_type = normalize_subcircuit_type(subcircuit_type)

    corners = ["WeakSlow", "Typical", "FastStrong"] if corner == "All" else [corner]
    results = {
        "generated": [],
        "symbols": [],
        "skipped": [],
        "failed": [],
    }

    for model_name in pybis2spice.list_models(ibis_model_ecdtools):
        ibis_data = pybis2spice.DataModel(ibis_model_ecdtools, model_name, component_name)

        if not hasattr(ibis_data, 'model'):
            results["failed"].append({"model": model_name, "reason": "unable to load model"})
            continue

        if not model_type_matches_io(ibis_data.model_type, io_type):
            results["skipped"].append(
                {"model": model_name, "reason": f'model type "{ibis_data.model_type}" incompatible with {io_type}'}
            )
            continue

        for _corner in corners:
            filename = f'{ibis_data.model_name}-{io_type}-{_corner}.sub'
            filepath = os.path.join(output_dir, filename)

            ret_val = generate_spice_model(io_type=io_type,
                                           subcircuit_type=subcircuit_type,
                                           ibis_data=ibis_data,
                                           corner=_corner,
                                           output_filepath=filepath)

            if ret_val == 0:
                results["generated"].append(filepath)
                if subcircuit_type == "LTSpice":
                    symbol_file = create_ltspice_symbol(ibis_data, _corner, filepath, io_type)
                    results["symbols"].append(symbol_file)
            else:
                results["failed"].append({"model": model_name, "corner": _corner, "reason": "generation failed"})

    return results


def sanitize_ngspice_identifier(name):
    """
    Returns a conservative ngspice subcircuit identifier.
    """
    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', name)
    if sanitized and sanitized[0].isdigit():
        sanitized = f'_{sanitized}'
    return sanitized


def convert_subcircuit_text_to_ngspice(spice_text, ibis_data, corner, io_type):
    """
    Converts the LTSpice/generic-flavored text emitted by this module to syntax
    accepted by ngspice.
    """
    old_subckt_name = f'{ibis_data.model_name}-{io_type}-{corner}'
    new_subckt_name = sanitize_ngspice_identifier(old_subckt_name)

    spice_text = spice_text.replace(old_subckt_name, new_subckt_name)
    spice_text = spice_text.replace('table(', 'pwl(')
    spice_text = spice_text.replace('{if(calc_gap_pos <= 0, 0.1e-12, calc_gap_pos)}',
                                    '{max(calc_gap_pos, 0.1e-12)}')
    spice_text = spice_text.replace('{if(calc_gap_neg <= 0, 0.1e-12, calc_gap_neg)}',
                                    '{max(calc_gap_neg, 0.1e-12)}')
    spice_text = convert_relative_pwl_sources_to_ngspice(spice_text)

    return spice_text


def format_ngspice_pwl_time(symbols, numeric_offset):
    """
    Formats a cumulative PWL time expression for ngspice.
    """
    if not symbols:
        return f'{numeric_offset:.16e}'

    terms = list(symbols)
    if numeric_offset:
        terms.append(f'{numeric_offset:.16e}')
    return '{' + '+'.join(terms) + '}'


def convert_relative_pwl_tokens_to_absolute(tokens):
    """
    Converts LTSpice relative PWL time tokens (+dt) into absolute time tokens.
    """
    converted = []
    symbols = []
    numeric_offset = 0.0

    for idx in range(0, len(tokens), 2):
        time_token = tokens[idx]
        value_token = tokens[idx + 1]

        if idx == 0:
            numeric_offset = float(time_token.strip('{}'))
        elif time_token.startswith('+'):
            increment = time_token[1:]
            if increment.startswith('{') and increment.endswith('}'):
                symbols.append(increment[1:-1])
            else:
                numeric_increment = float(increment)
                if numeric_increment <= 0:
                    numeric_increment = 1e-18
                numeric_offset += numeric_increment
        else:
            symbols = []
            numeric_offset = float(time_token.strip('{}'))

        converted.append(format_ngspice_pwl_time(symbols, numeric_offset))
        converted.append(value_token)

    return converted


def convert_relative_pwl_sources_to_ngspice(spice_text):
    """
    Converts independent-source PWL definitions from LTSpice relative time
    syntax to ngspice absolute time syntax.
    """
    converted_lines = []
    pwl_pattern = re.compile(r'(PWL\()(.+)(\))')

    for line in spice_text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith('V') or 'PWL(' not in line or '+' not in line:
            converted_lines.append(line)
            continue

        match = pwl_pattern.search(line)
        if not match:
            converted_lines.append(line)
            continue

        tokens = match.group(2).split()
        if len(tokens) % 2 != 0:
            converted_lines.append(line)
            continue

        converted_tokens = convert_relative_pwl_tokens_to_absolute(tokens)
        converted_pwl = match.group(1) + ' '.join(converted_tokens) + match.group(3)
        converted_lines.append(line[:match.start()] + converted_pwl + line[match.end():])

    return '\n'.join(converted_lines) + '\n'


def create_ngspice_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates an ngspice-compatible SPICE subcircuit.

    The original generic output is close, but uses LTSpice-style table()
    behavioral expressions and subcircuit names with punctuation that ngspice
    does not parse reliably.
    """
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.sub', delete=False) as temp_file:
        temp_filepath = temp_file.name

    try:
        if io_type == "Output":
            ret = create_generic_output_model(ibis_data, corner, io_type, temp_filepath, compress_threshold=1e-3)
        elif io_type == "Input":
            ret = create_input_model(ibis_data, corner, io_type, temp_filepath)
        else:
            return 1

        if ret != 0:
            return ret

        with open(temp_filepath, 'r') as file:
            spice_text = file.read()

        spice_text = convert_subcircuit_text_to_ngspice(spice_text, ibis_data, corner, io_type)

        with open(output_filepath, 'w') as file:
            file.write(spice_text)

        return 0
    finally:
        try:
            os.remove(temp_filepath)
        except OSError:
            pass


def float_or_none(value):
    """
    Converts IBIS parser numeric objects to float, preserving missing values.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def estimate_input_threshold(ibis_data, corner):
    """
    Estimates a single switching threshold for an input-driven output model.
    """
    vinl = float_or_none(getattr(ibis_data, "vinl", None))
    vinh = float_or_none(getattr(ibis_data, "vinh", None))
    if vinl is not None and vinh is not None:
        return (vinl + vinh) / 2

    _INDEX = convert_corner_str_to_index(corner)
    if ibis_data.v_range is not None and ibis_data.v_range[_INDEX] is not None:
        return float(ibis_data.v_range[_INDEX]) / 2

    return 0.5


def create_ngspice_k_lookup_source(source_name, node_name, time, k_param):
    """
    Creates a behavioral source that evaluates a waveform-derived K coefficient
    against the time since the most recent input edge.
    """
    scaled_time = time * 1e9
    table_str = convert_iv_table_to_str(scaled_time, k_param)
    last_time = float(scaled_time[-1])
    return f'{source_name} {node_name} 0 V = pwl(min(max(V(NX), 0), {last_time}), {table_str})\n'


def create_ngspice_k_lookup_source_from_arg(source_name, node_name, arg_node, time, k_param):
    """
    Creates a behavioral source that evaluates a waveform-derived K coefficient
    against a voltage-valued time argument in ns.
    """
    scaled_time = time * 1e9
    table_str = convert_iv_table_to_str(scaled_time, k_param)
    last_time = float(scaled_time[-1])
    return f'{source_name} {node_name} 0 V = pwl(min(max(V({arg_node}), 0), {last_time}), {table_str})\n'


def create_ngspice_k_lookup_source_from_elapsed(source_name, node_name, elapsed_node, time, k_param):
    """
    Creates a behavioral source that evaluates a waveform-derived K coefficient
    against a named elapsed-time node in ns.
    """
    scaled_time = time * 1e9
    table_str = convert_iv_table_to_str(scaled_time, k_param)
    last_time = float(scaled_time[-1])
    return f'{source_name} {node_name} 0 V = pwl(min(max(V({elapsed_node}), 0), {last_time}), {table_str})\n'


def inverse_time_lookup_table(time_values, values, point_count=81):
    """
    Builds a monotonic-x coefficient-to-time lookup for value-matched replay.

    IBIS-derived Ku/Kd curves are not guaranteed to be strictly monotonic, so
    duplicate/near-duplicate coefficient values are collapsed to their earliest
    table time. The result is a safe PWL x-axis in coefficient space; y is the
    matched replay time in ns.
    """
    time_ns = np.asarray(time_values, dtype=float) * 1e9
    coeff = np.asarray(values, dtype=float)
    mask = np.isfinite(time_ns) & np.isfinite(coeff)
    time_ns = time_ns[mask]
    coeff = coeff[mask]
    if len(time_ns) == 0:
        return np.asarray([0.0, 1.0]), np.asarray([0.0, 0.0])

    order = np.argsort(coeff)
    coeff = coeff[order]
    time_ns = time_ns[order]
    unique_x = []
    unique_t = []
    eps = 1.0e-9
    for value, time_value in zip(coeff, time_ns):
        value = float(value)
        time_value = float(time_value)
        if not unique_x or abs(value - unique_x[-1]) > eps:
            unique_x.append(value)
            unique_t.append(time_value)
        else:
            unique_t[-1] = min(unique_t[-1], time_value)

    if len(unique_x) == 1:
        x0 = unique_x[0]
        return np.asarray([x0 - 1e-6, x0 + 1e-6]), np.asarray([unique_t[0], unique_t[0]])

    x_min = float(unique_x[0])
    x_max = float(unique_x[-1])
    if abs(x_max - x_min) < 1e-12:
        return np.asarray([x_min - 1e-6, x_max + 1e-6]), np.asarray([unique_t[0], unique_t[-1]])

    grid = np.linspace(x_min, x_max, point_count)
    matched_time = np.interp(grid, np.asarray(unique_x), np.asarray(unique_t))
    return grid, matched_time


def create_inverse_time_lookup_source(source_name, node_name, sample_node, time, k_param):
    """
    Creates a coefficient-to-table-time behavioral lookup in ns.
    """
    inv_x, inv_t = inverse_time_lookup_table(time, k_param)
    table_str = convert_iv_table_to_str(inv_x, inv_t)
    return (
        f'{source_name} {node_name} 0 V = '
        f'pwl(min(max(V({sample_node}), {float(inv_x[0]):.16g}), {float(inv_x[-1]):.16g}), {table_str})\n'
    )


def create_ngspice_state_continuous_input_control_netlist(kr, kf, ibis_data):
    """
    Creates input-driven K-coefficient logic with a continuous transition state.

    PSTATE is a dimensionless progress variable:
        0 = settled low, 1 = settled high.
    New input edges reverse the PSTATE ramp from its current value rather than
    restarting Ku/Kd from a full-transition waveform endpoint.
    """
    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    rise_duration_ns = max(float(kr[-1, _TIME]) * 1e9, 1.0e-6)
    fall_duration_ns = max(float(kf[-1, _TIME]) * 1e9, 1.0e-6)
    rise_rate = 1.0 / (rise_duration_ns * 1e-9)
    fall_rate = 1.0 / (fall_duration_ns * 1e-9)

    st = ""
    st += "* State-continuous input-driven waveform coefficient control\n"
    st += "* PSTATE is a continuous low-to-high progress variable. Interrupted\n"
    st += "* transitions reverse from the current PSTATE instead of restarting from\n"
    st += "* a clean full-transition endpoint.\n"
    st += f".param rise_duration_ns={rise_duration_ns:.16g}\n"
    st += f".param fall_duration_ns={fall_duration_ns:.16g}\n"
    st += f".param rise_pstate_rate={rise_rate:.16g}\n"
    st += f".param fall_pstate_rate={fall_rate:.16g}\n"
    st += ".param pstate_c=1p pstate_stop_tau=1p coeff_c=1p coeff_tau=1p\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 PSTATE 0 I = -{pstate_c} * (V(NENABLE) > 0.5 ? "
    st += "((V(NINX) > 0.5) ? min(rise_pstate_rate, max((1.0 - V(PSTATE))/pstate_stop_tau, 0)) "
    st += ": -min(fall_pstate_rate, max(V(PSTATE)/pstate_stop_tau, 0))) "
    st += ": -min(fall_pstate_rate, max(V(PSTATE)/pstate_stop_tau, 0)))\n"
    st += "Cpstate PSTATE 0 {pstate_c} ic=0\n"
    st += "Rpstate PSTATE 0 1e15\n"
    st += "B13 KRARG 0 V = V(PSTATE) * rise_duration_ns\n"
    st += "B14 KFARG 0 V = (1.0 - V(PSTATE)) * fall_duration_ns\n\n"

    if ibis_data.model_type.lower() == "open_drain":
        st += "* Open-drain state-continuous mode uses Kd-only state targeting.\n"
        st += create_ngspice_k_lookup_source_from_arg("B20", "KDR0", "KRARG", kr[:, _TIME], kr[:, _KD_OD])
        st += create_ngspice_k_lookup_source_from_arg("B21", "KDF0", "KFARG", kf[:, _TIME], kf[:, _KD_OD])
        st += "B22 KDTARGET 0 V = (V(NINX) > 0.5) ? V(KDR0) : V(KDF0)\n"
        st += "B23 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
        st += "Ckd Kd 0 {coeff_c} ic=1\n"
        st += "Rkd Kd 0 1e15\n\n"
    else:
        st += create_ngspice_k_lookup_source_from_arg("B20", "KUR0", "KRARG", kr[:, _TIME], kr[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B21", "KDR0", "KRARG", kr[:, _TIME], kr[:, _KD])
        st += create_ngspice_k_lookup_source_from_arg("B22", "KUF0", "KFARG", kf[:, _TIME], kf[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B23", "KDF0", "KFARG", kf[:, _TIME], kf[:, _KD])
        st += "B24 KUTARGET 0 V = (V(NINX) > 0.5) ? V(KUR0) : V(KUF0)\n"
        st += "B25 KDTARGET 0 V = (V(NINX) > 0.5) ? V(KDR0) : V(KDF0)\n"
        st += "B26 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
        st += "Cku Ku 0 {coeff_c} ic=0\n"
        st += "Rku Ku 0 1e15\n"
        st += "B27 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
        st += "Ckd Kd 0 {coeff_c} ic=1\n"
        st += "Rkd Kd 0 1e15\n\n"

    return st


def format_spice_ns(value_ns):
    """
    Formats a nanosecond value for SPICE delay parameters.
    """
    if abs(value_ns) < 1e-15:
        return "0"
    return f"{value_ns:.12g}n"


def coefficient_event_taps(kr, kf, column, low_hint, high_hint, threshold=2e-3):
    """
    Builds independent rising/falling event-response tap weights.

    The generated SPICE uses short detected edge pulses. Each delayed tap injects
    a small charge into the target coefficient node, so a normal rising edge
    follows the rising coefficient table and a normal falling edge follows the
    falling coefficient table. If a pulse is interrupted, the still-pending
    delayed increments from both events overlap instead of either table being
    restarted from a clean endpoint.
    """
    tr = np.asarray(kr[:, _TIME], dtype=float) * 1e9
    tf = np.asarray(kf[:, _TIME], dtype=float) * 1e9
    yr = np.asarray(kr[:, column], dtype=float)
    yf = np.asarray(kf[:, column], dtype=float)

    low = float(low_hint)
    high = float(high_hint)

    def build_taps(time_ns, values, start_value, end_value):
        time_ns = np.asarray(time_ns, dtype=float)
        values = np.asarray(values, dtype=float)
        mask = np.isfinite(time_ns) & np.isfinite(values) & (time_ns >= 0)
        time_ns = time_ns[mask]
        values = values[mask]
        if len(time_ns) == 0:
            return []
        order = np.argsort(time_ns)
        time_ns = time_ns[order]
        values = values[order].copy()
        values[-1] = float(end_value)

        taps = []
        previous = float(start_value)
        pending = 0.0
        for idx, value in enumerate(values):
            pending += float(value - previous)
            previous = float(value)
            if abs(pending) >= threshold or idx == len(values) - 1:
                if abs(pending) > 1e-12:
                    taps.append((float(time_ns[idx]), pending))
                pending = 0.0
        return taps

    rise_taps = build_taps(tr, yr, low, high)
    fall_taps = build_taps(tf, yf, high, low)
    return low, high, rise_taps, fall_taps


def limit_event_taps(taps, max_taps=64):
    """
    Limits delayed event taps by merging adjacent tap groups.

    Dense IBIS waveform tables can produce hundreds of delayed sources per
    coefficient direction. That is faithful but painfully slow in ngspice. This
    keeps total charge exactly by summing weights and preserves timing by using
    an absolute-weighted average delay for each merged group.
    """
    taps = list(taps)
    if len(taps) <= max_taps:
        return taps
    max_taps = max(1, int(max_taps))
    merged = []
    edges = np.linspace(0, len(taps), max_taps + 1, dtype=int)
    for start, stop in zip(edges[:-1], edges[1:]):
        group = taps[start:stop]
        if not group:
            continue
        delays = np.asarray([item[0] for item in group], dtype=float)
        weights = np.asarray([item[1] for item in group], dtype=float)
        total = float(np.sum(weights))
        if abs(total) < 1e-15:
            continue
        denom = float(np.sum(np.abs(weights)))
        if denom < 1e-15:
            delay = float(np.mean(delays))
        else:
            delay = float(np.sum(delays * np.abs(weights)) / denom)
        merged.append((delay, total))
    return merged


def coefficient_state_endpoint_values(kr, kf, column, default_low, default_high):
    """
    Estimates low/high endpoints from the rise/fall coefficient tables.
    """
    yr = np.asarray(kr[:, column], dtype=float)
    yf = np.asarray(kf[:, column], dtype=float)
    try:
        low = float(np.nanmean([yr[0], yf[-1]]))
    except (IndexError, ValueError):
        low = float(default_low)
    try:
        high = float(np.nanmean([yr[-1], yf[0]]))
    except (IndexError, ValueError):
        high = float(default_high)
    if not np.isfinite(low):
        low = float(default_low)
    if not np.isfinite(high):
        high = float(default_high)
    return low, high


def crossing_time_ns(time_ns, progress, level):
    """
    Returns the first interpolated time where progress crosses level.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    progress = np.asarray(progress, dtype=float)
    mask = np.isfinite(time_ns) & np.isfinite(progress)
    time_ns = time_ns[mask]
    progress = progress[mask]
    if len(time_ns) == 0:
        return 0.0
    order = np.argsort(time_ns)
    time_ns = time_ns[order]
    progress = progress[order]
    for idx in range(1, len(time_ns)):
        p0 = progress[idx - 1]
        p1 = progress[idx]
        if (p0 <= level <= p1) or (p1 <= level <= p0):
            if abs(p1 - p0) < 1e-15:
                return float(time_ns[idx])
            frac = (level - p0) / (p1 - p0)
            return float(time_ns[idx - 1] + frac * (time_ns[idx] - time_ns[idx - 1]))
    return float(time_ns[-1])


def coefficient_branch_fit(kr, kf, column, low, high, branch_count=3):
    """
    Fits a compact delayed branch model for one coefficient.

    Each branch is a continuous 0..1 state driven by a delayed digital target.
    The coefficient is low + (high-low) * weighted_branch_sum. Rise/fall use
    separate time constants, so an interrupted transition reverses from the
    current branch values instead of applying a full opposite-edge table.
    """
    tr = np.asarray(kr[:, _TIME], dtype=float) * 1e9
    tf = np.asarray(kf[:, _TIME], dtype=float) * 1e9
    yr = np.asarray(kr[:, column], dtype=float)
    yf = np.asarray(kf[:, column], dtype=float)
    delta = float(high - low)
    if abs(delta) < 1e-12:
        return 0.0, 0.05, 0.05, [1.0]

    rise_progress = np.clip((yr - low) / delta, -0.5, 1.5)
    fall_progress = np.clip((yf - high) / (-delta), -0.5, 1.5)
    rise_t05 = crossing_time_ns(tr, rise_progress, 0.05)
    rise_t63 = crossing_time_ns(tr, rise_progress, 0.632)
    fall_t05 = crossing_time_ns(tf, fall_progress, 0.05)
    fall_t63 = crossing_time_ns(tf, fall_progress, 0.632)

    delay_ns = max(0.0, min(rise_t05, fall_t05))
    tau_up_ns = max(0.01, rise_t63 - delay_ns)
    tau_down_ns = max(0.01, fall_t63 - delay_ns)

    scales = np.array([0.35, 1.0, 3.0], dtype=float)
    if branch_count == 1:
        scales = np.array([1.0], dtype=float)
    elif branch_count == 2:
        scales = np.array([0.5, 2.0], dtype=float)
    elif branch_count > 3:
        scales = np.geomspace(0.25, 4.0, branch_count)

    tfit = np.maximum(0.0, tr - delay_ns)
    tau_basis = np.maximum(0.01, tau_up_ns * scales)
    basis = np.column_stack([1.0 - np.exp(-tfit / tau) for tau in tau_basis])
    target = rise_progress.copy()
    mask = np.isfinite(target) & np.all(np.isfinite(basis), axis=1)
    if np.count_nonzero(mask) >= len(scales) and len(scales) == 3:
        fit_basis = basis[mask]
        fit_target = np.clip(target[mask], 0.0, 1.0)
        grid = np.linspace(0.0, 1.0, 51)
        best_err = float("inf")
        weights = np.array([0.0, 1.0, 0.0], dtype=float)
        for w0 in grid:
            for w1 in grid:
                if w0 + w1 > 1.0:
                    continue
                trial = np.array([w0, w1, 1.0 - w0 - w1], dtype=float)
                err = float(np.mean((fit_basis @ trial - fit_target) ** 2))
                if err < best_err:
                    best_err = err
                    weights = trial
    elif np.count_nonzero(mask) >= len(scales):
        # A strong sum-to-one row keeps the final settled value reproducible.
        a = np.vstack([basis[mask], np.ones((1, len(scales))) * 20.0])
        b = np.concatenate([target[mask], [20.0]])
        weights, *_ = np.linalg.lstsq(a, b, rcond=None)
    else:
        weights = np.zeros(len(scales), dtype=float)
        weights[0] = 1.0
    if not np.all(np.isfinite(weights)):
        weights = np.zeros(len(scales), dtype=float)
        weights[0] = 1.0

    return delay_ns, tau_up_ns, tau_down_ns, [float(w) for w in weights]


def coefficient_progress(time_values, values, start_value, end_value):
    """
    Normalizes a coefficient waveform to 0..1 transition progress.
    """
    time_ns = np.asarray(time_values, dtype=float) * 1e9
    values = np.asarray(values, dtype=float)
    delta = float(end_value - start_value)
    if abs(delta) < 1e-15:
        progress = np.zeros_like(values)
    else:
        progress = (values - start_value) / delta
    return time_ns, np.clip(progress, -0.5, 1.5)


def coefficient_onset_delay_ns(time_values, values, start_value, end_value, level=0.05):
    """
    Estimates the first meaningful coefficient movement from an IBIS-derived
    coefficient table.
    """
    time_ns, progress = coefficient_progress(time_values, values, start_value, end_value)
    return crossing_time_ns(time_ns, progress, level)


def coefficient_main_slope_delay_ns(time_values, values, start_value, end_value):
    """
    Estimates onset by projecting the maximum-slope region back to the starting
    coefficient value. This is still Touchstone/IBIS-table local and does not
    use any HSPICE result.
    """
    time_ns = np.asarray(time_values, dtype=float) * 1e9
    values = np.asarray(values, dtype=float)
    mask = np.isfinite(time_ns) & np.isfinite(values)
    time_ns = time_ns[mask]
    values = values[mask]
    if len(time_ns) < 2:
        return 0.0
    order = np.argsort(time_ns)
    time_ns = time_ns[order]
    values = values[order]
    dt = np.diff(time_ns)
    dy = np.diff(values)
    valid = dt > 1e-15
    if not np.any(valid):
        return 0.0
    slopes = np.zeros_like(dy)
    slopes[valid] = dy[valid] / dt[valid]
    idx = int(np.argmax(np.abs(slopes)))
    slope = slopes[idx]
    if abs(slope) < 1e-15:
        return coefficient_onset_delay_ns(time_values, values, start_value, end_value)
    t_mid = 0.5 * (time_ns[idx] + time_ns[idx + 1])
    y_mid = 0.5 * (values[idx] + values[idx + 1])
    onset = t_mid + (float(start_value) - y_mid) / slope
    return float(max(0.0, min(onset, time_ns[-1])))


def short_pulse_window_ns(kr, kf):
    """
    Derives the short-pulse detector window from IBIS coefficient table length.
    Long normal pulses should not enter hybrid correction; interrupted pulses
    shorter than roughly the first third of the coefficient response should.
    """
    rise_duration = float(np.nanmax(np.asarray(kr[:, _TIME], dtype=float))) * 1e9
    fall_duration = float(np.nanmax(np.asarray(kf[:, _TIME], dtype=float))) * 1e9
    duration = max(0.1, min(rise_duration, fall_duration))
    return max(0.25, min(5.0, 0.35 * duration))


def hybrid_adjusted_delays(kr, kf, ku_low, ku_high, kd_low, kd_high, strategy):
    """
    Returns Ku/Kd correction delays for the selected short-pulse estimator.
    """
    ku_branch_delay, ku_tau_up, ku_tau_down, ku_weights = coefficient_branch_fit(
        kr, kf, _KU, ku_low, ku_high, branch_count=3
    )
    kd_branch_delay, kd_tau_up, kd_tau_down, kd_weights = coefficient_branch_fit(
        kr, kf, _KD, kd_low, kd_high, branch_count=3
    )
    if strategy == "main_slope":
        ku_delay = coefficient_main_slope_delay_ns(kr[:, _TIME], kr[:, _KU], ku_low, ku_high)
        kd_delay = coefficient_main_slope_delay_ns(kr[:, _TIME], kr[:, _KD], kd_low, kd_high)
    elif strategy == "constrained":
        ku_onset = coefficient_onset_delay_ns(kr[:, _TIME], kr[:, _KU], ku_low, ku_high)
        kd_onset = coefficient_onset_delay_ns(kr[:, _TIME], kr[:, _KD], kd_low, kd_high)
        ku_delay = max(ku_branch_delay, kd_onset, ku_onset)
        kd_delay = kd_branch_delay
    else:
        ku_delay = ku_branch_delay
        kd_delay = kd_branch_delay
    return (
        ku_delay,
        ku_tau_up,
        ku_tau_down,
        ku_weights,
        kd_delay,
        kd_tau_up,
        kd_tau_down,
        kd_weights,
    )


def coefficient_transition_timing(time_values, values, start_value, end_value):
    """
    Estimates onset and time constants for a coefficient transition.
    """
    time_ns, progress = coefficient_progress(time_values, values, start_value, end_value)
    t05 = crossing_time_ns(time_ns, progress, 0.05)
    t63 = crossing_time_ns(time_ns, progress, 0.632)
    t90 = crossing_time_ns(time_ns, progress, 0.90)
    delay = max(0.0, t05)
    tau = max(0.02, t63 - delay)
    if t90 > delay:
        tau = max(tau, (t90 - delay) / 2.302585093)
    return delay, tau


def gate_response(time_ns, delay_ns, tau_ns, start_value, end_value):
    """
    Evaluates a single-pole hidden gate state for transfer-curve fitting.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    x = np.maximum(0.0, time_ns - float(delay_ns))
    progress = 1.0 - np.exp(-x / max(float(tau_ns), 0.02))
    return float(start_value) + (float(end_value) - float(start_value)) * progress


def gate_transfer_curve(rise_time, rise_values, fall_time, fall_values,
                        rise_delay_ns, rise_tau_ns, fall_delay_ns, fall_tau_ns,
                        low, high, point_count=41):
    """
    Builds a monotonic coefficient-vs-gate-state map from complete-edge tables.
    """
    tr = np.asarray(rise_time, dtype=float) * 1e9
    tf = np.asarray(fall_time, dtype=float) * 1e9
    yr = np.asarray(rise_values, dtype=float)
    yf = np.asarray(fall_values, dtype=float)
    gr = gate_response(tr, rise_delay_ns, rise_tau_ns, 0.0, 1.0)
    gf = gate_response(tf, fall_delay_ns, fall_tau_ns, 1.0, 0.0)

    g = np.concatenate([gr, gf, [0.0, 1.0]])
    y = np.concatenate([yr, yf, [low, high]])
    mask = np.isfinite(g) & np.isfinite(y)
    g = np.clip(g[mask], 0.0, 1.0)
    y = y[mask]
    order = np.argsort(g)
    g = g[order]
    y = y[order]
    grid = np.linspace(0.0, 1.0, point_count)
    mapped = np.interp(grid, g, y)
    mapped[0] = float(low)
    mapped[-1] = float(high)
    mapped = np.maximum.accumulate(mapped)
    mapped[0] = float(low)
    mapped[-1] = max(float(high), mapped[-1])
    return grid, mapped


def gate_state_fit(kr, kf):
    """
    Fits a compact hidden-gate-state model from IBIS-derived Ku/Kd tables.
    """
    ku_off = float(np.nanmean([kr[0, _KU], kf[-1, _KU]]))
    ku_on = float(np.nanmean([kr[-1, _KU], kf[0, _KU]]))
    kd_on = float(np.nanmean([kr[0, _KD], kf[-1, _KD]]))
    kd_off = float(np.nanmean([kr[-1, _KD], kf[0, _KD]]))
    if not np.isfinite(ku_off):
        ku_off = 0.0
    if not np.isfinite(ku_on):
        ku_on = 1.0
    if not np.isfinite(kd_on):
        kd_on = 1.0
    if not np.isfinite(kd_off):
        kd_off = 0.0

    pu_on_delay, pu_on_tau = coefficient_transition_timing(kr[:, _TIME], kr[:, _KU], ku_off, ku_on)
    pu_off_delay, pu_off_tau = coefficient_transition_timing(kf[:, _TIME], kf[:, _KU], ku_on, ku_off)
    pd_off_delay, pd_off_tau = coefficient_transition_timing(kr[:, _TIME], kr[:, _KD], kd_on, kd_off)
    pd_on_delay, pd_on_tau = coefficient_transition_timing(kf[:, _TIME], kf[:, _KD], kd_off, kd_on)

    ku_x, ku_y = gate_transfer_curve(
        kr[:, _TIME],
        kr[:, _KU],
        kf[:, _TIME],
        kf[:, _KU],
        pu_on_delay,
        pu_on_tau,
        pu_off_delay,
        pu_off_tau,
        ku_off,
        ku_on,
    )
    kd_x, kd_y = gate_transfer_curve(
        kf[:, _TIME],
        kf[:, _KD],
        kr[:, _TIME],
        kr[:, _KD],
        pd_on_delay,
        pd_on_tau,
        pd_off_delay,
        pd_off_tau,
        kd_off,
        kd_on,
    )

    return {
        "ku_off": ku_off,
        "ku_on": ku_on,
        "kd_off": kd_off,
        "kd_on": kd_on,
        "pu_on_delay": pu_on_delay,
        "pu_off_delay": pu_off_delay,
        "pd_on_delay": pd_on_delay,
        "pd_off_delay": pd_off_delay,
        "pu_on_tau": pu_on_tau,
        "pu_off_tau": pu_off_tau,
        "pd_on_tau": pd_on_tau,
        "pd_off_tau": pd_off_tau,
        "ku_map_x": ku_x,
        "ku_map_y": ku_y,
        "kd_map_x": kd_x,
        "kd_map_y": kd_y,
        "interrupt_window_ns": short_pulse_window_ns(kr, kf),
    }


def gate_state_rate(time_ns, delay_ns, tau_ns, start_value, end_value):
    """
    Returns d(gate_state)/dt in state/ns for the fitted single-pole state.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    tau_ns = max(float(tau_ns), 0.02)
    x = np.asarray(time_ns, dtype=float) - float(delay_ns)
    rate = np.zeros_like(x, dtype=float)
    active = x >= 0.0
    rate[active] = (float(end_value) - float(start_value)) * np.exp(-x[active] / tau_ns) / tau_ns
    return rate


def directional_gate_transfer_curve(time_values, values, delay_ns, tau_ns, start_gate, end_gate,
                                    low, high, point_count=81):
    """
    Builds a direction-specific coefficient-vs-gate-state map.

    The x-axis is still the normalized hidden gate state, but unlike
    gate_transfer_curve this helper does not force y to be monotonic. That is
    intentional: io_buf Kd has a real undershoot in the complete-edge table,
    and forcing a nonnegative monotonic map erases the failure mode we need to
    preserve and measure.
    """
    t_ns = np.asarray(time_values, dtype=float) * 1e9
    y = np.asarray(values, dtype=float)
    g = gate_response(t_ns, delay_ns, tau_ns, start_gate, end_gate)
    mask = np.isfinite(g) & np.isfinite(y)
    g = np.clip(g[mask], 0.0, 1.0)
    y = y[mask]
    if len(g) < 2:
        grid = np.linspace(0.0, 1.0, point_count)
        return grid, low + (high - low) * grid
    order = np.argsort(g)
    g = g[order]
    y = y[order]
    rounded = np.round(g, 12)
    unique_g = []
    unique_y = []
    for value in np.unique(rounded):
        same = rounded == value
        unique_g.append(float(np.mean(g[same])))
        unique_y.append(float(np.mean(y[same])))
    unique_g = np.asarray(unique_g, dtype=float)
    unique_y = np.asarray(unique_y, dtype=float)
    if len(unique_g) < 2:
        grid = np.linspace(0.0, 1.0, point_count)
        return grid, low + (high - low) * grid
    grid = np.linspace(0.0, 1.0, point_count)
    mapped = np.interp(grid, unique_g, unique_y)
    mapped[0] = float(low)
    mapped[-1] = float(high)
    return grid, mapped


def two_state_directional_gate_fit(kr, kf):
    """
    Fits separate on/off gate maps plus a Kd rate residual candidate.
    """
    fit = dict(gate_state_fit(kr, kf))
    tr = np.asarray(kr[:, _TIME], dtype=float) * 1e9
    tf = np.asarray(kf[:, _TIME], dtype=float) * 1e9

    ku_on_x, ku_on_y = directional_gate_transfer_curve(
        kr[:, _TIME], kr[:, _KU], fit["pu_on_delay"], fit["pu_on_tau"], 0.0, 1.0,
        fit["ku_off"], fit["ku_on"]
    )
    ku_off_x, ku_off_y = directional_gate_transfer_curve(
        kf[:, _TIME], kf[:, _KU], fit["pu_off_delay"], fit["pu_off_tau"], 1.0, 0.0,
        fit["ku_off"], fit["ku_on"]
    )
    kd_off_x, kd_off_y = directional_gate_transfer_curve(
        kr[:, _TIME], kr[:, _KD], fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0,
        fit["kd_off"], fit["kd_on"]
    )
    kd_on_x, kd_on_y = directional_gate_transfer_curve(
        kf[:, _TIME], kf[:, _KD], fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0,
        fit["kd_off"], fit["kd_on"]
    )

    gdn_rise = gate_response(tr, fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0)
    gdn_fall = gate_response(tf, fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0)
    kd_rise_base = np.interp(gdn_rise, kd_off_x, kd_off_y)
    kd_fall_base = np.interp(gdn_fall, kd_on_x, kd_on_y)
    kd_rise_residual = np.asarray(kr[:, _KD], dtype=float) - kd_rise_base
    kd_fall_residual = np.asarray(kf[:, _KD], dtype=float) - kd_fall_base
    kd_residual = np.concatenate([
        kd_rise_residual,
        kd_fall_residual,
    ])
    kd_rate = np.concatenate([
        gate_state_rate(tr, fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0),
        gate_state_rate(tf, fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0),
    ])
    mask = np.isfinite(kd_residual) & np.isfinite(kd_rate) & (np.abs(kd_rate) > 1e-6)
    denom = float(np.dot(kd_rate[mask], kd_rate[mask])) if np.any(mask) else 0.0
    kd_rate_gain_ns = float(np.dot(kd_rate[mask], kd_residual[mask]) / denom) if denom > 1e-18 else 0.0
    if not np.isfinite(kd_rate_gain_ns):
        kd_rate_gain_ns = 0.0

    fit.update({
        "ku_on_map_x": ku_on_x,
        "ku_on_map_y": ku_on_y,
        "ku_off_map_x": ku_off_x,
        "ku_off_map_y": ku_off_y,
        "kd_off_map_x": kd_off_x,
        "kd_off_map_y": kd_off_y,
        "kd_on_map_x": kd_on_x,
        "kd_on_map_y": kd_on_y,
        "kd_rise_residual": kd_rise_residual,
        "kd_fall_residual": kd_fall_residual,
        "kd_rate_gain_ns": kd_rate_gain_ns,
    })
    return fit


def append_delayed_logic_source(st, name, source_expr, delay_ns):
    """
    Adds a delayed logic source using a T-line and returns the delayed node.
    """
    source_node = f"{name}SRC"
    raw_node = f"{name}RAW"
    st += f"B{name}SRC {source_node} 0 V = {source_expr}\n"
    if delay_ns <= 1e-15:
        return st, source_node
    st += f"T{name} {source_node} 0 {raw_node} 0 Z0=50 Td={format_spice_ns(delay_ns)}\n"
    st += f"R{name} {raw_node} 0 50\n"
    return st, raw_node


def append_delayed_level_source(st, name, source_node, delay_ns):
    """
    Adds a delayed copy of an existing logic-level node and returns the node.
    """
    if delay_ns <= 1e-15:
        st += f"B{name} {name} 0 V = V({source_node})\n"
        return st, name
    raw_node = f"{name}RAW"
    st += f"T{name} {source_node} 0 {raw_node} 0 Z0=50 Td={format_spice_ns(delay_ns)}\n"
    st += f"R{name} {raw_node} 0 50\n"
    st += f"B{name} {name} 0 V = V({raw_node})\n"
    return st, name


def append_logic_latch(st, name, initial_value, set_expr, reset_expr):
    """
    Adds a soft capacitor-backed logic latch.

    The latch changes continuously over edge_delay, so diagnostic flags avoid
    algebraic jumps while still acting like set/reset latches at transient scale.
    """
    set_node = f"{name}SET"
    reset_node = f"{name}RESET"
    st += f"B{set_node} {set_node} 0 V = {set_expr}\n"
    st += f"B{reset_node} {reset_node} 0 V = {reset_expr}\n"
    st += f"C{name} {name} 0 {{latch_c}} ic={float(initial_value):.16g}\n"
    st += f"R{name} {name} 0 1e15\n"
    st += (
        f"B{name}SETI {name} 0 I = "
        f"-{{latch_c}} * V({set_node}) * max(1.0 - V({name}), 0) / edge_delay\n"
    )
    st += (
        f"B{name}RESETI {name} 0 I = "
        f"{{latch_c}} * V({reset_node}) * max(V({name}), 0) / edge_delay\n"
    )
    return st


def smoothstep_expr(node_expr, low, high):
    """
    Returns a bounded linear gate expression for non-overlap shaping.
    """
    span = max(float(high) - float(low), 1e-9)
    return f"min(max(({node_expr} - {float(low):.16g})/{span:.16g}, 0), 1)"


def append_coeff_branch_state(st, name, source_node, low, high, delay_ns, tau_up_ns, tau_down_ns, weights):
    """
    Adds delayed-target branch states and returns a weighted expression.
    """
    raw_node = f"{name}CMDRAW"
    cmd_node = f"{name}CMD"
    if delay_ns <= 1e-15:
        st += f"B{name}CMD {cmd_node} 0 V = (V(NENABLE) > 0.5) ? V({source_node}) : 0.0\n"
    else:
        st += f"T{name}CMD {source_node} 0 {raw_node} 0 Z0=50 Td={format_spice_ns(delay_ns)}\n"
        st += f"R{name}CMD {raw_node} 0 50\n"
        st += f"B{name}CMD {cmd_node} 0 V = (V(NENABLE) > 0.5) ? V({raw_node}) : 0.0\n"

    terms = []
    for idx, weight in enumerate(weights, start=1):
        branch = f"{name}X{idx}"
        tau_up = max(0.01, tau_up_ns * ([0.35, 1.0, 3.0][idx - 1] if len(weights) == 3 else 1.0))
        tau_down = max(0.01, tau_down_ns * ([0.35, 1.0, 3.0][idx - 1] if len(weights) == 3 else 1.0))
        st += (
            f"B{name}X{idx} {branch} 0 I = -{{coeff_c}} * (V({cmd_node}) - V({branch})) / "
            f"((V({cmd_node}) > V({branch})) ? {format_spice_ns(tau_up)} : {format_spice_ns(tau_down)})\n"
        )
        st += f"C{name}X{idx} {branch} 0 {{coeff_c}} ic=0\n"
        st += f"R{name}X{idx} {branch} 0 1e12\n"
        terms.append((weight, branch))

    expr = f"{low:.16g}"
    delta = high - low
    for weight, branch in terms:
        sign = "+" if delta * weight >= 0 else "-"
        expr += f" {sign} {abs(delta * weight):.16g}*V({branch})"
    return st, expr


def append_coeff_state_delay_lines(st, prefix, source_node, taps):
    """
    Adds T-line delayed copies of an edge pulse and returns current-injection
    terms for the target coefficient state.
    """
    terms = []
    for idx, (delay_ns, weight) in enumerate(taps, start=1):
        if abs(delay_ns) < 1e-15:
            node = source_node
        else:
            node = f"{prefix}D{idx}"
            st += f"T{prefix}{idx} {source_node} 0 {node} 0 Z0=50 Td={format_spice_ns(delay_ns)}\n"
            st += f"R{prefix}{idx} {node} 0 50\n"
        terms.append((weight, node))
    return st, terms


def append_coeff_target_state(st, name, node_name, base, terms):
    """
    Writes a capacitor-backed target coefficient node. Delayed edge pulses add
    or remove charge, producing a held target that follows the independent rise
    and fall coefficient tables without using elapsed-time restarts.
    """
    base_node = f"{name}BASE"
    st += f"B{name}BASE {base_node} 0 V = {base:.16g}\n"
    st += f"C{name}T {node_name} 0 {{coeff_c}} ic={base:.16g}\n"
    st += f"R{name}T {node_name} {base_node} 1e12\n"
    for idx, (weight, pulse_node) in enumerate(terms, start=1):
        st += (
            f"B{name}T{idx} {node_name} 0 I = "
            f"-{{coeff_c}} * ({weight:.16g}) * V({pulse_node}) / edge_delay\n"
        )
    return st


def create_ngspice_coeff_state_input_control_netlist(kr, kf, ibis_data):
    """
    Creates coefficient-state input control using delayed branch states.

    Ku/Kd are independent states. Each coefficient has a delayed digital target
    and a small fitted branch basis derived only from the IBIS waveform
    coefficient tables. The branches reverse from their current values when an
    opposite edge arrives, so interrupted pulses remain continuous and partial.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenCoeffState v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    ku_low, ku_high = coefficient_state_endpoint_values(kr, kf, _KU, 0.0, 1.0)
    kd_low, kd_high = coefficient_state_endpoint_values(kr, kf, _KD, 1.0, 0.0)
    ku_delay, ku_tau_up, ku_tau_down, ku_weights = coefficient_branch_fit(kr, kf, _KU, ku_low, ku_high, branch_count=3)
    kd_delay, kd_tau_up, kd_tau_down, kd_weights = coefficient_branch_fit(kr, kf, _KD, kd_low, kd_high, branch_count=3)

    st = ""
    st += "* Coefficient-state input-driven waveform coefficient control\n"
    st += "* Ku and Kd are independent continuous states. KUTARGET/KDTARGET are\n"
    st += "* fitted delayed branch-basis responses derived from IBIS coefficient tables.\n"
    st += "* Interrupted pulses reverse branch states from their current values.\n"
    st += ".param coeff_c=1p coeff_tau=1p\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += (
        f"* Ku branch fit: delay={ku_delay:.6g}ns tau_up={ku_tau_up:.6g}ns "
        f"tau_down={ku_tau_down:.6g}ns weights={','.join(f'{w:.6g}' for w in ku_weights)}\n"
    )
    st += (
        f"* Kd branch fit: delay={kd_delay:.6g}ns tau_up={kd_tau_up:.6g}ns "
        f"tau_down={kd_tau_down:.6g}ns weights={','.join(f'{w:.6g}' for w in kd_weights)}\n"
    )
    st, ku_expr = append_coeff_branch_state(st, "KU", "NINX", ku_low, ku_high, ku_delay, ku_tau_up, ku_tau_down, ku_weights)
    st, kd_expr = append_coeff_branch_state(st, "KD", "NINX", kd_low, kd_high, kd_delay, kd_tau_up, kd_tau_down, kd_weights)
    st += f"B20 KUTARGET 0 V = {ku_expr}\n"
    st += f"B21 KDTARGET 0 V = {kd_expr}\n"
    st += "B22 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={ku_low:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B23 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={kd_low:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_short_pulse_hybrid_input_control_netlist(kr, kf, ibis_data, strategy="branch"):
    """
    Creates an experimental short-pulse-only hybrid control.

    The generated subcircuit runs legacy elapsed-time Ku/Kd and a continuous
    correction-state model in parallel. Final Ku/Kd follow legacy unless a short
    high pulse is detected: input falls while the measured high duration is
    still inside an IBIS-derived retrigger window. In that case final Ku/Kd
    smoothly retarget to the correction states.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenShortPulseHybrid v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    ku_low, ku_high = coefficient_state_endpoint_values(kr, kf, _KU, 0.0, 1.0)
    kd_low, kd_high = coefficient_state_endpoint_values(kr, kf, _KD, 1.0, 0.0)
    (
        ku_delay,
        ku_tau_up,
        ku_tau_down,
        ku_weights,
        kd_delay,
        kd_tau_up,
        kd_tau_down,
        kd_weights,
    ) = hybrid_adjusted_delays(kr, kf, ku_low, ku_high, kd_low, kd_high, strategy)
    detector_window_ns = short_pulse_window_ns(kr, kf)

    st = ""
    st += "* Short-pulse hybrid input-driven waveform coefficient control\n"
    st += "* Legacy elapsed-time Ku/Kd remain the normal path. HSHORT activates only\n"
    st += "* when a high pulse falls before the IBIS-derived retrigger window expires.\n"
    st += f"* Hybrid delay strategy: {strategy}\n"
    st += f".param coeff_c=1p coeff_tau=1p short_pulse_window_ns={detector_window_ns:.16g} high_age_c=1p\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += (
        f"* Correction Ku branch fit: delay={ku_delay:.6g}ns tau_up={ku_tau_up:.6g}ns "
        f"tau_down={ku_tau_down:.6g}ns weights={','.join(f'{w:.6g}' for w in ku_weights)}\n"
    )
    st += (
        f"* Correction Kd branch fit: delay={kd_delay:.6g}ns tau_up={kd_tau_up:.6g}ns "
        f"tau_down={kd_tau_down:.6g}ns weights={','.join(f'{w:.6g}' for w in kd_weights)}\n"
    )
    st, ku_expr = append_coeff_branch_state(st, "SPKU", "NINX", ku_low, ku_high, ku_delay, ku_tau_up, ku_tau_down, ku_weights)
    st, kd_expr = append_coeff_branch_state(st, "SPKD", "NINX", kd_low, kd_high, kd_delay, kd_tau_up, kd_tau_down, kd_weights)
    st += f"B30 KUCOR 0 V = {ku_expr}\n"
    st += f"B31 KDCOR 0 V = {kd_expr}\n\n"

    st += "* Short-high-pulse detector. HIGHAGE is measured in ns.\n"
    st += "B40 HIGHAGE 0 I = -{high_age_c} * ((V(NENABLE) > 0.5 && V(NINX) > 0.5) ? 1e9 : 0.0)\n"
    st += "Chighage HIGHAGE 0 {high_age_c} ic=0\n"
    st += "Rhighage HIGHAGE 0 1e15\n"
    st += "B41 HSHORTRAW 0 V = (V(NENABLE) > 0.5 && V(NINX) < 0.5 && V(HIGHAGE) > 0.01 && V(HIGHAGE) < short_pulse_window_ns) ? 1.0 : 0.0\n"
    st += "B42 HSHORT 0 V = V(HSHORTRAW)\n\n"

    st += "B43 KUTARGET 0 V = (V(HSHORT) > 0.5) ? V(KUCOR) : V(KULEG)\n"
    st += "B44 KDTARGET 0 V = (V(HSHORT) > 0.5) ? V(KDCOR) : V(KDLEG)\n"
    st += "B45 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={ku_low:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B46 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={kd_low:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_gate_state_input_control_netlist(kr, kf, ibis_data, mode="hybrid"):
    """
    Creates transistor-like hidden-gate-state input control.

    GUP/GDN are continuous predriver/gate-drive states. KUGATE/KDGATE are
    monotonic coefficient maps from those states. In hybrid mode, final Ku/Kd
    use the gate-state coefficients only for interrupted short-high pulses;
    otherwise they follow legacy elapsed-time pybis coefficients.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenGateState v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    fit = gate_state_fit(kr, kf)
    ku_table = convert_iv_table_to_str(fit["ku_map_x"], fit["ku_map_y"])
    kd_table = convert_iv_table_to_str(fit["kd_map_x"], fit["kd_map_y"])
    pu_allow = smoothstep_expr("1.0 - V(GDN)", 0.15, 0.75)
    pd_allow = smoothstep_expr("1.0 - V(GUP)", 0.15, 0.85)

    st = ""
    st += "* Gate-state input-driven waveform coefficient control\n"
    st += "* GUP/GDN are continuous pullup/pulldown gate-drive states. KUGATE/KDGATE\n"
    st += "* are monotonic maps from gate state to effective IBIS coefficients.\n"
    st += f"* Gate-state mode: {mode}\n"
    st += (
        f"* PU on/off delay={fit['pu_on_delay']:.6g}/{fit['pu_off_delay']:.6g}ns "
        f"tau={fit['pu_on_tau']:.6g}/{fit['pu_off_tau']:.6g}ns\n"
    )
    st += (
        f"* PD on/off delay={fit['pd_on_delay']:.6g}/{fit['pd_off_delay']:.6g}ns "
        f"tau={fit['pd_on_tau']:.6g}/{fit['pd_off_tau']:.6g}ns\n"
    )
    st += f".param coeff_c=1p coeff_tau=5p gate_c=1p high_age_c=1p gate_interrupt_window_ns={fit['interrupt_window_ns']:.16g}\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    for name, source, delay in [
        ("PUONP", "RISEEDGE", fit["pu_on_delay"]),
        ("PUOFFP", "FALLEDGE", fit["pu_off_delay"]),
        ("PDOFFP", "RISEEDGE", fit["pd_off_delay"]),
        ("PDONP", "FALLEDGE", fit["pd_on_delay"]),
    ]:
        if delay <= 1e-15:
            st += f"B{name} {name} 0 V = V({source})\n"
        else:
            st += f"T{name} {source} 0 {name} 0 Z0=50 Td={format_spice_ns(delay)}\n"
            st += f"R{name} {name} 0 50\n"
    st += "CGUPCMD GUPCMD 0 {gate_c} ic=0\n"
    st += "RGUPCMD GUPCMD 0 1e15\n"
    st += "BGUPCMDON GUPCMD 0 I = -{gate_c} * V(PUONP) / edge_delay\n"
    st += "BGUPCMDOFF GUPCMD 0 I = {gate_c} * V(PUOFFP) / edge_delay\n"
    st += "CGDNCMD GDNCMD 0 {gate_c} ic=1\n"
    st += "BGDNCMDBASE GDNCMDBASE 0 V = 1.0\n"
    st += "RGDNCMD GDNCMD GDNCMDBASE 1e15\n"
    st += "BGDNCMDOFF GDNCMD 0 I = {gate_c} * V(PDOFFP) / edge_delay\n"
    st += "BGDNCMDON GDNCMD 0 I = -{gate_c} * V(PDONP) / edge_delay\n"
    st += "BGUPTARGET GUPTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(GUPCMD), 0), 1) : 0.0\n"
    st += "BGDNTARGET GDNTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(GDNCMD), 0), 1) : 0.0\n"
    st += (
        f"BGUP GUP 0 I = -{{gate_c}} * (V(GUPTARGET) - V(GUP)) / "
        f"((V(GUPTARGET) > V(GUP)) ? {format_spice_ns(fit['pu_on_tau'])} : {format_spice_ns(fit['pu_off_tau'])})\n"
    )
    st += "CGUP GUP 0 {gate_c} ic=0\n"
    st += "RGUP GUP 0 1e12\n"
    st += (
        f"BGDN GDN 0 I = -{{gate_c}} * (V(GDNTARGET) - V(GDN)) / "
        f"((V(GDNTARGET) > V(GDN)) ? {format_spice_ns(fit['pd_on_tau'])} : {format_spice_ns(fit['pd_off_tau'])})\n"
    )
    st += "CGDN GDN 0 {gate_c} ic=1\n"
    st += "BGDNBASE GDNBASE 0 V = 1.0\n"
    st += "RGDN GDN GDNBASE 1e12\n\n"

    st += f"BKUGATERAW KUGATERAW 0 V = pwl(min(max(V(GUP), 0), 1), {ku_table})\n"
    st += f"BKDGATERAW KDGATERAW 0 V = pwl(min(max(V(GDN), 0), 1), {kd_table})\n"
    st += f"BKUGATE KUGATE 0 V = V(KUGATERAW) * ({pu_allow})\n"
    st += f"BKDGATE KDGATE 0 V = V(KDGATERAW) * (0.85 + 0.15*({pd_allow}))\n"
    st += "BOVERLAP KOVERLAP 0 V = max(V(KUGATE), 0) * max(V(KDGATE), 0)\n\n"

    st += "* Interrupted high-pulse detector. HIGHAGE is measured in ns.\n"
    st += "B40 HIGHAGE 0 I = -{high_age_c} * ((V(NENABLE) > 0.5 && V(NINX) > 0.5) ? 1e9 : 0.0)\n"
    st += "Chighage HIGHAGE 0 {high_age_c} ic=0\n"
    st += "Rhighage HIGHAGE 0 1e15\n"
    st += "B41 HINTERRUPT 0 V = (V(NENABLE) > 0.5 && V(NINX) < 0.5 && V(HIGHAGE) > 0.01 && V(HIGHAGE) < gate_interrupt_window_ns) ? 1.0 : 0.0\n\n"

    if mode == "full":
        st += "B42 KUTARGET 0 V = V(KUGATE)\n"
        st += "B43 KDTARGET 0 V = V(KDGATE)\n"
    else:
        st += "B42 KUTARGET 0 V = (V(HINTERRUPT) > 0.5) ? V(KUGATE) : V(KULEG)\n"
        st += "B43 KDTARGET 0 V = (V(HINTERRUPT) > 0.5) ? V(KDGATE) : V(KDLEG)\n"
    st += "B44 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={fit['ku_off']:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B45 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={fit['kd_on']:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def append_directional_event_state(st, name, node_name, terms):
    """
    Adds a capacitor-backed directional contribution state.

    The node stores only one direction's coefficient contribution. For example,
    KU_ON accumulates delayed rising-edge Ku increments, while KU_OFF accumulates
    delayed falling-edge Ku decrements. The final coefficient is composed from
    the low-state endpoint plus the independent directional states.
    """
    st += f"C{name} {node_name} 0 {{coeff_c}} ic=0\n"
    st += f"R{name} {node_name} 0 1e15\n"
    for idx, (weight, pulse_node) in enumerate(terms, start=1):
        st += (
            f"B{name}{idx} {node_name} 0 I = "
            f"-{{coeff_c}} * ({weight:.16g}) * V({pulse_node}) / edge_delay\n"
        )
    return st


def create_ngspice_directional_gate_state_input_control_netlist(kr, kf, ibis_data, mode="hybrid"):
    """
    Creates directional interrupted-switching coefficient control.

    Ku turn-on, Ku turn-off, Kd turn-off, and Kd turn-on are four independent
    continuous contribution states. Normal operation follows legacy InputDriven
    Ku/Kd. In hybrid mode, the directional states are blended in only when a
    short high or short low pulse is detected.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenDirectionalGateState v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    ku_low, ku_high = coefficient_state_endpoint_values(kr, kf, _KU, 0.0, 1.0)
    kd_low, kd_high = coefficient_state_endpoint_values(kr, kf, _KD, 1.0, 0.0)
    _, _, ku_rise_taps, ku_fall_taps = coefficient_event_taps(kr, kf, _KU, ku_low, ku_high, threshold=0.01)
    _, _, kd_rise_taps, kd_fall_taps = coefficient_event_taps(kr, kf, _KD, kd_low, kd_high, threshold=0.01)
    ku_rise_taps = limit_event_taps(ku_rise_taps, max_taps=16)
    ku_fall_taps = limit_event_taps(ku_fall_taps, max_taps=16)
    kd_rise_taps = limit_event_taps(kd_rise_taps, max_taps=16)
    kd_fall_taps = limit_event_taps(kd_fall_taps, max_taps=16)
    detector_window_ns = short_pulse_window_ns(kr, kf)

    st = ""
    st += "* Directional gate-state input-driven waveform coefficient control\n"
    st += "* KU_ON/KU_OFF/KD_OFF/KD_ON are independent delayed event-contribution states.\n"
    st += "* Hybrid mode follows legacy Ku/Kd except during interrupted high/low pulses.\n"
    st += f"* Directional mode: {mode}\n"
    st += (
        f"* Tap counts: KU_ON={len(ku_rise_taps)} KU_OFF={len(ku_fall_taps)} "
        f"KD_OFF={len(kd_rise_taps)} KD_ON={len(kd_fall_taps)}\n"
    )
    st += f".param coeff_c=1p coeff_tau=5p age_c=1p align_tau=5p directional_window_ns={detector_window_ns:.16g}\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    st, ku_on_terms = append_coeff_state_delay_lines(st, "KUON", "RISEEDGE", ku_rise_taps)
    st, ku_off_terms = append_coeff_state_delay_lines(st, "KUOFF", "FALLEDGE", ku_fall_taps)
    st, kd_off_terms = append_coeff_state_delay_lines(st, "KDOFF", "RISEEDGE", kd_rise_taps)
    st, kd_on_terms = append_coeff_state_delay_lines(st, "KDON", "FALLEDGE", kd_fall_taps)
    st = append_directional_event_state(st, "KUON", "KU_ON", ku_on_terms)
    st = append_directional_event_state(st, "KUOFF", "KU_OFF", ku_off_terms)
    st = append_directional_event_state(st, "KDOFF", "KD_OFF", kd_off_terms)
    st = append_directional_event_state(st, "KDON", "KD_ON", kd_on_terms)
    st += f"BKUDIR KUDIR 0 V = {ku_low:.16g} + V(KU_ON) + V(KU_OFF)\n"
    st += f"BKDDIR KDDIR 0 V = {kd_low:.16g} + V(KD_OFF) + V(KD_ON)\n"
    st += "BKOVERLAP KOVERLAP 0 V = max(V(KUDIR), 0) * max(V(KDDIR), 0)\n\n"

    st += "* Pulse-age tracking. HIGHAGE is reset on rising edges; LOWAGE is reset on falling edges.\n"
    st += "BHIGHAGE HIGHAGE 0 I = -{age_c} * ((V(NENABLE) > 0.5 && V(NINX) > 0.5) ? 1e9 : 0.0)\n"
    st += "BHIGHRESET HIGHAGE 0 I = {age_c} * V(RISEEDGE) * V(HIGHAGE) / edge_delay\n"
    st += "Chighage HIGHAGE 0 {age_c} ic=0\n"
    st += "Rhighage HIGHAGE 0 1e15\n"
    st += "BLOWAGE LOWAGE 0 I = -{age_c} * ((V(NENABLE) > 0.5 && V(NINX) < 0.5) ? 1e9 : 0.0)\n"
    st += "BLOWRESET LOWAGE 0 I = {age_c} * V(FALLEDGE) * V(LOWAGE) / edge_delay\n"
    st += "Clowage LOWAGE 0 {age_c} ic=0\n"
    st += "Rlowage LOWAGE 0 1e15\n"
    st += "BHFALL_AFTER_RISE HFALL_AFTER_RISE 0 V = (V(NENABLE) > 0.5 && V(NINX) < 0.5 && V(HIGHAGE) > 0.01 && V(HIGHAGE) < directional_window_ns) ? 1.0 : 0.0\n"
    st += "BHRISE_AFTER_FALL HRISE_AFTER_FALL 0 V = (V(NENABLE) > 0.5 && V(NINX) > 0.5 && V(LOWAGE) > 0.01 && V(LOWAGE) < directional_window_ns) ? 1.0 : 0.0\n"
    st += "BHDIRRAW HDIRRAW 0 V = (V(HFALL_AFTER_RISE) > 0.5 || V(HRISE_AFTER_FALL) > 0.5) ? 1.0 : 0.0\n"
    st += "BALIGNED HALIGNED 0 V = (abs(V(KUDIR) - V(KULEG)) < 0.01 && abs(V(KDDIR) - V(KDLEG)) < 0.01) ? 1.0 : 0.0\n"
    st += "BHDIRACTIVE HDIRACTIVE 0 V = (V(HDIRRAW) > 0.5 && V(HALIGNED) < 0.5) ? 1.0 : 0.0\n"
    if mode == "full":
        st += "BHALIGN HALIGN 0 V = 1.0\n"
    else:
        st += "BHALIGN HALIGN 0 V = V(HDIRACTIVE)\n"
    st += "\n"

    st += "B42 KUTARGET 0 V = V(HALIGN) * V(KUDIR) + (1.0 - V(HALIGN)) * V(KULEG)\n"
    st += "B43 KDTARGET 0 V = V(HALIGN) * V(KDDIR) + (1.0 - V(HALIGN)) * V(KDLEG)\n"
    st += "B44 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={ku_low:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B45 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={kd_low:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_charge_limited_gate_state_input_control_netlist(kr, kf, ibis_data, mode="hybrid"):
    """
    Creates charge-limited hidden-gate-state coefficient control.

    QPU/QPD are bounded hidden charge states for pullup and pulldown drive.
    They replace the additive KU_ON+KU_OFF style used by the directional
    experiment, so an interrupted reverse edge can only discharge charge that
    actually exists. Hybrid mode normally uses legacy Ku/Kd when settled, and
    switches to charge-state Ku/Kd while the hidden gate state is unsettled or
    an interrupted transition latch is active.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenChargeLimitedGate v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    fit = gate_state_fit(kr, kf)
    ku_table = convert_iv_table_to_str(fit["ku_map_x"], fit["ku_map_y"])
    kd_table = convert_iv_table_to_str(fit["kd_map_x"], fit["kd_map_y"])

    fast_factor = 0.5 if mode == "fast_recover" else 1.0
    fast_pu_delay = max(0.0, min(fit["pu_on_delay"], fit["pu_off_delay"]) * fast_factor)
    fast_pd_delay = max(0.0, min(fit["pd_on_delay"], fit["pd_off_delay"]) * fast_factor)
    fast_pu_tau = max(0.02, min(fit["pu_on_tau"], fit["pu_off_tau"]) * fast_factor)
    fast_pd_tau = max(0.02, min(fit["pd_on_tau"], fit["pd_off_tau"]) * fast_factor)

    st = ""
    st += "* Charge-limited gate-state input-driven waveform coefficient control\n"
    st += "* QPU/QPD are bounded pullup/pulldown gate-charge states. KUCHG/KDCHG\n"
    st += "* are monotonic maps from charge state to effective IBIS coefficients.\n"
    st += "* Reverse edges do not inject full off/on event taps; they retarget the\n"
    st += "* existing charge, avoiding over-cancellation during interrupted pulses.\n"
    st += f"* Charge-limited mode: {mode}\n"
    st += (
        f"* PU on/off delay={fit['pu_on_delay']:.6g}/{fit['pu_off_delay']:.6g}ns "
        f"tau={fit['pu_on_tau']:.6g}/{fit['pu_off_tau']:.6g}ns\n"
    )
    st += (
        f"* PD on/off delay={fit['pd_on_delay']:.6g}/{fit['pd_off_delay']:.6g}ns "
        f"tau={fit['pd_on_tau']:.6g}/{fit['pd_off_tau']:.6g}ns\n"
    )
    st += (
        f"* Fast recovery delay PU/PD={fast_pu_delay:.6g}/{fast_pd_delay:.6g}ns "
        f"tau={fast_pu_tau:.6g}/{fast_pd_tau:.6g}ns\n"
    )
    st += f".param coeff_c=1p coeff_tau=5p gate_c=1p latch_c=1p age_c=1p charge_window_ns={fit['interrupt_window_ns']:.16g}\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    pulse_delays = [
        ("PUONP", "RISEEDGE", fast_pu_delay if mode == "fast_recover" else fit["pu_on_delay"]),
        ("PUOFFP", "FALLEDGE", fit["pu_off_delay"]),
        ("PDOFFP", "RISEEDGE", fit["pd_off_delay"]),
        ("PDONP", "FALLEDGE", fast_pd_delay if mode == "fast_recover" else fit["pd_on_delay"]),
    ]
    for name, source, delay in pulse_delays:
        if delay <= 1e-15:
            st += f"B{name} {name} 0 V = V({source})\n"
        else:
            st += f"T{name} {source} 0 {name} 0 Z0=50 Td={format_spice_ns(delay)}\n"
            st += f"R{name} {name} 0 50\n"
    st += "\n"

    st += "* Short-pulse arming. HIGHAGE/LOWAGE are measured in ns; QPU/QPD are bounded charge states.\n"
    st += "BHAD_RISE HAD_RISE 0 V = V(NINX)\n"
    st += "BHAD_FALL HAD_FALL 0 V = 1.0 - V(NINX)\n"
    st += "BHIGHAGE HIGHAGE 0 I = -{age_c} * ((V(NENABLE) > 0.5 && V(NINX) > 0.5) ? 1e9 : 0.0)\n"
    st += "BHIGHRESET HIGHAGE 0 I = {age_c} * V(RISEEDGE) * V(HIGHAGE) / edge_delay\n"
    st += "Chighage HIGHAGE 0 {age_c} ic=0\n"
    st += "Rhighage HIGHAGE 0 1e15\n"
    st += "BLOWAGE LOWAGE 0 V = 0.0\n"
    st += "BHFALL_AFTER_RISE HFALL_AFTER_RISE 0 V = (V(NENABLE) > 0.5 && V(NINX) < 0.5 && V(HIGHAGE) > 0.01 && V(HIGHAGE) < charge_window_ns) ? 1.0 : 0.0\n"
    st += "BHRISE_AFTER_FALL HRISE_AFTER_FALL 0 V = (V(NENABLE) > 0.5 && V(NINX) > 0.5 && V(QPU) > 0.5 && V(QPU) < 0.98 && V(QPD) < 0.5) ? 1.0 : 0.0\n"
    st += "\n"

    st += "CQPUCMD QPUCMD 0 {gate_c} ic=0\n"
    st += "RQPUCMD QPUCMD 0 1e15\n"
    st += "BQPUCMDON QPUCMD 0 I = -{gate_c} * V(PUONP) / edge_delay\n"
    st += "BQPUCMDOFF QPUCMD 0 I = {gate_c} * V(PUOFFP) / edge_delay\n"
    st += "CQPDCMD QPDCMD 0 {gate_c} ic=1\n"
    st += "BQPDCMDBASE QPDCMDBASE 0 V = 1.0\n"
    st += "RQPDCMD QPDCMD QPDCMDBASE 1e15\n"
    st += "BQPDCMDOFF QPDCMD 0 I = {gate_c} * V(PDOFFP) / edge_delay\n"
    st += "BQPDCMDON QPDCMD 0 I = -{gate_c} * V(PDONP) / edge_delay\n"
    st += "BQPUTARGET QPUTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(QPUCMD), 0), 1) : 0.0\n"
    st += "BQPDTARGET QPDTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(QPDCMD), 0), 1) : 0.0\n"
    st += (
        f"BQPU QPU 0 I = -{{gate_c}} * (V(QPUTARGET) - V(QPU)) / "
        f"((V(QPUTARGET) > V(QPU)) ? ((V(HRISE_AFTER_FALL) > 0.5) ? {format_spice_ns(fast_pu_tau)} : {format_spice_ns(fit['pu_on_tau'])}) : {format_spice_ns(fit['pu_off_tau'])})\n"
    )
    st += "CQPU QPU 0 {gate_c} ic=0\n"
    st += "RQPU QPU 0 1e12\n"
    st += (
        f"BQPD QPD 0 I = -{{gate_c}} * (V(QPDTARGET) - V(QPD)) / "
        f"((V(QPDTARGET) > V(QPD)) ? ((V(HFALL_AFTER_RISE) > 0.5) ? {format_spice_ns(fast_pd_tau)} : {format_spice_ns(fit['pd_on_tau'])}) : {format_spice_ns(fit['pd_off_tau'])})\n"
    )
    st += "CQPD QPD 0 {gate_c} ic=1\n"
    st += "BQPD_BASE QPDBASE 0 V = 1.0\n"
    st += "RQPD QPD QPDBASE 1e12\n\n"

    st += f"BKUCHG KUCHG 0 V = pwl(min(max(V(QPU), 0), 1), {ku_table})\n"
    st += f"BKDCHG KDCHG 0 V = pwl(min(max(V(QPD), 0), 1), {kd_table})\n"
    st += "BKOVERLAP KOVERLAP 0 V = max(V(Ku), 0) * max(V(Kd), 0)\n"
    if mode == "full":
        st += "BHCHGACTIVE HCHGACTIVE 0 V = 1.0\n"
    elif mode == "fast_recover":
        st += "BCHGUNSETTLED HCHGUNSETTLED 0 V = min(max(max(abs(V(QPU) - V(NINX)), abs(V(QPD) - (1.0 - V(NINX)))) / 0.1, 0), 1)\n"
        st += "BHCHGACTIVE HCHGACTIVE 0 V = min(max(V(HFALL_AFTER_RISE), V(HRISE_AFTER_FALL)), 1)\n"
    else:
        st += "BCHGUNSETTLED HCHGUNSETTLED 0 V = min(max(max(abs(V(QPU) - V(NINX)), abs(V(QPD) - (1.0 - V(NINX)))) / 0.1, 0), 1)\n"
        st += "BHCHGACTIVE HCHGACTIVE 0 V = min(max(V(HFALL_AFTER_RISE), 0), 1)\n"
    st += "\n"

    st += "B42 KUTARGET 0 V = V(HCHGACTIVE) * V(KUCHG) + (1.0 - V(HCHGACTIVE)) * V(KULEG)\n"
    st += "B43 KDTARGET 0 V = V(HCHGACTIVE) * V(KDCHG) + (1.0 - V(HCHGACTIVE)) * V(KDLEG)\n"
    st += "B44 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={fit['ku_off']:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B45 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={fit['kd_on']:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_two_state_gate_input_control_netlist(kr, kf, ibis_data, mode="pwl_full"):
    """
    Creates the v2 two-state hidden-gate coefficient model.

    Unlike the earlier GateState/ChargeLimited experiments, this path is meant
    to be judged first on complete-edge Ku/Kd reconstruction. Runtime final
    coefficients do not index the IBIS Ku/Kd tables by elapsed edge time; the
    tables are consumed offline into two continuous gate states and optional
    monotonic coefficient maps.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenTwoStateGate v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    residual_modes = {
        "directional_residual_full",
        "directional_residual_recover_mean_full",
        "directional_residual_recover_fast_full",
    }
    recover_modes = {
        "directional_residual_recover_mean_full",
        "directional_residual_recover_fast_full",
    }
    use_directional_map = mode in {"directional_full"} | residual_modes
    fit = two_state_directional_gate_fit(kr, kf) if use_directional_map else gate_state_fit(kr, kf)
    use_identity_map = mode == "identity_full"
    full_mode = mode in {"pwl_full", "identity_full"}
    if use_directional_map:
        full_mode = True
    ku_table = convert_iv_table_to_str(fit["ku_map_x"], fit["ku_map_y"])
    kd_table = convert_iv_table_to_str(fit["kd_map_x"], fit["kd_map_y"])
    if use_directional_map:
        ku_on_table = convert_iv_table_to_str(fit["ku_on_map_x"], fit["ku_on_map_y"])
        ku_off_table = convert_iv_table_to_str(fit["ku_off_map_x"], fit["ku_off_map_y"])
        kd_off_table = convert_iv_table_to_str(fit["kd_off_map_x"], fit["kd_off_map_y"])
        kd_on_table = convert_iv_table_to_str(fit["kd_on_map_x"], fit["kd_on_map_y"])

    st = ""
    st += "* Two-state gate input-driven waveform coefficient control\n"
    st += "* GUP/GDN are continuous pullup/pulldown hidden gate states.\n"
    st += "* Complete-edge Ku/Kd tables are used only to fit delays, taus, and maps.\n"
    st += "* Final Ku/Kd are generated from GUP/GDN, not by elapsed-time table replay.\n"
    st += f"* Two-state gate mode: {mode}\n"
    st += (
        f"* PU on/off delay={fit['pu_on_delay']:.6g}/{fit['pu_off_delay']:.6g}ns "
        f"tau={fit['pu_on_tau']:.6g}/{fit['pu_off_tau']:.6g}ns\n"
    )
    st += (
        f"* PD on/off delay={fit['pd_on_delay']:.6g}/{fit['pd_off_delay']:.6g}ns "
        f"tau={fit['pd_on_tau']:.6g}/{fit['pd_off_tau']:.6g}ns\n"
    )
    st += (
        f"* Endpoint estimates: ku_off={fit['ku_off']:.6g} ku_on={fit['ku_on']:.6g} "
        f"kd_off={fit['kd_off']:.6g} kd_on={fit['kd_on']:.6g}\n"
    )
    if use_directional_map:
        st += f"* Direction-specific maps enabled. Kd rate gain={fit['kd_rate_gain_ns']:.6g} ns\n"
    pd_recover_delay = fit["pd_on_delay"]
    if mode == "directional_residual_recover_mean_full":
        pd_recover_delay = 0.5 * (fit["pd_on_delay"] + fit["pd_off_delay"])
    elif mode == "directional_residual_recover_fast_full":
        pd_recover_delay = min(fit["pd_on_delay"], fit["pd_off_delay"])
    if mode in recover_modes:
        st += f"* Retrigger-aware PD recovery delay={pd_recover_delay:.6g}ns for short-high fall-after-rise events.\n"
    st += ".param coeff_c=1p coeff_tau=5p gate_c=1p retrigger_window_ns=4.0\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += "* Legacy Ku/Kd remain as diagnostics and hybrid fallback only.\n"
    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "* Delayed command targets. Pending reverse events are not erased.\n"
    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    for name, source, delay in [
        ("PUONP", "RISEEDGE", fit["pu_on_delay"]),
        ("PUOFFP", "FALLEDGE", fit["pu_off_delay"]),
        ("PDOFFP", "RISEEDGE", fit["pd_off_delay"]),
    ]:
        if delay <= 1e-15:
            st += f"B{name} {name} 0 V = V({source})\n"
        else:
            st += f"T{name} {source} 0 {name} 0 Z0=50 Td={format_spice_ns(delay)}\n"
            st += f"R{name} {name} 0 50\n"
    if mode in recover_modes:
        st += "BPDRECOVEREDGE PDRECOVEREDGE 0 V = (V(FALLEDGE) > 0.5 && V(HNX) < retrigger_window_ns) ? 1.0 : 0.0\n"
        st += "BPDNORMALFALL PDNORMALFALL 0 V = (V(FALLEDGE) > 0.5 && V(HNX) >= retrigger_window_ns) ? 1.0 : 0.0\n"
        for name, source, delay in [
            ("PDONP_NORM", "PDNORMALFALL", fit["pd_on_delay"]),
            ("PDONP_RECOVER", "PDRECOVEREDGE", pd_recover_delay),
        ]:
            if delay <= 1e-15:
                st += f"B{name} {name} 0 V = V({source})\n"
            else:
                st += f"T{name} {source} 0 {name} 0 Z0=50 Td={format_spice_ns(delay)}\n"
                st += f"R{name} {name} 0 50\n"
        st += "BPDONP PDONP 0 V = max(V(PDONP_NORM), V(PDONP_RECOVER))\n"
        st += "BHSHORT_HIGH_RECOVERY HSHORT_HIGH_RECOVERY 0 V = (V(PDRECOVEREDGE) > 0.5 || V(PDONP_RECOVER) > 0.5) ? 1.0 : 0.0\n"
    else:
        delay = fit["pd_on_delay"]
        if delay <= 1e-15:
            st += "BPDONP PDONP 0 V = V(FALLEDGE)\n"
        else:
            st += f"TPDONP FALLEDGE 0 PDONP 0 Z0=50 Td={format_spice_ns(delay)}\n"
            st += "RPDONP PDONP 0 50\n"
        st += "BPDRECOVEREDGE PDRECOVEREDGE 0 V = 0.0\n"
        st += "BPDNORMALFALL PDNORMALFALL 0 V = V(FALLEDGE)\n"
        st += "BPDONP_NORM PDONP_NORM 0 V = V(PDONP)\n"
        st += "BPDONP_RECOVER PDONP_RECOVER 0 V = 0.0\n"
        st += "BHSHORT_HIGH_RECOVERY HSHORT_HIGH_RECOVERY 0 V = 0.0\n"
    st += "\n"

    st += "CGUPCMD GUPCMD 0 {gate_c} ic=0\n"
    st += "RGUPCMD GUPCMD 0 1e15\n"
    st += "BGUPCMDON GUPCMD 0 I = -{gate_c} * V(PUONP) / edge_delay\n"
    st += "BGUPCMDOFF GUPCMD 0 I = {gate_c} * V(PUOFFP) / edge_delay\n"
    st += "CGDNCMD GDNCMD 0 {gate_c} ic=1\n"
    st += "BGDNCMDBASE GDNCMDBASE 0 V = 1.0\n"
    st += "RGDNCMD GDNCMD GDNCMDBASE 1e15\n"
    st += "BGDNCMDOFF GDNCMD 0 I = {gate_c} * V(PDOFFP) / edge_delay\n"
    st += "BGDNCMDON GDNCMD 0 I = -{gate_c} * V(PDONP) / edge_delay\n"
    st += "BGUPTARGET GUPTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(GUPCMD), 0), 1) : 0.0\n"
    st += "BGDNTARGET GDNTARGET 0 V = (V(NENABLE) > 0.5) ? min(max(V(GDNCMD), 0), 1) : 0.0\n"
    st += (
        f"BGUP GUP 0 I = -{{gate_c}} * (V(GUPTARGET) - V(GUP)) / "
        f"((V(GUPTARGET) > V(GUP)) ? {format_spice_ns(fit['pu_on_tau'])} : {format_spice_ns(fit['pu_off_tau'])})\n"
    )
    st += "CGUP GUP 0 {gate_c} ic=0\n"
    st += "RGUP GUP 0 1e12\n"
    st += (
        f"BGDN GDN 0 I = -{{gate_c}} * (V(GDNTARGET) - V(GDN)) / "
        f"((V(GDNTARGET) > V(GDN)) ? {format_spice_ns(fit['pd_on_tau'])} : {format_spice_ns(fit['pd_off_tau'])})\n"
    )
    st += "CGDN GDN 0 {gate_c} ic=1\n"
    st += "BGDNBASE GDNBASE 0 V = 1.0\n"
    st += "RGDN GDN GDNBASE 1e12\n\n"

    if use_directional_map:
        st += f"BKUGATE_ON KUGATE_ON 0 V = pwl(min(max(V(GUP), 0), 1), {ku_on_table})\n"
        st += f"BKUGATE_OFF KUGATE_OFF 0 V = pwl(min(max(V(GUP), 0), 1), {ku_off_table})\n"
        st += "BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP)) ? V(KUGATE_ON) : V(KUGATE_OFF)\n"
        st += f"BKDGATE_OFF KDGATE_OFF 0 V = pwl(min(max(V(GDN), 0), 1), {kd_off_table})\n"
        st += f"BKDGATE_ON KDGATE_ON 0 V = pwl(min(max(V(GDN), 0), 1), {kd_on_table})\n"
        st += "BKDGATE_BASE KDGATE_BASE 0 V = (V(GDNTARGET) >= V(GDN)) ? V(KDGATE_ON) : V(KDGATE_OFF)\n"
        if mode in residual_modes:
            st += create_ngspice_k_lookup_source_from_elapsed("BKDRESR", "KDRES_R", "HNX", kr[:, _TIME], fit["kd_rise_residual"])
            st += create_ngspice_k_lookup_source_from_elapsed("BKDRESF", "KDRES_F", "HNX", kf[:, _TIME], fit["kd_fall_residual"])
            st += "BKDRES_TABLE KDRES_TABLE 0 V = (V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(KDRES_R) : V(KDRES_F)) : 0.0\n"
        else:
            st += "BKDRES_TABLE KDRES_TABLE 0 V = 0.0\n"
        st += (
            f"BGDNRATE GDNRATE 0 V = ((V(GDNTARGET) - V(GDN)) / "
            f"((V(GDNTARGET) > V(GDN)) ? {format_spice_ns(fit['pd_on_tau'])} : {format_spice_ns(fit['pd_off_tau'])})) * 1e-9\n"
        )
        if mode in residual_modes:
            st += f"BKDRES KDRES 0 V = V(KDRES_TABLE) + {fit['kd_rate_gain_ns']:.16g} * V(GDNRATE)\n"
        else:
            st += "BKDRES KDRES 0 V = 0.0\n"
        st += "BKUGATE KUGATE 0 V = V(KUGATE_BASE)\n"
        st += "BKDGATE KDGATE 0 V = V(KDGATE_BASE) + V(KDRES)\n"
    elif use_identity_map:
        st += f"BKUGATE KUGATE 0 V = {fit['ku_off']:.16g} + ({fit['ku_on'] - fit['ku_off']:.16g}) * min(max(V(GUP), 0), 1)\n"
        st += f"BKDGATE KDGATE 0 V = {fit['kd_off']:.16g} + ({fit['kd_on'] - fit['kd_off']:.16g}) * min(max(V(GDN), 0), 1)\n"
    else:
        st += f"BKUGATE KUGATE 0 V = pwl(min(max(V(GUP), 0), 1), {ku_table})\n"
        st += f"BKDGATE KDGATE 0 V = pwl(min(max(V(GDN), 0), 1), {kd_table})\n"
    st += "BKOVERLAP KOVERLAP 0 V = max(V(Ku), 0) * max(V(Kd), 0)\n"
    st += "BH2STATEACTIVE H2STATEACTIVE 0 V = "
    st += "((V(NINX) < 0.5 && V(GUP) > 0.05 && V(GUP) < 0.95) || "
    st += "(V(NINX) > 0.5 && V(GDN) > 0.05 && V(GDN) < 0.95)) ? 1.0 : 0.0\n\n"

    if full_mode:
        st += "B42 KUTARGET 0 V = V(KUGATE)\n"
        st += "B43 KDTARGET 0 V = V(KDGATE)\n"
    else:
        st += "B42 KUTARGET 0 V = V(H2STATEACTIVE) * V(KUGATE) + (1.0 - V(H2STATEACTIVE)) * V(KULEG)\n"
        st += "B43 KDTARGET 0 V = V(H2STATEACTIVE) * V(KDGATE) + (1.0 - V(H2STATEACTIVE)) * V(KDLEG)\n"
    st += "B44 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={fit['ku_off']:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B45 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={fit['kd_on']:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_value_matched_replay_input_control_netlist(kr, kf, ibis_data, mode="hybrid_balanced"):
    """
    Creates value-matched table-replay coefficient control.

    On each input edge, the current final Ku/Kd are sampled into KUSAMP/KDSAMP.
    Inverse PWL maps convert those sampled values into a matched time on the
    new transition table. The replay argument is matched_start + elapsed time.
    Hybrid mode uses legacy replay unless the inferred matched start time is
    nonzero; full mode always uses the value-matched replay path.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenValueMatchedReplay v1 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    ku_low, ku_high = coefficient_state_endpoint_values(kr, kf, _KU, 0.0, 1.0)
    kd_low, kd_high = coefficient_state_endpoint_values(kr, kf, _KD, 1.0, 0.0)
    if mode.endswith("_ku"):
        policy = "ku_only"
        tr_start_expr = "V(TR_KU)"
        tf_start_expr = "V(TF_KU)"
    elif mode.endswith("_kd"):
        policy = "kd_only"
        tr_start_expr = "V(TR_KD)"
        tf_start_expr = "V(TF_KD)"
    else:
        policy = "balanced"
        tr_start_expr = "0.5 * (V(TR_KU) + V(TR_KD))"
        tf_start_expr = "0.5 * (V(TF_KU) + V(TF_KD))"
    full_mode = mode.startswith("full")

    st = ""
    st += "* Value-matched replay input-driven waveform coefficient control\n"
    st += "* KUSAMP/KDSAMP sample current coefficients at an input edge. Inverse\n"
    st += "* coefficient-to-time maps find a start time on the new transition table.\n"
    st += f"* Value-matched mode: {mode}; policy={policy}\n"
    max_replay_time_ns = max(float(np.nanmax(kr[:, _TIME])), float(np.nanmax(kf[:, _TIME]))) * 1e9
    st += (
        ".param coeff_c=1p coeff_tau=1p sample_c=1p match_tau=0.2p "
        f"vm_end_ns={max_replay_time_ns:.16g}\n"
    )
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    st += "BEDGEPULSE EDGEPULSE 0 V = min(max(abs(V(HN2)), 0), 1)\n"
    st += "BFALLAFTRISE HFALL_AFTER_RISE 0 V = (V(FALLEDGE) > 0.5 && (V(Ku) < 0.95 || V(Kd) > 0.05)) ? 1.0 : 0.0\n"
    st += "BRISEAFTFALL HRISE_AFTER_FALL 0 V = (V(RISEEDGE) > 0.5 && (V(Ku) > 0.05 || V(Kd) < 0.95)) ? 1.0 : 0.0\n"
    st += "BHREVERSE HREVERSE_EDGE 0 V = (V(HFALL_AFTER_RISE) > 0.5 || V(HRISE_AFTER_FALL) > 0.5) ? 1.0 : 0.0\n"
    st += f"CKUSAMP KUSAMP 0 {{sample_c}} ic={ku_low:.16g}\n"
    st += "RKUSAMP KUSAMP 0 1e15\n"
    st += "BKUSAMPLE KUSAMP 0 I = -{sample_c} * V(EDGEPULSE) * (V(Ku) - V(KUSAMP)) / match_tau\n"
    st += f"CKDSAMP KDSAMP 0 {{sample_c}} ic={kd_low:.16g}\n"
    st += "BKDSAMPBASE KDSAMPBASE 0 V = 1.0\n"
    st += "RKDSAMP KDSAMP KDSAMPBASE 1e15\n"
    st += "BKDSAMPLE KDSAMP 0 I = -{sample_c} * V(EDGEPULSE) * (V(Kd) - V(KDSAMP)) / match_tau\n\n"

    st += create_inverse_time_lookup_source("B30", "TR_KU", "KUSAMP", kr[:, _TIME], kr[:, _KU])
    st += create_inverse_time_lookup_source("B31", "TR_KD", "KDSAMP", kr[:, _TIME], kr[:, _KD])
    st += create_inverse_time_lookup_source("B32", "TF_KU", "KUSAMP", kf[:, _TIME], kf[:, _KU])
    st += create_inverse_time_lookup_source("B33", "TF_KD", "KDSAMP", kf[:, _TIME], kf[:, _KD])
    st += f"B34 TR_START 0 V = {tr_start_expr}\n"
    st += f"B35 TF_START 0 V = {tf_start_expr}\n"
    st += "B36 VMSTARTCMD 0 V = (V(NINX) > 0.5) ? V(TR_START) : V(TF_START)\n"
    st += "CVMSTART VMSTART 0 {sample_c} ic=0\n"
    st += "RVMSTART VMSTART 0 1e15\n"
    st += "BVMSTART VMSTART 0 I = -{sample_c} * V(EDGEPULSE) * (V(VMSTARTCMD) - V(VMSTART)) / match_tau\n"
    st += "B37 VMARG 0 V = V(VMSTART) + V(HNX)\n"
    st += "B38 START_DISAGREE 0 V = (V(NINX) > 0.5) ? abs(V(TR_KU) - V(TR_KD)) : abs(V(TF_KU) - V(TF_KD))\n"
    st += "B39 MATCH_AMBIGUOUS 0 V = (V(START_DISAGREE) > 0.5) ? 1.0 : 0.0\n\n"

    st += create_ngspice_k_lookup_source_from_arg("B40", "KURM", "VMARG", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_arg("B41", "KDRM", "VMARG", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_arg("B42", "KUFM", "VMARG", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_arg("B43", "KDFM", "VMARG", kf[:, _TIME], kf[:, _KD])
    st += "B44 KUMATCH 0 V = (V(NINX) > 0.5) ? V(KURM) : V(KUFM)\n"
    st += "B45 KDMATCH 0 V = (V(NINX) > 0.5) ? V(KDRM) : V(KDFM)\n"
    st += "B46 MATCH_ERR_KU 0 V = abs(V(KUMATCH) - V(KUSAMP))\n"
    st += "B47 MATCH_ERR_KD 0 V = abs(V(KDMATCH) - V(KDSAMP))\n"
    if full_mode:
        st += "B48 HVMATCH 0 V = 1.0\n"
    else:
        st += "B48 HVMATCHCMD 0 V = (V(HREVERSE_EDGE) > 0.5) ? 1.0 : ((V(VMARG) < vm_end_ns) ? V(HVMATCH) : 0.0)\n"
        st += "CHVMATCH HVMATCH 0 {sample_c} ic=0\n"
        st += "RHVMATCH HVMATCH 0 1e15\n"
        st += "BHVMATCH HVMATCH 0 I = -{sample_c} * (V(HVMATCHCMD) - V(HVMATCH)) / match_tau\n"
    st += "\n"

    st += "B49 KUTARGET 0 V = (V(HREVERSE_EDGE) > 0.5) ? V(KUSAMP) : ((V(HVMATCH) > 0.05) ? V(KUMATCH) : V(KULEG))\n"
    st += "B50 KDTARGET 0 V = (V(HREVERSE_EDGE) > 0.5) ? V(KDSAMP) : ((V(HVMATCH) > 0.05) ? V(KDMATCH) : V(KDLEG))\n"
    st += "B51 Ku 0 I = -{coeff_c} * (V(KUTARGET) - V(Ku)) / coeff_tau\n"
    st += f"Cku Ku 0 {{coeff_c}} ic={ku_low:.16g}\n"
    st += "Rku Ku 0 1e12\n"
    st += "B52 Kd 0 I = -{coeff_c} * (V(KDTARGET) - V(Kd)) / coeff_tau\n"
    st += f"Ckd Kd 0 {{coeff_c}} ic={kd_low:.16g}\n"
    st += "Rkd Kd 0 1e12\n\n"
    return st


def create_ngspice_value_matched_replay_v2_input_control_netlist(kr, kf, ibis_data, mode="hybrid_balanced"):
    """
    Creates corrected value-matched replay coefficient control.

    V1 reused HNX, the legacy elapsed-time coordinate, in VMARG. During a reverse
    edge that mixed a newly latched value-match start with the old transition
    elapsed time. V2 latches the reverse-edge sample and start time, creates a
    fresh value-match timer, and evaluates the replay tables from
    VMSTART_LATCH + VMELAPSED.
    """
    if ibis_data.model_type.lower() == "open_drain":
        st = "* InputDrivenValueMatchedReplayV2 is push-pull only; using legacy Kd control for open-drain.\n"
        return st + create_ngspice_input_control_netlist(kr, kf, ibis_data)

    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    ku_low, _ = coefficient_state_endpoint_values(kr, kf, _KU, 0.0, 1.0)
    kd_low, _ = coefficient_state_endpoint_values(kr, kf, _KD, 1.0, 0.0)
    split_mode = mode.endswith("_split")
    if mode.endswith("_ku"):
        policy = "ku_only"
        tr_start_expr = "V(TR_KU)"
        tf_start_expr = "V(TF_KU)"
        ku_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"
        kd_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"
    elif mode.endswith("_kd"):
        policy = "kd_only"
        tr_start_expr = "V(TR_KD)"
        tf_start_expr = "V(TF_KD)"
        ku_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"
        kd_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"
    elif split_mode:
        policy = "split_ku_kd"
        tr_start_expr = "0.5 * (V(TR_KU) + V(TR_KD))"
        tf_start_expr = "0.5 * (V(TF_KU) + V(TF_KD))"
        ku_start_expr = "(V(NINX) > 0.5) ? V(TR_KU) : V(TF_KU)"
        kd_start_expr = "(V(NINX) > 0.5) ? V(TR_KD) : V(TF_KD)"
    else:
        policy = "balanced"
        tr_start_expr = "0.5 * (V(TR_KU) + V(TR_KD))"
        tf_start_expr = "0.5 * (V(TF_KU) + V(TF_KD))"
        ku_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"
        kd_start_expr = "(V(NINX) > 0.5) ? V(TR_START) : V(TF_START)"

    st = ""
    st += "* Value-matched replay V2 input-driven waveform coefficient control\n"
    st += "* V2 latches Ku/Kd samples and inverse start times, then uses a fresh\n"
    st += "* VMELAPSED timer. VMARG intentionally does not depend on legacy HNX.\n"
    st += f"* Value-matched V2 mode: {mode}; policy={policy}\n"
    max_replay_time_ns = max(float(np.nanmax(kr[:, _TIME])), float(np.nanmax(kf[:, _TIME]))) * 1e9
    st += (
        ".param coeff_c=1p coeff_tau=5p sample_c=1p sample_tau=2p match_tau=5p "
        "vm_latch_width=20p vm_latch_delay=20p vm_edge_delay_ns=0.01 interrupt_window_ns=4.0 "
        f"vm_end_ns={max_replay_time_ns:.16g}\n"
    )
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 HNI 0 V = V(NINX) - 0.5\n"
    st += "B13 HN2 0 V = V(HNI,HN9) * 8\n"
    st += "B14 HN3 0 V = abs(V(HN2))\n"
    st += "B15 HN4 0 V = (V(HN3) > 0.5) ? 1 : -1\n"
    st += "B16 HN5 0 V = (V(HN4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 HN6 0 V = (V(HN4) > 0) ? V(HN5) : V(HN8)\n"
    st += "B18 HNX 0 V = (V(HN6) >= 1.0) ? time*{time_scale} - V(HN8) : 0.0\n"
    st += "T1 HN6 0 HN8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 HNI 0 HN9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 HN8 0 50\n"
    st += "R6 HN9 0 50\n\n"

    st += create_ngspice_k_lookup_source_from_elapsed("B20", "HKUR0", "HNX", kr[:, _TIME], kr[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B21", "HKDR0", "HNX", kr[:, _TIME], kr[:, _KD])
    st += create_ngspice_k_lookup_source_from_elapsed("B22", "HKUF0", "HNX", kf[:, _TIME], kf[:, _KU])
    st += create_ngspice_k_lookup_source_from_elapsed("B23", "HKDF0", "HNX", kf[:, _TIME], kf[:, _KD])
    st += "B24 HNKUF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 1 : V(HKUF0)) : 0\n"
    st += "B25 HNKDF 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 || V(HN2) < -0.1) ? 0 : V(HKDF0)) : 1\n"
    st += "B26 HNKUR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKUR0) : 0) : 0\n"
    st += "B27 HNKDR 0 V = (V(HN6) > 0.5) ? "
    st += "((V(HNI) > 0 && V(HN3) < 0.1) ? V(HKDR0) : 1) : 1\n"
    st += "B28 KULEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKUR) : V(HNKUF)) : 0) : 0\n"
    st += "B29 KDLEG 0 V = (V(NENABLE) > 0.5) ? "
    st += "((V(HN6) > 0.5) ? ((V(HNI) > 0 && V(HN2) > -0.1) ? V(HNKDR) : V(HNKDF)) : 1) : 0\n\n"

    st += "BRISEEDGE RISEEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) > 0.5) ? 1.0 : 0.0\n"
    st += "BFALLEDGE FALLEDGE 0 V = (V(NENABLE) > 0.5 && V(HN2) < -0.5) ? 1.0 : 0.0\n"
    st += "CHADRISE HAD_RISE 0 {sample_c} ic=0\n"
    st += "RHADRISE HAD_RISE 0 1e15\n"
    st += "BHADRISE HAD_RISE 0 I = -{sample_c} * V(RISEEDGE) * (1.0 - V(HAD_RISE)) / match_tau\n"
    st += "CHADFALL HAD_FALL 0 {sample_c} ic=0\n"
    st += "RHADFALL HAD_FALL 0 1e15\n"
    st += "BHADFALL HAD_FALL 0 I = -{sample_c} * V(FALLEDGE) * (1.0 - V(HAD_FALL)) / match_tau\n"
    st += "BHINTWINDOW HINTWINDOW 0 V = (V(HNX) < interrupt_window_ns) ? 1.0 : 0.0\n"
    st += "BFALLAFTRISE HFALL_AFTER_RISE 0 V = (V(FALLEDGE) > 0.5 && V(HINTWINDOW) > 0.5) ? 1.0 : 0.0\n"
    st += "BRISEAFTFALL HRISE_AFTER_FALL 0 V = (V(RISEEDGE) > 0.5 && V(HAD_FALL) > 0.5 && V(HINTWINDOW) > 0.5 && (V(Ku) > 0.05 || V(Kd) < 0.95)) ? 1.0 : 0.0\n"
    st += "BHREVERSE HREVERSE_EDGE 0 V = (V(HFALL_AFTER_RISE) > 0.5 || V(HRISE_AFTER_FALL) > 0.5) ? 1.0 : 0.0\n"
    st += "* Pre-edge event source: use the previous transition table directly, before legacy replay direction switches.\n"
    st += "BPREKU KUPRE 0 V = (V(HFALL_AFTER_RISE) > 0.5) ? V(HKUR0) : ((V(HRISE_AFTER_FALL) > 0.5) ? V(HKUF0) : V(KULEG))\n"
    st += "BPREKD KDPRE 0 V = (V(HFALL_AFTER_RISE) > 0.5) ? V(HKDR0) : ((V(HRISE_AFTER_FALL) > 0.5) ? V(HKDF0) : V(KDLEG))\n"
    st += "TREVEDGE HREVERSE_EDGE 0 HREVERSE_DLY 0 Z0=50 Td={vm_latch_width}\n"
    st += "RHREVEDGE HREVERSE_DLY 0 50\n"
    st += "BVMSAMPLE VMSAMPLE 0 V = max(0, min(max(V(HREVERSE_EDGE), 0), 1) - min(max(V(HREVERSE_DLY), 0), 1))\n"
    st += "TVMLATCH VMSAMPLE 0 VMLATCHRAW 0 Z0=50 Td={vm_latch_delay}\n"
    st += "RVMLATCH VMLATCHRAW 0 50\n"
    st += "B24A VMLATCHPULSE 0 V = min(max(V(VMLATCHRAW), 0), 1)\n\n"
    st += "TVMACTIVATE VMLATCHPULSE 0 VMACTIVATE 0 Z0=50 Td={vm_latch_width}\n"
    st += "RVMACTIVATE VMACTIVATE 0 50\n\n"

    st += f"CKUSAMP KUSAMP 0 {{sample_c}} ic={ku_low:.16g}\n"
    st += "RKUSAMP KUSAMP 0 1e15\n"
    st += "BKUSAMPLE KUSAMP 0 I = -{sample_c} * V(VMSAMPLE) * (V(KUPRE) - V(KUSAMP)) / sample_tau\n"
    st += f"CKDSAMP KDSAMP 0 {{sample_c}} ic={kd_low:.16g}\n"
    st += "BKDSAMPBASE KDSAMPBASE 0 V = 1.0\n"
    st += "RKDSAMP KDSAMP KDSAMPBASE 1e15\n"
    st += "BKDSAMPLE KDSAMP 0 I = -{sample_c} * V(VMSAMPLE) * (V(KDPRE) - V(KDSAMP)) / sample_tau\n\n"

    st += create_inverse_time_lookup_source("B30", "TR_KU", "KUSAMP", kr[:, _TIME], kr[:, _KU])
    st += create_inverse_time_lookup_source("B31", "TR_KD", "KDSAMP", kr[:, _TIME], kr[:, _KD])
    st += create_inverse_time_lookup_source("B32", "TF_KU", "KUSAMP", kf[:, _TIME], kf[:, _KU])
    st += create_inverse_time_lookup_source("B33", "TF_KD", "KDSAMP", kf[:, _TIME], kf[:, _KD])
    st += f"B34 TR_START 0 V = {tr_start_expr}\n"
    st += f"B35 TF_START 0 V = {tf_start_expr}\n"
    st += "B36 VMSTARTCMD 0 V = (V(NINX) > 0.5) ? V(TR_START) : V(TF_START)\n"
    st += f"B36A KUSTARTCMD 0 V = {ku_start_expr}\n"
    st += f"B36B KDSTARTCMD 0 V = {kd_start_expr}\n"
    st += "CVMSTART VMSTART_LATCH 0 {sample_c} ic=0\n"
    st += "RVMSTART VMSTART_LATCH 0 1e15\n"
    st += "BVMSTART VMSTART_LATCH 0 I = -{sample_c} * V(VMLATCHPULSE) * (V(VMSTARTCMD) - V(VMSTART_LATCH)) / match_tau\n"
    st += "CKUSTART KUSTART_LATCH 0 {sample_c} ic=0\n"
    st += "RKUSTART KUSTART_LATCH 0 1e15\n"
    st += "BKUSTART KUSTART_LATCH 0 I = -{sample_c} * V(VMLATCHPULSE) * (V(KUSTARTCMD) - V(KUSTART_LATCH)) / match_tau\n"
    st += "CKDSTART KDSTART_LATCH 0 {sample_c} ic=0\n"
    st += "RKDSTART KDSTART_LATCH 0 1e15\n"
    st += "BKDSTART KDSTART_LATCH 0 I = -{sample_c} * V(VMLATCHPULSE) * (V(KDSTARTCMD) - V(KDSTART_LATCH)) / match_tau\n"
    st += "CVMT0 VMT0 0 {sample_c} ic=0\n"
    st += "RVMT0 VMT0 0 1e15\n"
    st += "BVMT0 VMT0 0 I = -{sample_c} * V(VMLATCHPULSE) * (time*{time_scale} - V(VMT0)) / match_tau\n"
    st += "B37 VMELAPSED 0 V = (V(HVMATCH) > 0.05) ? max(0, time*{time_scale} - V(VMT0) - vm_edge_delay_ns) : 0.0\n"
    st += "B37A VMARG 0 V = V(VMSTART_LATCH) + V(VMELAPSED)\n"
    st += "B37B KUARG 0 V = V(KUSTART_LATCH) + V(VMELAPSED)\n"
    st += "B37C KDARG 0 V = V(KDSTART_LATCH) + V(VMELAPSED)\n"
    st += "B37D VMARG_BACKSTEP 0 V = 0.0\n"
    st += "B38 START_DISAGREE 0 V = (V(NINX) > 0.5) ? abs(V(TR_KU) - V(TR_KD)) : abs(V(TF_KU) - V(TF_KD))\n"
    st += "B39 MATCH_AMBIGUOUS 0 V = (V(START_DISAGREE) > 0.5) ? 1.0 : 0.0\n\n"

    if split_mode:
        st += create_ngspice_k_lookup_source_from_arg("B40", "KURM", "KUARG", kr[:, _TIME], kr[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B41", "KDRM", "KDARG", kr[:, _TIME], kr[:, _KD])
        st += create_ngspice_k_lookup_source_from_arg("B42", "KUFM", "KUARG", kf[:, _TIME], kf[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B43", "KDFM", "KDARG", kf[:, _TIME], kf[:, _KD])
    else:
        st += create_ngspice_k_lookup_source_from_arg("B40", "KURM", "VMARG", kr[:, _TIME], kr[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B41", "KDRM", "VMARG", kr[:, _TIME], kr[:, _KD])
        st += create_ngspice_k_lookup_source_from_arg("B42", "KUFM", "VMARG", kf[:, _TIME], kf[:, _KU])
        st += create_ngspice_k_lookup_source_from_arg("B43", "KDFM", "VMARG", kf[:, _TIME], kf[:, _KD])
    st += "B44 KUMATCH 0 V = (V(NINX) > 0.5) ? V(KURM) : V(KUFM)\n"
    st += "B45 KDMATCH 0 V = (V(NINX) > 0.5) ? V(KDRM) : V(KDFM)\n"
    st += "B46 MATCH_ERR_KU 0 V = abs(V(KUMATCH) - V(KUSAMP))\n"
    st += "B47 MATCH_ERR_KD 0 V = abs(V(KDMATCH) - V(KDSAMP))\n"
    st += "B48 HVMATCHCMD 0 V = (V(VMACTIVATE) > 0.5) ? 1.0 : ((V(VMARG) < vm_end_ns) ? V(HVMATCH) : 0.0)\n"
    st += "CHVMATCH HVMATCH 0 {sample_c} ic=0\n"
    st += "RHVMATCH HVMATCH 0 1e15\n"
    st += "BHVMATCH HVMATCH 0 I = -{sample_c} * (V(HVMATCHCMD) - V(HVMATCH)) / match_tau\n\n"

    st += "* Keep the sampled state selected continuously from reverse-edge detect until value-match replay owns the target.\n"
    st += "B48A HVMHOLDTARGET 0 V = (V(HREVERSE_EDGE) > 0.5) ? 1.0 : ((V(HVMATCH) > 0.05) ? 0.0 : V(HVMPENDING))\n"
    st += "CHVMPENDING HVMPENDING 0 {sample_c} ic=0\n"
    st += "RHVMPENDING HVMPENDING 0 1e15\n"
    st += "B48B HVMPENDING 0 I = -{sample_c} * (V(HVMHOLDTARGET) - V(HVMPENDING)) / match_tau\n"
    st += "B48C HPREHOLD 0 V = (V(VMSAMPLE) > 0.5 || V(VMLATCHPULSE) > 0.5 || V(VMACTIVATE) > 0.5 || V(HVMPENDING) > 0.05) ? 1.0 : 0.0\n"
    st += "B48D KUPENDING 0 V = (V(VMSAMPLE) > 0.5) ? V(KUPRE) : V(KUSAMP)\n"
    st += "B48E KDPENDING 0 V = (V(VMSAMPLE) > 0.5) ? V(KDPRE) : V(KDSAMP)\n"
    st += "B49 KUTARGET 0 V = (V(HVMATCH) > 0.05) ? V(KUMATCH) : ((V(HPREHOLD) > 0.5) ? V(KUPENDING) : V(KULEG))\n"
    st += "B50 KDTARGET 0 V = (V(HVMATCH) > 0.05) ? V(KDMATCH) : ((V(HPREHOLD) > 0.5) ? V(KDPENDING) : V(KDLEG))\n"
    st += "B50A COEFF_JUMP_KU 0 V = 0.0\n"
    st += "B50B COEFF_JUMP_KD 0 V = 0.0\n"
    st += "B51 Ku 0 V = V(KUTARGET)\n"
    st += "B52 Kd 0 V = V(KDTARGET)\n\n"
    return st


def create_ngspice_input_control_netlist(kr, kf, ibis_data):
    """
    Creates SPISim-style input edge timing and K-coefficient selection logic.
    """
    if str(getattr(ibis_data, "enable", "")).lower() == "active-low":
        enable_expr = "(V(EN,VSS) < {enable_threshold})"
    else:
        enable_expr = "(V(EN,VSS) > {enable_threshold})"

    st = ""
    st += "* Input-driven waveform coefficient control\n"
    st += "* This follows the SPISim free-spice waveform flow: threshold IN, use a\n"
    st += "* short T-line for one-step edge differentiation, latch the scaled edge\n"
    st += "* time through another T-line, and evaluate Ku/Kd versus elapsed ns.\n"
    st += "B10 NINX 0 V = (V(IN,VSS) > {input_threshold}) ? 1.0 : 0.0\n"
    st += f"B11 NENABLE 0 V = {enable_expr} ? 1.0 : 0.0\n"
    st += "B12 NI 0 V = V(NINX) - 0.5\n"
    st += "B13 N2 0 V = V(NI,N9) * 8\n"
    st += "B14 N3 0 V = abs(V(N2))\n"
    st += "B15 N4 0 V = (V(N3) > 0.5) ? 1 : -1\n"
    st += "B16 N5 0 V = (V(N4) > 0) ? time*{time_scale} : 0\n"
    st += "B17 N6 0 V = (V(N4) > 0) ? V(N5) : V(N8)\n"
    st += "B18 NX 0 V = (V(N6) >= 1.0) ? time*{time_scale} - V(N8) : 0.0\n"
    st += "T1 N6 0 N8 0 Z0=50 Td={edge_delay}\n"
    st += "T2 NI 0 N9 0 Z0=50 Td={edge_delay}\n"
    st += "R5 N8 0 50\n"
    st += "R6 N9 0 50\n\n"

    if ibis_data.model_type.lower() == "open_drain":
        st += create_ngspice_k_lookup_source("B20", "KDR0", kr[:, _TIME], kr[:, _KD_OD])
        st += create_ngspice_k_lookup_source("B21", "KDF0", kf[:, _TIME], kf[:, _KD_OD])
        st += "B22 NKDF 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 || V(N2) < -0.1) ? 0 : V(KDF0)) : 1\n"
        st += "B23 NKDR 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 && V(N3) < 0.1) ? V(KDR0) : 1) : 1\n"
        st += "B24 Kd 0 V = (V(NENABLE) > 0.5) ? "
        st += "((V(N6) > 0.5) ? ((V(NI) > 0 && V(N2) > -0.1) ? V(NKDR) : V(NKDF)) : 1) : 0\n\n"
    else:
        st += create_ngspice_k_lookup_source("B20", "KUR0", kr[:, _TIME], kr[:, _KU])
        st += create_ngspice_k_lookup_source("B21", "KDR0", kr[:, _TIME], kr[:, _KD])
        st += create_ngspice_k_lookup_source("B22", "KUF0", kf[:, _TIME], kf[:, _KU])
        st += create_ngspice_k_lookup_source("B23", "KDF0", kf[:, _TIME], kf[:, _KD])
        st += "B24 NKUF 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 || V(N2) < -0.1) ? 1 : V(KUF0)) : 0\n"
        st += "B25 NKDF 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 || V(N2) < -0.1) ? 0 : V(KDF0)) : 1\n"
        st += "B26 NKUR 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 && V(N3) < 0.1) ? V(KUR0) : 0) : 0\n"
        st += "B27 NKDR 0 V = (V(N6) > 0.5) ? "
        st += "((V(NI) > 0 && V(N3) < 0.1) ? V(KDR0) : 1) : 1\n"
        st += "B28 Ku 0 V = (V(NENABLE) > 0.5) ? "
        st += "((V(N6) > 0.5) ? ((V(NI) > 0 && V(N2) > -0.1) ? V(NKUR) : V(NKUF)) : 0) : 0\n"
        st += "B29 Kd 0 V = (V(NENABLE) > 0.5) ? "
        st += "((V(N6) > 0.5) ? ((V(NI) > 0 && V(N2) > -0.1) ? V(NKDR) : V(NKDF)) : 1) : 0\n\n"

    return st


def get_nominal_vcc(ibis_data, corner):
    """
    Returns the nominal VCC for the selected corner.
    """
    _INDEX = convert_corner_str_to_index(corner)
    if ibis_data.v_range is not None and ibis_data.v_range[_INDEX] is not None:
        return float(ibis_data.v_range[_INDEX])
    if ibis_data.v_range is not None and ibis_data.v_range[0] is not None:
        return float(ibis_data.v_range[0])
    return 0.0


def format_voltage_offset(value):
    """
    Formats small voltage-source offsets cleanly.
    """
    if abs(value) < 1e-15:
        return "0"
    return f"{value}"


def spice_rlc_netlist_with_supply(ibis_data, corner, pin_name):
    """
    Returns package parasitics referenced to the explicit VSS pin.
    """
    st = spice_rlc_netlist(ibis_data, corner, pin_name)
    st = st.replace(f'C1 {pin_name} 0 {{C_pkg}}', f'C1 {pin_name} VSS {{C_pkg}}')
    st = st.replace('C2 DIE 0 {C_comp}', 'C2 DIE VSS {C_comp}')
    return st


def define_pwr_and_gnd_clamps_with_supply(ibis_data, corner):
    """
    Defines clamp branches using explicit VCC/VSS pins.
    """
    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1
    nominal_vcc = get_nominal_vcc(ibis_data, corner)

    pwr_clamp_ref = pybis2spice.get_reference(ibis_data.pwr_clamp_ref, ibis_data.v_range, _CORNER_INDEX)
    gnd_clamp_ref = pybis2spice.get_reference(ibis_data.gnd_clamp_ref, 0, _CORNER_INDEX)

    return_val = ""
    if ibis_data.iv_pwr_clamp is not None:
        pwr_offset = format_voltage_offset(float(pwr_clamp_ref) - nominal_vcc)
        return_val += f'V1 PWR_CLAMP_REF VCC {pwr_offset}\n'
        pwr_clamp_table_str = convert_iv_table_to_str(np.flip(pwr_clamp_ref - ibis_data.iv_pwr_clamp[:, 0]),
                                                      np.flip(ibis_data.iv_pwr_clamp[:, _CORNER_INDEX]))
        return_val += f'B1 DIE PWR_CLAMP_REF I = pwl(V(DIE,VSS), {pwr_clamp_table_str})\n'

    if ibis_data.iv_gnd_clamp is not None:
        gnd_offset = format_voltage_offset(float(gnd_clamp_ref))
        return_val += f'V2 GND_CLAMP_REF VSS {gnd_offset}\n'
        gnd_clamp_table_str = convert_iv_table_to_str(ibis_data.iv_gnd_clamp[:, 0] - gnd_clamp_ref,
                                                      ibis_data.iv_gnd_clamp[:, _CORNER_INDEX])
        return_val += f'B2 DIE GND_CLAMP_REF I = pwl(V(DIE,VSS), {gnd_clamp_table_str})\n\n'

    return return_val


def define_pullup_and_pulldown_devices_with_supply(ibis_data, corner):
    """
    Defines PU/PD branches using explicit VCC/VSS pins.
    """
    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1
    nominal_vcc = get_nominal_vcc(ibis_data, corner)

    pullup_ref = pybis2spice.get_reference(ibis_data.pullup_ref, ibis_data.v_range, _CORNER_INDEX)
    pulldown_ref = pybis2spice.get_reference(ibis_data.pulldown_ref, 0, _CORNER_INDEX)

    return_val = ""
    if ibis_data.iv_pullup is not None:
        pullup_offset = format_voltage_offset(float(pullup_ref) - nominal_vcc)
        return_val += f'V3 PULLUP_REF VCC {pullup_offset}\n'
        pullup_table_str = convert_iv_table_to_str(np.flip(pullup_ref - ibis_data.iv_pullup[:, 0]),
                                                   np.flip(ibis_data.iv_pullup[:, _CORNER_INDEX]))
        return_val += f'B3 DIE PULLUP_REF I={{V(Ku)*pwl(V(DIE,VSS), {pullup_table_str})}}\n'

    if ibis_data.iv_pulldown is not None:
        pulldown_offset = format_voltage_offset(float(pulldown_ref))
        return_val += f'V4 PULLDOWN_REF VSS {pulldown_offset}\n'
        pulldown_table_str = convert_iv_table_to_str(ibis_data.iv_pulldown[:, 0] - pulldown_ref,
                                                     ibis_data.iv_pulldown[:, _CORNER_INDEX])
        return_val += f'B4 DIE PULLDOWN_REF I={{V(Kd)*pwl(V(DIE,VSS), {pulldown_table_str})}}\n\n'

    return return_val


def create_ngspice_input_driven_output_model(ibis_data, corner, io_type, output_filepath,
                                             compress_threshold=1e-3, state_continuous=False,
                                             coeff_state=False, short_pulse_hybrid=None,
                                             gate_state_mode=None,
                                             directional_gate_state_mode=None,
                                             charge_limited_gate_mode=None,
                                             value_matched_replay_mode=None,
                                             value_matched_replay_v2_mode=None,
                                             two_state_gate_mode=None):
    """
    Creates an ngspice output model with a real input pin.

    The output IV/clamp/package network is the same pybis2spice network used by
    the generic model. The default stimulus is SPISim-style: input edges reset a
    time-since-edge signal, and waveform-derived Ku/Kd curves are evaluated
    from that edge time. The state-continuous variant is opt-in and reverses a
    continuous progress state when an edge interrupts the previous transition.
    """
    if io_type != "Output":
        return 1

    return_val = 0
    try:
        _INDEX = convert_corner_str_to_index(corner)
        _CORNER_INDEX = _INDEX + 1

        if ibis_data.model_type.lower() == "open_drain":
            kr = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX,
                                                              waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX,
                                                              waveform_type="Falling")
        else:
            kr = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")

        kr = pybis2spice.compress_param(kr, threshold=compress_threshold)
        kf = pybis2spice.compress_param(kf, threshold=compress_threshold)

        threshold = estimate_input_threshold(ibis_data, corner)
        subckt_name = sanitize_ngspice_identifier(f'{ibis_data.model_name}-OutputInput-{corner}')

        if two_state_gate_mode is not None:
            extra_info = "* Note: InputDrivenTwoStateGate exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN drives continuous GUP/GDN hidden gate states mapped to Ku/Kd.\n"
        elif value_matched_replay_v2_mode is not None:
            extra_info = "* Note: InputDrivenValueMatchedReplayV2 exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN reverse edges latch Ku/Kd and replay from a fresh VMELAPSED timer.\n"
        elif value_matched_replay_mode is not None:
            extra_info = "* Note: InputDrivenValueMatchedReplay exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN edges sample Ku/Kd and retime replay from inverse coefficient maps.\n"
        elif charge_limited_gate_mode is not None:
            extra_info = "* Note: InputDrivenChargeLimitedGate exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN drives bounded QPU/QPD charge states and charge-mapped Ku/Kd diagnostics.\n"
        elif directional_gate_state_mode is not None:
            extra_info = "* Note: InputDrivenDirectionalGateState exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN drives independent KU_ON/KU_OFF/KD_OFF/KD_ON directional states.\n"
        elif gate_state_mode is not None:
            extra_info = "* Note: InputDrivenGateState exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN drives hidden GUP/GDN gate states and gate-mapped Ku/Kd diagnostics.\n"
        elif short_pulse_hybrid is not None:
            extra_info = "* Note: InputDrivenShortPulseHybrid exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN normally uses legacy Ku/Kd, with short-high-pulse correction diagnostics.\n"
        elif coeff_state:
            extra_info = "* Note: InputDrivenCoeffState exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN drives independent continuous Ku/Kd delayed coefficient states.\n"
        elif state_continuous:
            extra_info = "* Note: InputDrivenStateContinuous exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN edges drive continuous PSTATE/KUTARGET/KDTARGET coefficient logic.\n"
        else:
            extra_info = "* Note: NgSpiceInputDriven exposes OUT IN EN VCC VSS pins.\n"
            extra_info += "* IN edges trigger waveform-derived Ku/Kd coefficient curves.\n"

        spice_text = spice_header_info(ibis_data, corner, extra_info=extra_info)
        spice_text += f'.SUBCKT {subckt_name} OUT IN EN VCC VSS '
        spice_text += f'params: input_threshold={threshold} enable_threshold={threshold} '
        spice_text += f'edge_delay=10p time_scale=1e9\n\n'
        spice_text += spice_rlc_netlist_with_supply(ibis_data, corner, pin_name="OUT")
        spice_text += define_pwr_and_gnd_clamps_with_supply(ibis_data, corner)
        spice_text += define_pullup_and_pulldown_devices_with_supply(ibis_data, corner)
        if two_state_gate_mode is not None:
            spice_text += create_ngspice_two_state_gate_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=two_state_gate_mode,
            )
        elif value_matched_replay_v2_mode is not None:
            spice_text += create_ngspice_value_matched_replay_v2_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=value_matched_replay_v2_mode,
            )
        elif value_matched_replay_mode is not None:
            spice_text += create_ngspice_value_matched_replay_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=value_matched_replay_mode,
            )
        elif charge_limited_gate_mode is not None:
            spice_text += create_ngspice_charge_limited_gate_state_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=charge_limited_gate_mode,
            )
        elif directional_gate_state_mode is not None:
            spice_text += create_ngspice_directional_gate_state_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=directional_gate_state_mode,
            )
        elif gate_state_mode is not None:
            spice_text += create_ngspice_gate_state_input_control_netlist(
                kr,
                kf,
                ibis_data,
                mode=gate_state_mode,
            )
        elif short_pulse_hybrid is not None:
            spice_text += create_ngspice_short_pulse_hybrid_input_control_netlist(
                kr,
                kf,
                ibis_data,
                strategy=short_pulse_hybrid,
            )
        elif coeff_state:
            spice_text += create_ngspice_coeff_state_input_control_netlist(kr, kf, ibis_data)
        elif state_continuous:
            spice_text += create_ngspice_state_continuous_input_control_netlist(kr, kf, ibis_data)
        else:
            spice_text += create_ngspice_input_control_netlist(kr, kf, ibis_data)
        spice_text += ".ENDS\n"

        with open(output_filepath, 'w') as file:
            file.write(spice_text)
    except:
        return_val = 1

    return return_val


def convert_corner_str_to_index(corner):
    """
    Coverts the corner string into an index number used to reference the arrays within pybis2spice methods
    Parameters:
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns:
        index - 0, 1, 2 corresponding to the corner string "Typical", "WeakSlow" and "FastStrong" respectively
    """
    index = 0
    if corner == "Typical":
        index = 0
    if corner == "WeakSlow":
        index = 1
    if corner == "FastStrong":
        index = 2

    return index


def spice_header_info(ibis_data, corner, extra_info=""):
    """
    Returns a header string for the ibis file. Helps create a comment on the SPICE subcircuit file

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
    """
    st = "*********************************************************************\n*\n"
    st += f'* IBIS filename: {ibis_data.file_name}\n'
    st += f'* Component: {ibis_data.component_name}\n'
    st += f'* Model: {ibis_data.model_name}\n'
    st += f'* Model Type: {ibis_data.model_type}\n'
    st += f'* Corner: {corner}\n'
    st += f'* Voltage Range (V): {ibis_data.v_range} (Typ, Min, Max)\n'
    st += f'* Temperature Range (degC): {ibis_data.temp_range} (Typ, Min, Max)\n'
    st += f'* SPICE subcircuit model created with pybis2spice version {version.get_version()}\n'
    st += f'* For more info, visit https://github.com/kamratia1/pybis2spice/\n*\n'
    st += f'{extra_info}'
    st += "*********************************************************************\n\n"
    return st


def spice_rlc_netlist(ibis_data, corner, pin_name):
    """
    Returns a netlist string for the r_pkg, l_pkg,  c_comp

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
    """
    _INDEX = convert_corner_str_to_index(corner)
    c_pkg = ibis_data.c_pkg[_INDEX]
    l_pkg = ibis_data.l_pkg[_INDEX]
    r_pkg = ibis_data.r_pkg[_INDEX]
    st = ""

    if c_pkg is None:
        st += f'.param C_pkg = {ibis_data.c_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the C_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for C_pkg\n'
    elif c_pkg == 0:
        st += '.param C_pkg = 0\n'
        st += '* Exact zero from IBIS [Package]; keep zero for consistency\n'
    else:
        st += f'.param C_pkg = {c_pkg}\n'

    if l_pkg is None:
        st += f'.param L_pkg = {ibis_data.l_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the L_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for L_pkg\n'
    elif l_pkg == 0:
        st += '.param L_pkg = 0\n'
        st += '* Exact zero from IBIS [Package]; keep zero for consistency\n'
    else:
        st += f'.param L_pkg = {l_pkg}\n'

    if r_pkg is None:
        st += f'.param R_pkg = {ibis_data.r_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the R_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for R_pkg\n'
    elif r_pkg == 0:
        st += '.param R_pkg = 0\n'
        st += '* Exact zero from IBIS [Package]; keep zero for consistency\n'
    else:
        st += f'.param R_pkg = {r_pkg}\n'

    st += f'.param C_comp = {ibis_data.c_comp[_INDEX]}\n\n'

    st += f'R1 {pin_name} MID {{R_pkg}}\n'
    st += f'L1 DIE MID {{L_pkg}}\n'
    st += f'C1 {pin_name} 0 {{C_pkg}}\n'
    st += f'C2 DIE 0 {{C_comp}}\n\n'

    return st


def define_pwr_and_gnd_clamps(ibis_data, corner):
    """
    Arbitrary Source definition for power and ground clamp
    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns the netlist for the arbitrary source
    """

    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1

    pwr_clamp_ref = pybis2spice.get_reference(ibis_data.pwr_clamp_ref, ibis_data.v_range, _CORNER_INDEX)
    gnd_clamp_ref = pybis2spice.get_reference(ibis_data.gnd_clamp_ref, 0, _CORNER_INDEX)

    return_val = ""

    # Arbitrary Source definition for power and ground clamp
    if ibis_data.iv_pwr_clamp is not None:
        return_val += f'V1 PWR_CLAMP_REF 0 {pwr_clamp_ref}\n'
        pwr_clamp_table_str = convert_iv_table_to_str(np.flip(pwr_clamp_ref - ibis_data.iv_pwr_clamp[:, 0]),
                                                      np.flip(ibis_data.iv_pwr_clamp[:, _CORNER_INDEX]))
        return_val += f'B1 DIE PWR_CLAMP_REF I = table(V(DIE), {pwr_clamp_table_str})\n'

    if ibis_data.iv_gnd_clamp is not None:
        return_val += f'V2 GND_CLAMP_REF 0 {gnd_clamp_ref}\n'
        gnd_clamp_table_str = convert_iv_table_to_str(ibis_data.iv_gnd_clamp[:, 0] - gnd_clamp_ref,
                                                      ibis_data.iv_gnd_clamp[:, _CORNER_INDEX])
        return_val += f'B2 DIE GND_CLAMP_REF I = table(V(DIE), {gnd_clamp_table_str})\n\n'

    return return_val


def define_pullup_and_pulldown_devices(ibis_data, corner):
    """
    Arbitrary Source definition for pullup and pulldown devices
    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns the netlist for the arbitrary source for the devices
    """

    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1

    pullup_ref = pybis2spice.get_reference(ibis_data.pullup_ref, ibis_data.v_range, _CORNER_INDEX)
    pulldown_ref = pybis2spice.get_reference(ibis_data.pulldown_ref, 0, _CORNER_INDEX)

    return_val = ""
    # Arbitrary Source definition for pullup and pulldown devices
    if ibis_data.iv_pullup is not None:
        return_val += f'V3 PULLUP_REF 0 {pullup_ref}\n'
        pullup_table_str = convert_iv_table_to_str(np.flip(pullup_ref - ibis_data.iv_pullup[:, 0]),
                                                   np.flip(ibis_data.iv_pullup[:, _CORNER_INDEX]))
        return_val += f'B3 DIE PULLUP_REF I={{V(Ku)*table(V(DIE), {pullup_table_str})}}\n'

    if ibis_data.iv_pulldown is not None:
        return_val += f'V4 PULLDOWN_REF 0 {pulldown_ref}\n'
        pulldown_table_str = convert_iv_table_to_str(ibis_data.iv_pulldown[:, 0] - pulldown_ref,
                                                     ibis_data.iv_pulldown[:, _CORNER_INDEX])
        return_val += f'B4 DIE PULLDOWN_REF I={{V(Kd)*table(V(DIE), {pulldown_table_str})}}\n\n'

    return return_val


def create_input_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates a SPICE generic subcircuit model.
    Generic models are simple and only supports a single oscillation pulse with a given frequency

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        output_filepath - path of output file
    """

    with open(output_filepath, 'w') as file:

        header = spice_header_info(ibis_data, corner)
        file.write(header)

        file.write(f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} IN\n\n')

        rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="IN")
        file.write(rlc_netlist)

        clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
        file.write(clamps_netlist)

        file.write(f'.ENDS\n')

    return 0


def create_generic_output_model(ibis_data, corner, io_type, output_filepath, compress_threshold=1e-6):
    """
    Creates a SPICE generic subcircuit model.
    Generic models are simple and only supports a single oscillation pulse with a given frequency

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        k_param_rise - the k_parameter numpy array for the rising waveform (output of the solve_k_params_output method)
        k_param_fall - the k_parameter numpy array for the falling waveform (output of the solve_k_params_output method)
        output_filepath - path of output file

    Returns 0 if there are no errors in the creation
    """
    return_val = 0
    try:
        _INDEX = convert_corner_str_to_index(corner)
        _CORNER_INDEX = _INDEX + 1

        if ibis_data.model_type.lower() == "open_drain":
            kr = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")
        else:
            kr = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")

        kr = pybis2spice.compress_param(kr, threshold=compress_threshold)
        kf = pybis2spice.compress_param(kf, threshold=compress_threshold)

        with open(output_filepath, 'w') as file:
            header = spice_header_info(ibis_data, corner)
            file.write(header)

            file.write(f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} OUT params: freq=10Meg duty=0.5\n\n')

            rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="OUT")
            file.write(rlc_netlist)

            clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
            file.write(clamps_netlist)

            device_netlist = define_pullup_and_pulldown_devices(ibis_data, corner)
            file.write(device_netlist)

            # Calculations to define the oscillation stimulus
            if ibis_data.model_type.lower() == "open_drain":
                k_d_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD], kf[:, _TIME], kf[:, _KD_OD])
            else:
                k_u_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KU], kf[:, _TIME], kf[:, _KU])
                k_d_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD], kf[:, _TIME], kf[:, _KD])

            (offset_neg_r, offset_pos_r) = determine_crossover_offsets(kr)
            (offset_neg_f, offset_pos_f) = determine_crossover_offsets(kf)

            file.write(f'* Define Oscillation Sources\n')
            file.write(f'.param calc_gap_pos = {{(duty/freq) - {offset_pos_r} - {offset_neg_f}}}\n')
            file.write(f'.param calc_gap_neg = {{((1-duty)/freq) - {offset_pos_f} - {offset_neg_r}}}\n\n')

            file.write(f'.param GAP_POS = {{if(calc_gap_pos <= 0, 0.1e-12, calc_gap_pos)}}\n')
            file.write(f'.param GAP_NEG = {{if(calc_gap_neg <= 0, 0.1e-12, calc_gap_neg)}}\n\n')

            if ibis_data.model_type.lower() != "open_drain":
                file.write(f'V5 Ku 0 PWL({k_u_osc_str})\n\n')

            file.write(f'V6 Kd 0 PWL({k_d_osc_str})\n\n')

            file.write(f'.ENDS\n')
    except:
        return_val = 1

    return return_val


def ltspice_stimulus_netlist_setup():
    """
    Returns a netlist string that sets up the LTSpice stimulus sources for the model
    """
    # Setup the Stimulus setting options for the Pullup Waveform (Ku)
    setup_str = ".model SW SW(Ron=1n Roff=1G Vt=.5 Vh=-.4)\n\n"
    setup_str += "\n* Setup the Stimulus setting options for the Pullup Waveform (Ku)\n"
    setup_str += "V10 OSC 0 {if(stimulus_==1, 1, 0)}\n"
    setup_str += "V11 OSC_INV 0 {if(stimulus_==2, 1, 0)}\n"
    setup_str += "V12 RISE 0 {if(stimulus_==3, 1, 0)}\n"
    setup_str += "V13 FALL 0 {if(stimulus_==4, 1, 0)}\n"
    setup_str += "V14 HIGH 0 {if(stimulus_==5, 1, 0)}\n"
    setup_str += "V15 LOW 0 {if(stimulus_==6, 1, 0)}\n"
    setup_str += "S1 Ku K_U_OSC OSC 0 SW\n"
    setup_str += "S2 Ku K_U_OSC_INV OSC_INV 0 SW\n"
    setup_str += "S3 Ku K_U_RISE RISE 0 SW\n"
    setup_str += "S4 Ku K_U_FALL FALL 0 SW\n"
    setup_str += "S5 Ku K_U_HIGH HIGH 0 SW\n"
    setup_str += "S6 Ku K_U_LOW LOW 0 SW\n"

    # Setup the Stimulus setting options for the Pulldown Waveform (Kd)
    setup_str += "\n* Setup the Stimulus setting options for the Pulldown Waveform (Kd)\n"
    setup_str += "S7 Kd K_D_OSC OSC 0 SW\n"
    setup_str += "S8 Kd K_D_OSC_INV OSC_INV 0 SW\n"
    setup_str += "S9 Kd K_D_RISE RISE 0 SW\n"
    setup_str += "S10 Kd K_D_FALL FALL 0 SW\n"
    setup_str += "S11 Kd K_D_HIGH HIGH 0 SW\n"
    setup_str += "S12 Kd K_D_LOW LOW 0 SW\n"

    return setup_str


def create_ltspice_output_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates a SPICE subcircuit model designed for LTSpice.
    LTSpice specific models provide extra functionality to manipulate the waveform stimulus of the output

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        output_filepath - path of output file

    Returns 0 if there are no errors in the creation
    """

    return_val = 0
    try:
        _INDEX = convert_corner_str_to_index(corner)
        _CORNER_INDEX = _INDEX + 1

        if ibis_data.model_type.lower() == "open_drain":
            kr = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")
        else:
            kr = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")

        kr = pybis2spice.compress_param(kr)
        kf = pybis2spice.compress_param(kf)

        with open(output_filepath, 'w') as file:

            parameter_info = "* Note: This model may only work in LTSpice.\n"
            parameter_info += "* Stimulus Options: \n" \
                              "*\t1 - Oscillate at given freq and duty\n" \
                              "*\t2 - Inverted Oscillate at given freq and duty\n" \
                              "*\t3 - Rising Edge with delay\n" \
                              "*\t4 - Falling Edge with delay\n" \
                              "*\t5 - Stuck High\n" \
                              "*\t6 - Stuck Low\n" \
                              "*\t7 - HighZ (if 3-State output)\n\n"
            header = spice_header_info(ibis_data, corner, extra_info=parameter_info)
            file.write(header)

            subcircuit = f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} '
            subcircuit_params = f'OUT params: stimulus=1 freq=10Meg duty=0.5 delay=0 \n\n'

            file.write(subcircuit + subcircuit_params)

            rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="OUT")
            file.write(rlc_netlist)

            clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
            file.write(clamps_netlist)

            device_netlist = define_pullup_and_pulldown_devices(ibis_data, corner)
            file.write(device_netlist)

            stimulus_netlist = ltspice_stimulus_netlist_setup() # Look at this in more detail
            file.write(stimulus_netlist)

            (offset_neg_r, offset_pos_r) = determine_crossover_offsets(kr)
            (offset_neg_f, offset_pos_f) = determine_crossover_offsets(kf)

            # Calculations for defining the frequency and duty cycle of the oscillation stimuli'
            file.write(f'\n* Define Oscillation Sources\n')
            file.write(f'.param calc_gap_pos = {{(duty/freq) - {offset_pos_r} - {offset_neg_f}}}\n')
            file.write(f'.param calc_gap_neg = {{((1-duty)/freq) - {offset_pos_f} - {offset_neg_r}}}\n\n')
            file.write(f'.param GAP_POS = {{if(calc_gap_pos <= 0, 0.1e-12, calc_gap_pos)}}\n')
            file.write(f'.param GAP_NEG = {{if(calc_gap_neg <= 0, 0.1e-12, calc_gap_neg)}}\n\n')

            max_stimulus = 6
            if ibis_data.model_type.lower() == "3-state":
                max_stimulus = 7

            # Limit the stimulus between 1 and 7
            file.write(f'.param stimulus_ = {{if(stimulus < 1, 1, '
                       f'if(stimulus > {max_stimulus}, {max_stimulus}, stimulus)}}\n\n')

            # Oscillation Strings
            if ibis_data.model_type.lower() == "open_drain":
                kd_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD], kf[:, _TIME], kf[:, _KD_OD])
            else:
                ku_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KU], kf[:, _TIME], kf[:, _KU])
                kd_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD], kf[:, _TIME], kf[:, _KD])

            if ibis_data.model_type.lower() == "open_drain":
                kd_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KD_OD], kr[:, _TIME], kr[:, _KD_OD])
            else:
                ku_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KU], kr[:, _TIME], kr[:, _KU])
                kd_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KD], kr[:, _TIME], kr[:, _KD])

            # Rising Edge Strings
            if ibis_data.model_type.lower() == "open_drain":
                kdr_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD])
            else:
                kur_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KU])
                kdr_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KD])

            # Falling Edge Strings
            if ibis_data.model_type.lower() == "open_drain":
                kdf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KD_OD])
            else:
                kuf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KU])
                kdf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KD])

            if ibis_data.model_type.lower() != "open_drain":
                # Setup the K-Parameter waveforms for the Pullup transistor (Ku)
                file.write(f"V16 K_U_OSC 0 PWL REPEAT FOREVER ({ku_osc_str}) ENDREPEAT\n")
                file.write(f"V17 K_U_HIGH 0 1\n")
                file.write(f"V18 K_U_LOW 0 0\n")
                file.write(f"V19 K_U_OSC_INV 0 PWL REPEAT FOREVER ({ku_inv_osc_str}) ENDREPEAT\n")
                file.write(f"V20 K_U_RISE 0 PWL({kur_str})\n")
                file.write(f"V21 K_U_FALL 0 PWL({kuf_str})\n")

            # Setup the K-Parameter waveforms for the Pullup transistor (Kd)
            file.write(f"V36 K_D_OSC 0 PWL REPEAT FOREVER ({kd_osc_str}) ENDREPEAT\n")
            file.write(f"V37 K_D_HIGH 0 0\n")
            file.write(f"V38 K_D_LOW 0 1\n")
            file.write(f"V39 K_D_OSC_INV 0 PWL REPEAT FOREVER ({kd_inv_osc_str}) ENDREPEAT\n")
            file.write(f"V40 K_D_RISE 0 PWL({kdr_str})\n")
            file.write(f"V41 K_D_FALL 0 PWL({kdf_str})\n")

            if ibis_data.model_type.lower() == "3-state":
                file.write("V50 EN 0 {if(stimulus==7, 1, 0)}\n")
                file.write("S13 Ku 0 EN 0 SW\n")
                file.write("S14 Kd 0 EN 0 SW\n")

            file.write(f'\n.ENDS\n')
    except:
        return_val = 1

    return return_val


def create_ltspice_symbol(ibis_data, corner, model_path, io_type):
    """
    Creates an LTSpice symbol for the given model_path within the model_path directory
    This helps with the relative referencing of the model_path within the symbol file.
    The symbol is given the same name as the model for consistency.

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        model_path - filepath of the subcircuit model
        io_type - "Input" or "Output"

    Returns the filepath of the created symbol
    """
    symbol_path = os.path.join(os.path.dirname(model_path), f'{ibis_data.model_name}-{io_type}-{corner}.asy')
    symbol_value = f'{ibis_data.model_name}-{io_type}-{corner}'
    model_filename = os.path.basename(model_path)

    with open(symbol_path, 'w') as file:
        if io_type == "Input":
            file.write(f"Version 4\n")
            file.write(f"SymbolType BLOCK\n")
            file.write(f"LINE Normal 0 32 48 64\n")
            file.write(f"LINE Normal 0 96 48 64\n")
            file.write(f"LINE Normal 0 96 0 32\n")
            file.write(f"WINDOW 0 8 16 Left 2\n")
            file.write(f"WINDOW 3 8 120 Left 2\n")
            file.write(f"SYMATTR Value {symbol_value}\n")
            file.write(f"SYMATTR Prefix X\n")
            file.write(f"SYMATTR ModelFile {model_filename}\n")
            file.write(f"PIN 0 64 NONE 0\n")
            file.write(f"PINATTR PinName IN\n")
            file.write(f"PINATTR SpiceOrder 1\n")

        if io_type == "Output":
            file.write(f"Version 4\n")
            file.write(f"SymbolType BLOCK\n")
            file.write(f"LINE Normal -16 0 32 -32\n")
            file.write(f"LINE Normal -16 -64 -16 0\n")
            file.write(f"LINE Normal 32 -32 -16 -64\n")
            file.write(f"WINDOW 0 0 -80 Bottom 2\n")
            file.write(f"WINDOW 3 8 24 Top 2\n")
            file.write(f"WINDOW 39 8 48 Top 2\n")
            file.write(f"SYMATTR Value {symbol_value}\n")
            file.write(f"SYMATTR SpiceLine stimulus=1 freq=10Meg duty=0.5 delay=0\n")
            file.write(f"SYMATTR Prefix X\n")
            file.write(f"SYMATTR ModelFile {model_filename}\n")
            file.write(f"PIN 32 -32 NONE 8\n")
            file.write(f"PINATTR PinName OUT\n")
            file.write(f"PINATTR SpiceOrder 1\n")

    return symbol_path


def convert_iv_table_to_str(voltage, current):
    """
    Creates the IV table of values for the current sources modelling the devices and clamps

        Parameters:
            voltage - numpy voltage array
            current - corresponding numpy current array

        Returns:
            str_val: the string that goes into subcircuit table
    """
    str_val = f'{voltage[0]}, {current[0]}'
    for i in range(1, len(voltage)):
        str_val = str_val + f', {voltage[i]}, {current[i]}'
    return str_val


def create_edge_waveform_pwl(time, k_param):
    """
    Creates the PWL value string for the oscillation waveform
    Only valid for LTSpice subcircuit

        Parameters:
            time - numpy time array for k parameter waveform
            k_param - numpy array for k_r or k_f waveform

        Returns:
            str_val: the string that goes into PWL source for the edge
    """
    str_val = f'{{delay}}, {k_param[0]}'
    for i in range(1, len(time)):
        str_val = str_val + f', {{delay+{time[i]}}}, {k_param[i]}'
    return str_val


def create_osc_waveform_pwl(t1, k1, t2, k2):
    """
    Creates the PWL value string for the oscillation waveform

        Parameters:
            t1 - numpy time array for first edge (rising or falling)
            t2 - numpy time array for second edge (rising or falling)
            k1 - numpy ku or kd array for first edge (rising or falling)
            k2 - numpy ku or kd array for second edge (rising or falling)

        Returns:
            str_val: the string that goes into the oscillator PWL source
    """

    # First Edge
    # the +0.01p fudge is for Simetrix as it seems to have a bug in its PWLS source
    # where it cannot start at any value other than 0 regardless of the k_r[0] value
    str_val = f'0 {k1[0]} +0.01e-12 {k1[0]}'
    for i in range(1, len(t1)):
        dt = t1[i] - t1[i - 1]
        str_val = str_val + f' +{dt} {k1[i]}'

    str_val = str_val + f' +{{GAP_POS}} {k1[-1]} +{t2[0]} {k2[0]}'

    # Second Edge
    for i in range(1, len(t2)):
        dt = t2[i] - t2[i - 1]
        str_val = str_val + f' +{dt} {k2[i]}'

    str_val = str_val + f' +{{GAP_NEG}} {k2[-1]}'

    # gap_pos and gap_neg are parameters calculated within SPICE to oscillate at the right frequency and duty
    return str_val


def determine_crossover_offsets(k_param):
    """
    returns the approximate crossover point between the rising and falling k_param waveforms
        offset_neg: Time offset between beginning of k_param to crossover point
        offset_neg: Time offset between crossover point to end of k_param
    """

    # crossover time point (x_t)
    if np.shape(k_param)[1] == 3:
        # Find the index of the minimum value of the difference between k_u and k_d
        index = np.argmin(np.absolute(k_param[:, 1] - k_param[:, 2]))
        x_t = k_param[index, 0]
    else:
        # Find the index of the value at the halfway voltage point of the k-param waveform
        index = np.argmin((np.max(k_param[:, 1]) - np.min(k_param[:, 1]))/2)
        x_t = k_param[index, 0]

    # Time offset
    offset_neg = x_t - k_param[0][0]
    offset_pos = k_param[:, 0][-1] - x_t

    return offset_neg, offset_pos

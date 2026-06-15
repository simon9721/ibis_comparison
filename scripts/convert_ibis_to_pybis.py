from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
if str(PYBIS_ROOT) not in sys.path:
    sys.path.insert(0, str(PYBIS_ROOT))

from pybis2spice import pybis2spice, subcircuit  # noqa: E402


def convert(
    ibis_path: Path,
    output_path: Path,
    component_name: str,
    model_name: str,
    io_type: str,
    subcircuit_type: str,
    corner: str,
) -> Path:
    ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
    data_model = pybis2spice.DataModel(ibis, model_name=model_name, component_name=component_name)
    if not hasattr(data_model, "model"):
        raise RuntimeError(f"failed to load model {model_name!r} / component {component_name!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ret = subcircuit.generate_spice_model(
        io_type=io_type,
        subcircuit_type=subcircuit_type,
        ibis_data=data_model,
        corner=corner,
        output_filepath=str(output_path),
    )
    if ret != 0:
        raise RuntimeError(f"pybis2spice conversion failed with return code {ret}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert an IBIS model to an ngspice-ready pybis2spice subcircuit.")
    parser.add_argument("ibis", type=Path, help="Input IBIS file")
    parser.add_argument("--component", required=True, help="IBIS component name")
    parser.add_argument("--model", required=True, help="IBIS model name")
    parser.add_argument("--out", type=Path, required=True, help="Output .sub file")
    parser.add_argument("--io-type", default="Output", choices=["Input", "Output"])
    parser.add_argument("--subcircuit-type", default="InputDriven")
    parser.add_argument("--corner", default="Typical", choices=["Typical", "WeakSlow", "FastStrong"])
    parser.add_argument("--list", action="store_true", help="Print parsed components/models before converting")
    args = parser.parse_args()

    if args.list:
        ibis = pybis2spice.get_ibis_model_ecdtools(str(args.ibis))
        print("components:", ", ".join(pybis2spice.list_components(ibis)))
        print("models:", ", ".join(pybis2spice.list_models(ibis)))

    output_path = convert(
        ibis_path=args.ibis,
        output_path=args.out,
        component_name=args.component,
        model_name=args.model,
        io_type=args.io_type,
        subcircuit_type=args.subcircuit_type,
        corner=args.corner,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

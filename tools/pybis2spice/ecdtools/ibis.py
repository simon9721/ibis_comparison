from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class TypMinMax:
    typical: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    def __float__(self) -> float:
        if self.typical is None:
            raise TypeError("typical value is missing")
        return float(self.typical)


@dataclass
class Table:
    samples: list[list[float]]


@dataclass
class Waveform:
    table: Table
    r_fixture: float = 0.0
    v_fixture: TypMinMax = field(default_factory=TypMinMax)


@dataclass
class Package:
    r_pkg: TypMinMax = field(default_factory=TypMinMax)
    l_pkg: TypMinMax = field(default_factory=TypMinMax)
    c_pkg: TypMinMax = field(default_factory=TypMinMax)


@dataclass
class Component:
    name: str
    package: Package = field(default_factory=Package)


@dataclass
class Model:
    name: str
    model_type: str | None = None
    enable: str | None = None
    vinl: TypMinMax | None = None
    vinh: TypMinMax | None = None
    c_comp: TypMinMax | None = None
    voltage_range: TypMinMax | None = None
    temperature_range: TypMinMax | None = None
    pullup_reference: TypMinMax | None = None
    pulldown_reference: TypMinMax | None = None
    power_clamp_reference: TypMinMax | None = None
    gnd_clamp_reference: TypMinMax | None = None
    pullup: list[list[float]] | None = None
    pulldown: list[list[float]] | None = None
    power_clamp: list[list[float]] | None = None
    gnd_clamp: list[list[float]] | None = None
    ramp: object | None = None
    rising_waveforms: list[Waveform] = field(default_factory=list)
    falling_waveforms: list[Waveform] = field(default_factory=list)


class IbsFile:
    """Small IBIS parser that exposes the ecdtools surface pybis2spice uses.

    This is intentionally narrow: it parses component package parasitics,
    model scalar/range metadata, IV tables, and V/T waveform blocks.
    """

    def __init__(self, text: str, transform: bool = True):
        self.text = text
        self.transform = transform
        self.components: list[Component] = []
        self.models: list[Model] = []
        self.component_names: list[str] = []
        self.model_names: list[str] = []
        self.source_file_name: str | None = None
        self.file_name: str | None = None
        self._parse(text)

    def get_model_by_name(self, name: str) -> Model:
        for model in self.models:
            if model.name == name:
                return model
        raise KeyError(f"model not found: {name}")

    def get_component_by_name(self, name: str) -> Component:
        for component in self.components:
            if component.name == name:
                return component
        raise KeyError(f"component not found: {name}")

    def _parse(self, text: str) -> None:
        current_component: Component | None = None
        current_model: Model | None = None
        table_attr: str | None = None
        waveform_kind: str | None = None
        waveform_samples: list[list[float]] = []
        waveform_r_fixture = 0.0
        waveform_v_fixture = TypMinMax()

        def flush_waveform() -> None:
            nonlocal waveform_kind, waveform_samples, waveform_r_fixture, waveform_v_fixture
            if waveform_kind is not None and current_model is not None:
                waveform = Waveform(
                    table=Table(waveform_samples),
                    r_fixture=waveform_r_fixture,
                    v_fixture=waveform_v_fixture,
                )
                if waveform_kind == "rising":
                    current_model.rising_waveforms.append(waveform)
                else:
                    current_model.falling_waveforms.append(waveform)
            waveform_kind = None
            waveform_samples = []
            waveform_r_fixture = 0.0
            waveform_v_fixture = TypMinMax()

        for raw_line in text.splitlines():
            line = _strip_comment(raw_line)
            if not line:
                continue

            header = _parse_header(line)
            if header is not None:
                flush_waveform()
                name, rest = header
                name_l = name.lower()
                table_attr = None

                if name_l == "component":
                    current_component = Component(rest.strip())
                    self.components.append(current_component)
                    continue

                if name_l == "model":
                    current_model = Model(rest.strip())
                    self.models.append(current_model)
                    continue

                if current_model is not None:
                    if name_l == "pulldown":
                        current_model.pulldown = []
                        table_attr = "pulldown"
                        continue
                    if name_l == "pullup":
                        current_model.pullup = []
                        table_attr = "pullup"
                        continue
                    if name_l == "power clamp":
                        current_model.power_clamp = []
                        table_attr = "power_clamp"
                        continue
                    if name_l == "gnd clamp":
                        current_model.gnd_clamp = []
                        table_attr = "gnd_clamp"
                        continue
                    if name_l == "rising waveform":
                        waveform_kind = "rising"
                        waveform_samples = []
                        waveform_r_fixture = 0.0
                        waveform_v_fixture = TypMinMax()
                        continue
                    if name_l == "falling waveform":
                        waveform_kind = "falling"
                        waveform_samples = []
                        waveform_r_fixture = 0.0
                        waveform_v_fixture = TypMinMax()
                        continue
                    if name_l == "voltage range":
                        current_model.voltage_range = _parse_typ_min_max(rest)
                        continue
                    if name_l == "temperature range":
                        current_model.temperature_range = _parse_typ_min_max(rest)
                        continue
                    if name_l == "pullup reference":
                        current_model.pullup_reference = _parse_typ_min_max(rest)
                        continue
                    if name_l == "pulldown reference":
                        current_model.pulldown_reference = _parse_typ_min_max(rest)
                        continue
                    if name_l == "power clamp reference":
                        current_model.power_clamp_reference = _parse_typ_min_max(rest)
                        continue
                    if name_l == "gnd clamp reference":
                        current_model.gnd_clamp_reference = _parse_typ_min_max(rest)
                        continue
                    if name_l == "ramp":
                        current_model.ramp = []
                        continue

                continue

            if current_component is not None and current_model is None:
                _parse_component_line(current_component, line)
                continue

            if current_model is None:
                continue

            if waveform_kind is not None:
                parsed_fixture = _parse_waveform_fixture(line)
                if parsed_fixture is not None:
                    fixture_name, fixture_value = parsed_fixture
                    if fixture_name == "r_fixture":
                        waveform_r_fixture = fixture_value.typical or 0.0
                    elif fixture_name == "v_fixture":
                        waveform_v_fixture.typical = fixture_value.typical
                        if fixture_value.minimum is not None:
                            waveform_v_fixture.minimum = fixture_value.minimum
                        if fixture_value.maximum is not None:
                            waveform_v_fixture.maximum = fixture_value.maximum
                    elif fixture_name == "v_fixture_min":
                        waveform_v_fixture.minimum = fixture_value.typical
                    elif fixture_name == "v_fixture_max":
                        waveform_v_fixture.maximum = fixture_value.typical
                    continue

                sample = _parse_numeric_row(line, min_values=2)
                if sample is not None:
                    waveform_samples.append(_pad_sample(sample, 4))
                continue

            _parse_model_line(current_model, line)

            if table_attr is not None:
                row = _parse_numeric_row(line, min_values=4)
                if row is not None:
                    getattr(current_model, table_attr).append(row[:4])

        flush_waveform()
        self.components = [component for component in self.components if component.name]
        self.models = [model for model in self.models if model.name]
        self.component_names = [component.name for component in self.components]
        self.model_names = [model.name for model in self.models]
        for model in self.models:
            _finalize_model_tables(model)


def load_file(path: str, transform: bool = True) -> IbsFile:
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="latin1")
    ibis = IbsFile(text, transform=transform)
    ibis.source_file_name = str(file_path)
    ibis.file_name = str(file_path)
    return ibis


def _strip_comment(line: str) -> str:
    return line.split("|", 1)[0].strip()


def _parse_header(line: str) -> tuple[str, str] | None:
    match = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _parse_component_line(component: Component, line: str) -> None:
    parts = _split_assignment_or_words(line)
    if not parts:
        return
    key = parts[0].lower()
    if key == "r_pkg":
        component.package.r_pkg = _parse_typ_min_max(" ".join(parts[1:]))
    elif key == "l_pkg":
        component.package.l_pkg = _parse_typ_min_max(" ".join(parts[1:]))
    elif key == "c_pkg":
        component.package.c_pkg = _parse_typ_min_max(" ".join(parts[1:]))


def _parse_model_line(model: Model, line: str) -> None:
    parts = _split_assignment_or_words(line)
    if not parts:
        return
    key = parts[0].lower()
    values = " ".join(parts[1:])

    if key == "model_type":
        model.model_type = values.strip()
    elif key == "enable":
        model.enable = values.strip()
    elif key == "vinl":
        model.vinl = _parse_typ_min_max(values)
    elif key == "vinh":
        model.vinh = _parse_typ_min_max(values)
    elif key == "c_comp":
        model.c_comp = _parse_typ_min_max(values)
    elif key == "voltage_range":
        model.voltage_range = _parse_typ_min_max(values)
    elif key == "temperature_range":
        model.temperature_range = _parse_typ_min_max(values)
    elif key == "pullup_reference":
        model.pullup_reference = _parse_typ_min_max(values)
    elif key == "pulldown_reference":
        model.pulldown_reference = _parse_typ_min_max(values)
    elif key == "power_clamp_reference":
        model.power_clamp_reference = _parse_typ_min_max(values)
    elif key == "gnd_clamp_reference":
        model.gnd_clamp_reference = _parse_typ_min_max(values)


def _parse_waveform_fixture(line: str) -> tuple[str, TypMinMax] | None:
    parts = _split_assignment_or_words(line)
    if not parts:
        return None
    key = parts[0].lower()
    values = " ".join(parts[1:])
    if key == "r_fixture":
        return key, _parse_typ_min_max(values)
    if key in {"v_fixture", "v_fixture_min", "v_fixture_max"}:
        return key, _parse_typ_min_max(values)
    return None


def _split_assignment_or_words(line: str) -> list[str]:
    if "=" in line:
        left, right = line.split("=", 1)
        return [left.strip(), *right.strip().split()]
    return line.split()


def _parse_typ_min_max(text: str) -> TypMinMax:
    values = [_parse_number(token) for token in text.split()]
    while len(values) < 3:
        values.append(None)
    return TypMinMax(values[0], values[1], values[2])


def _parse_numeric_row(line: str, min_values: int) -> list[float] | None:
    tokens = line.replace(",", " ").split()
    values: list[float | None] = []
    for token in tokens:
        value = _parse_number(token)
        if value is None and token.strip().lower() not in {"na", "n/a", "nc", "-"}:
            return None
        values.append(value)
    if len(values) < min_values:
        return None
    first = values[0]
    typical = values[1] if len(values) > 1 else None
    if first is None or typical is None:
        return None
    return [_fill_missing(value, typical) for value in values]


def _pad_sample(values: list[float], width: int) -> list[float]:
    if len(values) >= width:
        return values[:width]
    fill = values[1] if len(values) > 1 else values[0]
    return values + [fill] * (width - len(values))


def _fill_missing(value: float | None, default: float) -> float:
    return float(default if value is None else value)


def _parse_number(token: str) -> float | None:
    text = token.strip().strip("()")
    if not text:
        return None
    if text.lower() in {"na", "n/a", "nc", "-"}:
        return None

    text = text.replace(",", "")
    match = re.match(
        r"^([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?)([A-Za-zµ]*)$",
        text,
    )
    if match is None:
        return None

    number = float(match.group(1))
    suffix = match.group(2).lower().replace("\u00b5", "u")
    return number * _suffix_multiplier(suffix)


def _suffix_multiplier(suffix: str) -> float:
    if not suffix:
        return 1.0
    if suffix.startswith("meg"):
        return 1e6
    if suffix[0] == "t":
        return 1e12
    if suffix[0] == "g":
        return 1e9
    if suffix[0] == "k":
        return 1e3
    if suffix[0] == "m":
        return 1e-3
    if suffix[0] == "u":
        return 1e-6
    if suffix[0] == "n":
        return 1e-9
    if suffix[0] == "p":
        return 1e-12
    if suffix[0] == "f":
        return 1e-15
    return 1.0


def _finalize_model_tables(model: Model) -> None:
    for attr in ("pullup", "pulldown", "power_clamp", "gnd_clamp"):
        if getattr(model, attr) == []:
            setattr(model, attr, None)

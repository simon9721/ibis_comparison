import unittest
from pathlib import Path
import tempfile
import subprocess
import shutil
from pybis2spice import pybis2spice
from pybis2spice import subcircuit
import numpy as np
import ecdtools
from ecdtools.ibis import TypMinMax

TEST_DIR = Path(__file__).resolve().parent
IBIS_DIR = TEST_DIR / "ibis"
REPO_DIR = TEST_DIR.parent
SPICE_DIR = REPO_DIR.parent
NGSPICE_BIN = SPICE_DIR / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"


def load_test_ibis(filename):
    return ecdtools.ibis.load_file(str(IBIS_DIR / filename), transform=True)


def find_ngspice_bin():
    if NGSPICE_BIN.exists():
        return NGSPICE_BIN

    fallback = shutil.which("ngspice")
    if fallback is not None:
        return Path(fallback)

    return None


class TestPybis2Spice(unittest.TestCase):

    def test_extract_range_param(self):
        # Test an empty TypMinMax object
        data = TypMinMax()
        data.typical = None
        data.minimum = None
        data.maximum = None
        self.assertEqual(pybis2spice.extract_range_param(data), None)

        data.typical = 1e-9
        data.minimum = 8.341E-02
        np.testing.assert_equal(pybis2spice.extract_range_param(data), [1e-9, 8.341E-02, None])

        data.typical = None
        data.minimum = None
        data.maximum = 3e-12
        np.testing.assert_equal(pybis2spice.extract_range_param(data), [None, None, 3e-12])

        # Test values from some test Ibis files
        ibis = load_test_ibis('bird57ex.ibs')
        component = ibis.get_component_by_name('BIRD57ex')
        np.testing.assert_equal(pybis2spice.extract_range_param(component.package.r_pkg), [0.1, None, None])
        np.testing.assert_equal(pybis2spice.extract_range_param(component.package.l_pkg), [8e-9, None, None])
        np.testing.assert_equal(pybis2spice.extract_range_param(component.package.c_pkg), [5e-12, None, None])

        ibis = load_test_ibis('hct1g08.ibs')
        component = ibis.get_component_by_name('74HCT1G08_GW')
        model = ibis.get_model_by_name('HCT1G08_IN_50')
        self.assertEqual(pybis2spice.extract_range_param(model.pullup_reference), None)
        np.testing.assert_equal(pybis2spice.extract_range_param(model.c_comp), [2.8774e-12, 1.2578e-12, 5.2328e-12])
        np.testing.assert_equal(pybis2spice.extract_range_param(component.package.r_pkg),
                                [8.353E-02, 8.341E-02, 8.366E-02])

    def test_extract_iv_table(self):
        ibis = load_test_ibis('bushold.ibs')
        model = ibis.get_model_by_name('TOP_MODEL_BUS_HOLD')

        from decimal import Decimal
        test = [(Decimal('2'), Decimal('0'), Decimal('0'), Decimal('0')),
                (Decimal('1'), Decimal('0'), Decimal('0'), Decimal('0'))]
        # Test the inversion
        np.testing.assert_equal(pybis2spice.extract_iv_table(test),
                                [[1, 0, 0, 0],
                                 [2, 0, 0, 0]])

        np.testing.assert_equal(pybis2spice.extract_iv_table(model.pullup),
                                [[-5.0e+00,  1.0e-04,  8.0e-05,  1.2e-04],
                                [-1.0e+00,  3.0e-05,  2.5e-05,  4.0e-05],
                                [0.0e+00,  0.0e+00,  0.0e+00,  0.0e+00],
                                [1.0e+00, -3.0e-05, -2.5e-05, -4.0e-05],
                                [3.0e+00, -5.0e-05, -4.5e-05, -5.0e-05],
                                [5.0e+00, -1.0e-04, -8.0e-05, -1.2e-04],
                                [1.0e+01, -1.2e-04, -9.0e-05, -1.5e-04]])

        np.testing.assert_equal(pybis2spice.extract_iv_table(model.gnd_clamp),
                                [[-2.0, -6.158e+17, np.nan, np.nan],
                                [-1.9, -1.697e+16, np.nan, np.nan],
                                [-1.8, -467900000000000.0, np.nan, np.nan],
                                [-1.7, -12900000000000.0, np.nan, np.nan],
                                [-1.6, -355600000000.0, np.nan, np.nan],
                                [-1.5, -9802000000.0, np.nan, np.nan],
                                [-1.4, -270200000.0, np.nan, np.nan],
                                [-1.3, -7449000.0, np.nan, np.nan],
                                [-1.2, -205300.0, np.nan, np.nan],
                                [-1.1, -5660.0, np.nan, np.nan],
                                [-1.0, -156.0, np.nan, np.nan],
                                [-0.9, -4.308, np.nan, np.nan],
                                [-0.8, -0.1221, np.nan, np.nan],
                                [-0.7, -0.004315, np.nan, np.nan],
                                [-0.6, -0.0001715, np.nan, np.nan],
                                [-0.5, -4.959e-06, np.nan, np.nan],
                                [-0.4, -1.373e-07, np.nan, np.nan],
                                [-0.3, -4.075e-09, np.nan, np.nan],
                                [-0.2, -3.044e-10, np.nan, np.nan],
                                [-0.1, -1.03e-10, np.nan, np.nan],
                                [0.0, 0.0, np.nan, np.nan],
                                [5.0, 0.0, np.nan, np.nan]])

        np.testing.assert_equal(pybis2spice.extract_iv_table(model.gnd_clamp),
                                [[-2.0, -6.158e+17, np.nan, np.nan],
                                 [-1.9, -1.697e+16, np.nan, np.nan],
                                 [-1.8, -467900000000000.0, np.nan, np.nan],
                                 [-1.7, -12900000000000.0, np.nan, np.nan],
                                 [-1.6, -355600000000.0, np.nan, np.nan],
                                 [-1.5, -9802000000.0, np.nan, np.nan],
                                 [-1.4, -270200000.0, np.nan, np.nan],
                                 [-1.3, -7449000.0, np.nan, np.nan],
                                 [-1.2, -205300.0, np.nan, np.nan],
                                 [-1.1, -5660.0, np.nan, np.nan],
                                 [-1.0, -156.0, np.nan, np.nan],
                                 [-0.9, -4.308, np.nan, np.nan],
                                 [-0.8, -0.1221, np.nan, np.nan],
                                 [-0.7, -0.004315, np.nan, np.nan],
                                 [-0.6, -0.0001715, np.nan, np.nan],
                                 [-0.5, -4.959e-06, np.nan, np.nan],
                                 [-0.4, -1.373e-07, np.nan, np.nan],
                                 [-0.3, -4.075e-09, np.nan, np.nan],
                                 [-0.2, -3.044e-10, np.nan, np.nan],
                                 [-0.1, -1.03e-10, np.nan, np.nan],
                                 [0.0, 0.0, np.nan, np.nan],
                                 [5.0, 0.0, np.nan, np.nan]])

    def test_adjust_device_data(self):
        device = np.asarray([[0, 10, 10, 10], [1, 10, 10, 10], [2, 10, 10, 10]])
        clamp = np.asarray([[0, 0, 0, 0], [1, 0, 0, 0], [2, 0, 0, 0]])
        clamp_pos = np.asarray([[0, 1, 1, 1], [1, 1, 1, 1], [2, 1, 1, 1]])
        clamp_neg = np.asarray([[0, -1, -1, -1], [1, -1, -1, -1], [2, -1, -1, -1]])
        result1 = pybis2spice.adjust_device_data(device, clamp)
        result2 = pybis2spice.adjust_device_data(device, clamp_pos)
        result3 = pybis2spice.adjust_device_data(device, clamp_neg)

        device2 = np.asarray([[0, 10, 10, 10], [-1, 10, 10, 10], [-2, 10, 10, 10]])
        clamp2 = np.asarray([[0, 0, 0, 0], [-1, 0, 0, 0], [-2, 0, 0, 0]])
        clamp2_pos = np.asarray([[0, 1, 1, 1], [-1, 1, 1, 1], [-2, 1, 1, 1]])
        clamp2_neg = np.asarray([[0, -1, -1, -1], [-1, -1, -1, -1], [-2, -1, -1, -1]])
        result4 = pybis2spice.adjust_device_data(device2, clamp2)
        result5 = pybis2spice.adjust_device_data(device2, clamp2_pos)
        result6 = pybis2spice.adjust_device_data(device2, clamp2_neg)

        # interpolate
        device3 = np.asarray([[0, 0, 0, 0], [1, 1, 1, 1], [2, 2, 2, 2]])
        clamp3 = np.asarray([[0, 0, 0, 0], [1.5, 1.5, 1.5, 1.5], [2, 2, 2, 2]])
        result7 = pybis2spice.adjust_device_data(device3, clamp3)

        np.testing.assert_equal(result1, np.asarray([[0, 10, 10, 10], [1, 10, 10, 10], [2, 10, 10, 10]]))
        np.testing.assert_equal(result2, np.asarray([[0, 9, 9, 9], [1, 9, 9, 9], [2, 9, 9, 9]]))
        np.testing.assert_equal(result3, np.asarray([[0, 11, 11, 11], [1, 11, 11, 11], [2, 11, 11, 11]]))
        np.testing.assert_equal(result4, np.asarray([[0, 10, 10, 10], [-1, 10, 10, 10], [-2, 10, 10, 10]]))
        np.testing.assert_equal(result5, np.asarray([[0, 9, 9, 9], [-1, 9, 9, 9], [-2, 9, 9, 9]]))
        np.testing.assert_equal(result6, np.asarray([[0, 11, 11, 11], [-1, 11, 11, 11], [-2, 11, 11, 11]]))
        np.testing.assert_equal(result7, np.asarray([[0, 0, 0, 0], [1, 0, 0, 0], [2, 0, 0, 0]]))

    def test_increasing(self):
        self.assertEqual(pybis2spice.increasing([0, 0, 0, 0]), True)
        self.assertEqual(pybis2spice.increasing([0, 1, 0, 0]), False)
        self.assertEqual(pybis2spice.increasing([0, 1, 2, 3]), True)
        self.assertEqual(pybis2spice.increasing([0, 1, 1, 39000]), True)

    def test_get_current_data_from_iv_data(self):
        # TODO test_get_current_data_from_iv_data
        pass

    def test_get_reference(self):
        v_range = np.asarray([4.5, 5, 5.5])
        ref1 = np.asarray([3, 3.3, 3.6])
        ref2 = None

        # Test when the ref parameter is not None. The output should be equal to the v_range
        self.assertEqual(pybis2spice.get_reference(ref1, v_range, 1), 3)
        self.assertEqual(pybis2spice.get_reference(ref1, v_range, 2), 3.3)
        self.assertEqual(pybis2spice.get_reference(ref1, v_range, 3), 3.6)

        # Test when the ref parameter is None. The output should be equal to the v_range
        self.assertEqual(pybis2spice.get_reference(ref2, v_range, 1), 4.5)
        self.assertEqual(pybis2spice.get_reference(ref2, v_range, 2), 5)
        self.assertEqual(pybis2spice.get_reference(ref2, v_range, 3), 5.5)

        # Testing when v_range parameter is 0, so the output should be 0
        self.assertEqual(pybis2spice.get_reference(ref2, 0, 1), 0)
        self.assertEqual(pybis2spice.get_reference(ref2, 0, 2), 0)
        self.assertEqual(pybis2spice.get_reference(ref2, 0, 3), 0)

    def test_generating_current_data(self):
        # TODO test_generating_current_data
        pass

    def test_solve_k_params_output(self):
        # TODO test_solve_k_params_output
        pass

    def test_differentiate(self):
        np.testing.assert_equal(pybis2spice.differentiate([0, 1, 2, 3], [0, 1, 2, 3]), [1, 1, 1, 1])
        np.testing.assert_equal(pybis2spice.differentiate([1, 1, 1, 1], [0, 1, 2, 3]), [0, 0, 0, 0])
        np.testing.assert_equal(pybis2spice.differentiate([10, 10, 200, 20], [0, 1, 2, 3]), [0, 190, -180, -180])

    def test_compress_param(self):
        k_param = np.asarray([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 1, 1], [4, 2, 2], [5, 2, 2], [6, 2, 2]])
        k_compressed = np.asarray([[0, 0, 0], [2, 0, 0], [3, 1, 1], [6, 2, 2]])

        np.testing.assert_equal(pybis2spice.compress_param(k_param), k_compressed)

        #np.testing.assert_equal(pybis2spice.compress_param([4, 4, 3, 2, 1, 0, 0]), [4, 3, 2, 1, 0])
        #np.testing.assert_equal(pybis2spice.compress_param([4, 4, 3, 2, 1, 0, 0], threshold=1.5), [4, 4, 3, 2, 1, 0, 0])
        #np.testing.assert_equal(pybis2spice.compress_param([4.6, 4, 3, 2, 1, 0.6, 0.2], threshold=0.5), [4, 3, 2, 1, 0.6, 0.2])

    def test_waveform_scalar_v_fixture_and_input_threshold_metadata(self):
        ibis = load_test_ibis('sn74lvc2t45.ibs')
        ibis_data = pybis2spice.DataModel(ibis, 'LVC2T45_IO_A_18', 'LVC2T45_DCT')

        np.testing.assert_equal(ibis_data.vt_rising[0].v_fix, [0.0, 0.0, 0.0])
        self.assertTrue(np.all(np.isfinite(ibis_data.vt_falling[0].v_fix)))
        self.assertEqual(ibis_data.enable, 'Active-Low')
        self.assertAlmostEqual(float(ibis_data.vinl), 0.5775)
        self.assertAlmostEqual(float(ibis_data.vinh), 1.2675)

    def test_sanitize_ibis_numeric_tokens_adds_leading_zero(self):
        text = "C_pkg 0.141pF  .133pF  -.149pF\nR_pkg .1m 1m +.2m\n"
        sanitized = pybis2spice.sanitize_ibis_numeric_tokens(text)
        self.assertIn("0.133pF", sanitized)
        self.assertIn("-0.149pF", sanitized)
        self.assertIn("0.1m", sanitized)
        self.assertIn("+0.2m", sanitized)

    def test_parse_spice_numeric_token(self):
        self.assertAlmostEqual(pybis2spice.parse_spice_numeric_token("20.0000pF"), 20e-12)
        self.assertAlmostEqual(pybis2spice.parse_spice_numeric_token("1.0k"), 1000.0)
        self.assertAlmostEqual(pybis2spice.parse_spice_numeric_token("0.5"), 0.5)

    def test_extract_waveform_fixture_metadata(self):
        ibis_text = "\n".join(
            [
                "[Model] TEST_MODEL",
                "[Rising Waveform]",
                "R_fixture = 50",
                "V_fixture = 0.0",
                "C_fixture = 20.0000pF",
                "[Rising Waveform]",
                "R_fixture = 50",
                "V_fixture = 1.2",
                "C_fixture = 10.0000pF",
                "[Falling Waveform]",
                "R_fixture = 50",
                "V_fixture = 0.0",
                "C_fixture = 30.0000pF",
                "| End [Model] TEST_MODEL",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            ibis_path = Path(temp_dir) / "fixture_test.ibs"
            ibis_path.write_text(ibis_text, encoding="utf-8")
            meta = pybis2spice.extract_waveform_fixture_metadata(str(ibis_path), "TEST_MODEL")

        self.assertEqual(len(meta["rising"]), 2)
        self.assertEqual(len(meta["falling"]), 1)
        self.assertAlmostEqual(meta["rising"][0]["c_fix"], 20e-12)
        self.assertAlmostEqual(meta["rising"][1]["c_fix"], 10e-12)
        self.assertAlmostEqual(meta["falling"][0]["c_fix"], 30e-12)

    def test_spice_rlc_netlist_preserves_exact_zero_package(self):
        class DummyData:
            c_pkg = [0.0, None, None]
            l_pkg = [0.0, None, None]
            r_pkg = [0.0, None, None]
            c_comp = [1.2e-12, 1.2e-12, 1.2e-12]

        text = subcircuit.spice_rlc_netlist(DummyData(), "Typical", pin_name="OUT")
        self.assertIn('.param C_pkg = 0', text)
        self.assertIn('.param L_pkg = 0', text)
        self.assertIn('.param R_pkg = 0', text)
        self.assertIn('Exact zero from IBIS [Package]; keep zero for consistency', text)
        self.assertNotIn('therefore this has been set to the typical value', text)

    def test_generate_input_driven_output_model(self):
        ibis = load_test_ibis('sn74lvc2t45.ibs')
        ibis_data = pybis2spice.DataModel(ibis, 'LVC2T45_IO_A_18', 'LVC2T45_DCT')

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'ng_input_driven.sub'
            ret = subcircuit.generate_spice_model(io_type="Output",
                                                  subcircuit_type="InputDriven",
                                                  ibis_data=ibis_data,
                                                  corner="Typical",
                                                  output_filepath=str(output_path))
            self.assertEqual(ret, 0)

            text = output_path.read_text()
            self.assertIn('.SUBCKT LVC2T45_IO_A_18_OutputInput_Typical OUT IN EN VCC VSS', text)
            self.assertIn('B11 NENABLE 0 V = (V(EN,VSS) < {enable_threshold}) ? 1.0 : 0.0', text)
            self.assertIn('T1 N6 0 N8 0 Z0=50 Td={edge_delay}', text)
            self.assertIn('T2 NI 0 N9 0 Z0=50 Td={edge_delay}', text)
            self.assertIn('time*{time_scale}', text)
            self.assertIn('V(NI) > 0 && V(N2) > -0.1', text)
            self.assertIn('pwl(min(max(V(NX), 0),', text)
            self.assertNotIn('table(', text)

    def test_generate_input_driven_input_model_falls_back_to_ngspice_input_path(self):
        ibis = load_test_ibis('hct1g08.ibs')
        ibis_data = pybis2spice.DataModel(ibis, 'HCT1G08_IN_50', '74HCT1G08_GW')

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'ng_inputdriven_input.sub'
            ret = subcircuit.generate_spice_model(io_type="Input",
                                                  subcircuit_type="InputDriven",
                                                  ibis_data=ibis_data,
                                                  corner="Typical",
                                                  output_filepath=str(output_path))
            self.assertEqual(ret, 0)

            text = output_path.read_text()
            self.assertIn('.SUBCKT HCT1G08_IN_50_Input_Typical', text)
            self.assertNotIn('OUT IN EN VCC VSS', text)
            self.assertIn('pwl(', text)

    def test_input_driven_aliases_normalize(self):
        self.assertEqual(subcircuit.normalize_subcircuit_type("InputDriven"), "InputDriven")
        self.assertEqual(subcircuit.normalize_subcircuit_type("Input-Driven"), "InputDriven")
        self.assertEqual(subcircuit.normalize_subcircuit_type("NgSpiceInputDriven"), "InputDriven")
        self.assertEqual(subcircuit.normalize_subcircuit_type("NgSpiceExternalInput"), "InputDriven")

    def test_generate_ngspice_generic_model_uses_pwl_syntax(self):
        ibis = load_test_ibis('hct1g08.ibs')
        ibis_data = pybis2spice.DataModel(ibis, 'HCT1G08_OUTN_50', '74HCT1G08_GW')

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'ng_generic.sub'
            ret = subcircuit.generate_spice_model(io_type="Output",
                                                  subcircuit_type="NgSpice",
                                                  ibis_data=ibis_data,
                                                  corner="Typical",
                                                  output_filepath=str(output_path))
            self.assertEqual(ret, 0)

            text = output_path.read_text()
            self.assertIn('.SUBCKT HCT1G08_OUTN_50_Output_Typical', text)
            self.assertIn('pwl(', text)
            self.assertNotIn('table(', text)

    def test_batch_generate_all_models_for_component(self):
        ibis = load_test_ibis('hct1g08.ibs')

        with tempfile.TemporaryDirectory() as temp_dir:
            results = subcircuit.generate_spice_models_for_all_models(
                ibis_model_ecdtools=ibis,
                component_name='74HCT1G08_GW',
                output_dir=temp_dir,
                io_type="Output",
                subcircuit_type="InputDriven",
                corner="Typical",
            )

            generated = results["generated"]
            skipped = results["skipped"]
            failed = results["failed"]

            self.assertEqual(len(generated), 1)
            self.assertEqual(len(skipped), 1)
            self.assertEqual(len(failed), 0)
            self.assertTrue(Path(generated[0]).exists())
            self.assertIn('HCT1G08_OUTN_50-Output-Typical.sub', Path(generated[0]).name)
            self.assertEqual(skipped[0]["model"], 'HCT1G08_IN_50')

    @unittest.skipUnless(find_ngspice_bin() is not None, "ngspice executable not available")
    def test_ngspice_input_driven_generated_model_smoke(self):
        ibis = load_test_ibis('sn74lvc2t45.ibs')
        ibis_data = pybis2spice.DataModel(ibis, 'LVC2T45_IO_A_18', 'LVC2T45_DCT')
        ngspice_bin = find_ngspice_bin()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            model_path = temp_path / 'driver.sub'
            raw_path = temp_path / 'smoke.raw'
            bench_path = temp_path / 'smoke.sp'

            ret = subcircuit.generate_spice_model(io_type="Output",
                                                  subcircuit_type="InputDriven",
                                                  ibis_data=ibis_data,
                                                  corner="Typical",
                                                  output_filepath=str(model_path))
            self.assertEqual(ret, 0)

            subckt_name = None
            for line in model_path.read_text().splitlines():
                if line.startswith('.SUBCKT '):
                    subckt_name = line.split()[1]
                    break
            self.assertIsNotNone(subckt_name)

            bench_path.write_text(
                "\n".join(
                    [
                        ".temp 27",
                        ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
                        "Vin in_src 0 PWL(0 0 1n 0 1.005n 1.8 5n 1.8 5.005n 0 8n 0)",
                        "Rin in_src in_dig 1",
                        "Ven en_sig 0 DC 0",
                        "Vdd vdd 0 DC 1.8",
                        ".include 'driver.sub'",
                        f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
                        "T1 pad 0 ntst 0 Z0=50 Td=30p",
                        "R1 ntst 0 50",
                        ".save V(in_dig) V(pad) V(ntst)",
                        ".tran 10p 8n",
                        ".end",
                        "",
                    ]
                )
            )

            proc = subprocess.run([str(ngspice_bin), "-b", "-r", str(raw_path.name), str(bench_path.name)],
                                  cwd=temp_path, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, msg=f"ngspice failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
            self.assertTrue(raw_path.exists())

            raw_bytes = raw_path.read_bytes()
            self.assertIn(b"Binary:\n", raw_bytes)
            header = raw_bytes.split(b"Binary:\n", 1)[0].decode("latin1")
            self.assertIn("No. Variables:", header)
            self.assertIn("No. Points:", header)
            self.assertGreater(raw_path.stat().st_size, 1024)

    #  TODO Test the functions for the subcircuit creation. Probably better to check the files


if __name__ == '__main__':
    unittest.main()

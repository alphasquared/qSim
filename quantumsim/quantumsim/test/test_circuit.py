import quantumsim.circuit as circuit
import quantumsim.ptm as ptm
from unittest.mock import MagicMock, patch, call, ANY
import numpy as np
import pytest


class TestCircuit:

    def test_add_qubit(self):
        c = circuit.Circuit()

        c.add_qubit(circuit.Qubit("A", t1=10, t2=20))

        assert len(c.gates) == 0
        assert len(c.qubits) == 1
        assert c.qubits[0].name == "A"

    def test_add_qubit_twice_raises_error(self):

        c = circuit.Circuit()

        c.add_qubit("A")

        with pytest.raises(ValueError) as excinfo:
            c.add_qubit("A")
            assert 'Trying to add qubit with name' in str(excinfo.value)

    def test_get_qubit_names(self):
        c = circuit.Circuit()
        c.add_qubit("A")
        c.add_qubit("B")
        c.add_qubit("C")

        assert set(c.get_qubit_names()) == {"A", "B", "C"}

    def test_order_regression_classical(self):
        c = circuit.Circuit("test")

        c.add_qubit("D", 1000, 1000)
        c.add_qubit("A", 1000, 1000)
        c.add_qubit("MA")
        c.add_qubit("SA")

        c.add_gate(circuit.RotateY("A", time=0, angle=np.pi / 2))
        c.add_gate(circuit.CPhase("A", "D", time=10))

        rotate_normal = circuit.RotateY("A", time=20, angle=-np.pi / 2)
        rotate_backwards = circuit.RotateY("A", time=20, angle=np.pi / 2)

        conditional_rotate1 = circuit.ConditionalGate(
            control_bit="SA", time=20, zero_gates=[rotate_normal],
            one_gates=[])
        c.add_gate(conditional_rotate1)

        conditional_rotate2 = circuit.ConditionalGate(
            control_bit="SA", time=30, zero_gates=[],
            one_gates=[rotate_backwards])
        c.add_gate(conditional_rotate2)

        sampler = circuit.BiasedSampler(readout_error=0.0015, alpha=1, seed=43)
        measurement = circuit.Measurement(
            "A", time=40, sampler=sampler, output_bit="MA")
        c.add_gate(measurement)
        c.add_gate(circuit.ClassicalCNOT("MA", "SA", time=35))

        assert len(c.gates) == 6

        c.order()

        assert len(c.gates) == 6

    def test_order_no_meas(self):
        c = circuit.Circuit()

        qb = circuit.Qubit("A", t1=10, t2=0)
        c.add_qubit(qb)

        c.add_gate(circuit.Hadamard("A", time=1))
        c.add_gate(circuit.Hadamard("A", time=0))

        c.order()

        assert len(c.gates) == 2
        assert c.gates[0].time == 0

    def test_order_no_gates(self):
        c = circuit.Circuit()
        c.add_qubit("A")
        c.add_qubit("B")

        c.order()

    def test_add_waiting_full(self):
        c = circuit.Circuit()

        qb = circuit.Qubit("A", t1=10, t2=0)
        c.add_qubit(qb)

        c.add_gate(circuit.Hadamard("A", time=1))
        c.add_gate(circuit.Hadamard("A", time=0))

        assert len(c.gates) == 2

        c.add_waiting_gates()

        assert len(c.gates) == 3

        c.order()

        assert c.gates[1].time == 0.5
        assert c.gates[1].duration == 1.0

    def test_add_waiting_empty(self):
        c = circuit.Circuit()

        c.add_qubit(circuit.Qubit("A", 0, 0))

        c.add_waiting_gates()

        assert len(c.gates) == 0

        c.add_waiting_gates(tmin=0, tmax=100)

        assert len(c.gates) == 1

    def test_add_waiting_partial(self):
        c = circuit.Circuit()
        c.add_qubit("A", 10, 10)
        c.add_qubit("B", 10, 10)

        assert len(c.gates) == 0

        c.add_waiting_gates(only_qubits=["A"], tmin=0, tmax=1)

        assert len(c.gates) == 1

        c.add_waiting_gates(only_qubits=["B"], tmin=0, tmax=1)

        assert len(c.gates) == 2

    def test_add_waiting_not_to_inf_qubits(self):
        c = circuit.Circuit()
        c.add_qubit("A")  # should have infinite lifetime by default
        # should have infinite lifetime by default
        c.add_qubit("B", np.inf, np.inf)
        c.add_qubit("C", 10, 10)

        c.add_waiting_gates(tmin=0, tmax=1)

        assert len(c.gates) == 1

    def test_add_no_waiting_classical_bit(self):
        c = circuit.Circuit()

        qa = circuit.ClassicalBit("A")

        c.add_qubit(qa)
        c.add_qubit("B", np.inf, np.inf)
        c.add_qubit("C", 10, 10)

        c.add_waiting_gates(tmin=0, tmax=1)

        assert len(c.gates) == 1

    def test_apply_to(self):
        sdm = MagicMock()
        sdm.hadamard = MagicMock()
        sdm.amp_ph_damping = MagicMock()
        sdm.apply_ptm = MagicMock()
        sdm.peak_measurement = MagicMock(return_value=(1, 0))
        sdm.project_measurement = MagicMock()

        c = circuit.Circuit()

        c.add_qubit(circuit.Qubit("A", 10, 20))
        c.add_gate(circuit.Hadamard("A", 0))
        c.add_gate(circuit.Hadamard("A", 10))

        with pytest.warns(UserWarning):
            c.add_gate(circuit.Measurement("A", 20, sampler=None))

        c.add_waiting_gates()

        c.order()

        c.apply_to(sdm)

        sdm.assert_has_calls([call.apply_ptm("A", ptm=ANY),
                              call.apply_ptm("A", ptm=ANY),
                              call.apply_ptm("A", ptm=ANY),
                              call.apply_ptm("A", ptm=ANY),
                              call.peak_measurement("A"),
                              call.project_measurement("A", 0)])

    def test_simplified_adding_qubit(self):
        c = circuit.Circuit()
        c.add_qubit("A", 10, 10)

        assert len(c.qubits) == 1
        assert c.qubits[0].name == 'A'

    def test_add_gate_by_class(self):
        c = circuit.Circuit()
        c.add_qubit("A", 10, 10)

        c.add_gate(circuit.Hadamard, "A", time=20)

        assert len(c.gates) == 1
        assert c.gates[0].time == 20

    def test_add_gate_by_class_name(self):
        c = circuit.Circuit()
        c.add_qubit("A", 10, 10)

        c.add_gate("hadamard", "A", time=20)

        assert len(c.gates) == 1
        assert c.gates[0].time == 20

        c.add_gate("cphase", "A", "B", time=30)

        assert len(c.gates) == 2
        assert c.gates[-1].time == 30

    def test_add_gate_by_getattr(self):
        c = circuit.Circuit()
        c.add_qubit("A", 10, 10)

        c.add_hadamard("A", time=20)
        c.add_rotate_y("A", time=20, angle=0)

        assert len(c.gates) == 2
        assert c.gates[0].time == 20

    def test_add_subcircuit_normal_use(self):
        c = circuit.Circuit()
        subc = circuit.Circuit()

        subc.add_qubit('A')

        subc.add_hadamard("A", 0)
        subc.add_hadamard("A", 5)

        c.add_qubit('Q')
        c.add_subcircuit(subc, time=0, name_map={'A': 'Q'})  # call with dict
        c.add_subcircuit(subc, time=10, name_map=['Q'])  # call with list

        assert len(c.gates) == 4
        assert {g.time for g in c.gates} == {0, 5, 10, 15}
        assert {g.involved_qubits[0] for g in c.gates} == {'Q'}

        c.add_qubit("A")
        c.add_subcircuit(subc, time=0)  # call with None

        assert len(c.gates) == 6
        assert {g.time for g in c.gates} == {0, 5, 10, 15}
        assert {g.involved_qubits[0] for g in c.gates} == {'Q', 'A'}


class TestVariableQubits:
    def test_add_gates(self):
        c = circuit.Circuit()

        qb = circuit.VariableDecoherenceQubit(
            "A", base_t1=10, base_t2=10, t1s=[
                (10, 20, 10)], t2s=[
                (10, 20, 10)])
        c.add_qubit(qb)

        c.add_gate(circuit.Hadamard("A", time=10))
        c.add_gate(circuit.Hadamard("A", time=0))
        c.add_gate(circuit.Hadamard("A", time=20))

        c.add_waiting_gates()
        c.order()

        assert c.gates[1].time == 5
        assert c.gates[1].duration == 10

        assert c.gates[1].t1 == 10
        assert c.gates[3].t1 == 5

    def test_averaging(self):
        c = circuit.Circuit()

        qb = circuit.VariableDecoherenceQubit(
            "A", base_t1=10, base_t2=10, t1s=[
                (10, 20, 10)], t2s=[
                (10, 20, 10)])
        c.add_qubit(qb)

        c.add_waiting_gates(tmin=0, tmax=100)
        c.order()

        assert c.gates[0].time == 50
        assert c.gates[0].duration == 100

        assert np.allclose(c.gates[0].t1, 10 / (9 / 10 + 1 / 5))


class TestHadamardGate:

    def test_init(self):
        h = circuit.Hadamard("A", 7)
        assert h.time == 7
        assert h.involves_qubit("A")
        assert not h.involves_qubit("B")
        assert not h.is_measurement

    def test_apply(self):
        sdm = MagicMock()
        sdm.apply_ptm = MagicMock()
        h = circuit.Hadamard("A", 7)
        h.apply_to(sdm)
        sdm.apply_ptm.assert_called_once_with("A", ptm=ANY)


class TestRotateYGate:

    def test_init(self):
        h = circuit.RotateY("A", 7, 0)
        assert h.time == 7
        assert h.involves_qubit("A")
        assert not h.involves_qubit("B")
        assert not h.is_measurement

        assert h.label == r"$R_y(0)$"

    def test_label_pi(self):
        h = circuit.RotateY("A", 7, np.pi)
        assert h.label == r"$R_y(\pi)$"

    def test_label_piover2(self):
        h = circuit.RotateY("A", 7, np.pi / 2)
        assert h.label == r"$R_y(\pi/2)$"

    def test_apply_piover2(self):
        sdm = MagicMock()
        sdm.apply_ptm = MagicMock()
        h = circuit.RotateY("A", 7, np.pi / 2)
        h.apply_to(sdm)
        sdm.apply_ptm.assert_called_once_with("A", ptm=ANY)

    def test_dephasing(self):

        a = 1

        g = circuit.RotateY("A", angle=a, time=0)
        g2 = circuit.RotateY("A", angle=a, time=0, dephasing_angle=0)
        g3 = circuit.RotateY("A", angle=a, time=0, dephasing_angle=1)

        assert np.allclose(g.ptm, g2.ptm)
        assert np.allclose(g3.ptm, ptm.dephasing_ptm(1, 0, 1))


class TestCPhaseGate:

    def test_init(self):
        cp = circuit.CPhase("A", "B", 10)
        assert cp.time == 10
        assert set(cp.involved_qubits) == {"A", "B"}
        assert not cp.is_measurement

    def test_apply(self):
        sdm = MagicMock()
        sdm.cphase = MagicMock()

        cp = circuit.CPhase("A", "B", 10)

        cp.apply_to(sdm)

        sdm.cphase.assert_called_once_with("A", "B")


class TestAmpPhDamping:

    def test_init(self):
        apd = circuit.AmpPhDamp("A", 0, 1, 10, 10)
        assert apd.time == 0
        assert apd.duration == 1
        assert apd.involves_qubit("A")
        assert not apd.is_measurement

    def test_apply(self):
        sdm = MagicMock()
        sdm.apply_ptm = MagicMock()

        apd = circuit.AmpPhDamp("A", 0, 1, 10, 5)

        apd.apply_to(sdm)

        sdm.apply_ptm.assert_called_once_with("A", ptm=ANY)


class TestMeasurement:

    def test_init(self):
        with pytest.warns(UserWarning):
            m = circuit.Measurement("A", 0, sampler=None)
        assert m.is_measurement
        assert m.involves_qubit("A")
        assert m.time == 0

    def test_apply_with_uniform_sampler(self):
        with pytest.warns(UserWarning):
            m = circuit.Measurement("A", 0, sampler=None)

        sdm = MagicMock()
        sdm.peak_measurement = MagicMock(return_value=(0, 1))
        sdm.project_measurement = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 1)

        sdm.peak_measurement = MagicMock(return_value=(1, 0))
        sdm.project_measurement = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1, 0]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 0)

    def test_apply_with_selection_sampler(self):
        m = circuit.Measurement("A", 0, sampler=circuit.selection_sampler(1))

        sdm = MagicMock()
        sdm.peak_measurement = MagicMock(return_value=(0, 1))
        sdm.project_measurement = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 1)

        sdm.peak_measurement = MagicMock(return_value=(1, 0))
        sdm.project_measurement = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1, 1]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 1)

    def test_apply_random(self):
        sampler = circuit.uniform_sampler(42)
        m = circuit.Measurement("A", 0, sampler=sampler)

        with patch('numpy.random.RandomState') as rsclass:
            rs = MagicMock()
            rsclass.return_value = rs
            rs.random_sample = MagicMock()
            p = rs.random_sample
            p.return_value = 0.3
            sdm = MagicMock()
            sdm.peak_measurement = MagicMock(return_value=(0.06, 0.04))
            sdm.project_measurement = MagicMock()

            m.apply_to(sdm)

            sdm.project_measurement.assert_called_once_with("A", 0)

            sdm.peak_measurement = MagicMock(return_value=(0.06, 0.04))
            sdm.project_measurement = MagicMock()
            p.return_value = 0.7

            m.apply_to(sdm)

            sdm.project_measurement.assert_called_once_with("A", 1)

    def test_output_bit(self):
        with pytest.warns(UserWarning):
            m = circuit.Measurement("A", 0, sampler=None, output_bit="O")

        sdm = MagicMock()
        sdm.peak_measurement = MagicMock(return_value=(0, 1))
        sdm.project_measurement = MagicMock()
        sdm.set_bit = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 1)
        sdm.set_bit.assert_called_once_with("O", 1)

        sdm.peak_measurement = MagicMock(return_value=(1, 0))
        sdm.project_measurement = MagicMock()
        sdm.set_bit = MagicMock()

        m.apply_to(sdm)

        assert m.measurements == [1, 0]

        sdm.peak_measurement.assert_called_once_with("A")
        sdm.project_measurement.assert_called_once_with("A", 0)
        sdm.set_bit.assert_called_once_with("O", 0)

    def test_one_sampler_two_measurements(self):
        # Biased sampler
        with pytest.warns(UserWarning):
            s = circuit.BiasedSampler(alpha=1, readout_error=0.7)
        m1 = circuit.Measurement("A", 0, sampler=s, output_bit="O")
        m2 = circuit.Measurement("A", 0, sampler=s, output_bit="O")

        # uniform sampler
        s = circuit.uniform_sampler(seed=42)
        m1 = circuit.Measurement("A", 0, sampler=s, output_bit="O")
        m2 = circuit.Measurement("A", 0, sampler=s, output_bit="O")

        # selection sampler
        s = circuit.selection_sampler(result=1)
        m1 = circuit.Measurement("A", 0, sampler=s, output_bit="O")
        m2 = circuit.Measurement("A", 0, sampler=s, output_bit="O")

        m1, m2


class TestConditionalGates:

    @pytest.mark.skip()
    def test_simple(self):
        sdm = MagicMock()
        sdm.classical = {"A": 0, "B": 1}
        sdm.apply_ptm = MagicMock()

        c = circuit.Circuit()

        c.add_gate("hadamard", "A", time=0, conditional_bit="B")

        c.apply_to(sdm)

        sdm.apply_ptm.assert_called_once_with("A", ptm=ANY)
        sdm.ensure_classical.assert_called_once_with("B")

        sdm = MagicMock()
        sdm.classical = {"A": 0, "B": 0}
        sdm.hadamard = MagicMock()

        c.apply_to(sdm)

        sdm.apply_ptm.assert_not_called()
        sdm.ensure_classical.assert_called_once_with("B")


class TestSamplers:

    def test_selection_sampler(self):
        s = circuit.selection_sampler(0)
        next(s)
        for _ in range(10):
            pr, dec, prob = s.send((0.5, 0.5))
            assert pr == 0
            assert dec == 0
            assert prob == 1

    def test_uniform_sampler(self):
        with patch("numpy.random.RandomState") as rsclass:
            rs = MagicMock()
            rsclass.return_value = rs
            rs.random_sample = MagicMock(return_value=0.5)

            s = circuit.uniform_sampler(seed=42)
            next(s)

            rsclass.assert_called_once_with(seed=42)

            for p0 in np.linspace(0, 1, 10):
                proj, dec, prob = s.send((p0, 1 - p0))
                assert proj == dec
                assert prob == 1
                assert proj == int(p0 < 0.5)

    def test_uniform_noisy_sampler(self):
        with patch("numpy.random.RandomState") as rsclass:
            rs = MagicMock()
            rsclass.return_value = rs
            rs.random_sample = MagicMock(return_value=0.5)

            s = circuit.uniform_noisy_sampler(0.4, seed=42)
            next(s)

            rsclass.assert_called_once_with(seed=42)

            # no readout error
            dec, proj, prob = s.send((0.2, 0.8))
            assert (proj, dec, prob) == (1, 1, 0.6)
            dec, proj, prob = s.send((0.9, 0.1))
            assert (proj, dec, prob) == (0, 0, 0.6)

            s = circuit.uniform_noisy_sampler(0.7, seed=42)
            next(s)
            dec, proj, prob = s.send((0.2, 0.8))
            assert (proj, dec, prob) == (1, 0, 0.7)
            dec, proj, prob = s.send((0.9, 0.1))
            assert (proj, dec, prob) == (0, 1, 0.7)

    def test_BiasedSampler(self):
        with patch("numpy.random.RandomState") as rsclass:
            rs = MagicMock()
            rsclass.return_value = rs
            rs.random_sample = MagicMock(return_value=0.5)

            with pytest.warns(UserWarning):
                s = circuit.BiasedSampler(alpha=1, readout_error=0.4)
            next(s)

            rsclass.assert_called_once_with(seed=None)

            # no readout error
            dec, proj, prob = s.send((0.2, 0.8))
            assert (proj, dec, prob) == (1, 1, 0.6)
            dec, proj, prob = s.send((0.9, 0.1))
            assert (proj, dec, prob) == (0, 0, 0.6)

            with pytest.warns(UserWarning):
                s = circuit.BiasedSampler(alpha=1, readout_error=0.7)
            next(s)
            dec, proj, prob = s.send((0.2, 0.8))
            assert (proj, dec, prob) == (1, 0, 0.7)
            dec, proj, prob = s.send((0.9, 0.1))
            assert (proj, dec, prob) == (0, 1, 0.7)
        assert s.p_twiddle < 1 and s.p_twiddle > 0

import quantumsim.circuit as circuit
import quantumsim.sparsedm as sparsedm
import quantumsim.qasm as qasm
import numpy as np

import os
import pytest


threequbit_qasm = """
qubits 5

.threequbit
  h q1
  h q3
  cz q1,q2
  cz q3,q4
  cz q1,q0
  cz q3,q2
  h q1
  h q3
"""


def test_three_qbit_clean():
    c = circuit.Circuit()

    qubit_names = ["D1", "A1", "D2", "A2", "D3"]

    # clean ancillas have infinite life-time
    for qb in qubit_names:
        # set lifetime to only almost inf so that waiting gates are added but
        # ineffective
        c.add_qubit(qb, np.inf, 1e10)

    c.add_hadamard("A1", time=0)
    c.add_hadamard("A2", time=0)

    c.add_cphase("A1", "D1", time=200)
    c.add_cphase("A2", "D2", time=200)

    c.add_cphase("A1", "D2", time=100)
    c.add_cphase("A2", "D3", time=100)

    c.add_hadamard("A1", time=300)
    c.add_hadamard("A2", time=300)

    with pytest.warns(UserWarning):
        m1 = circuit.Measurement("A1", time=350, sampler=None)
    c.add_gate(m1)
    with pytest.warns(UserWarning):
        m2 = circuit.Measurement("A2", time=350, sampler=None)
    c.add_gate(m2)

    c.add_waiting_gates(tmin=0, tmax=1500)

    c.order()

    assert len(c.gates) == 27

    sdm = sparsedm.SparseDM(qubit_names)

    for bit in sdm.classical:
        sdm.classical[bit] = 1

    sdm.classical["D3"] = 0

    assert sdm.classical == {'A1': 1, 'A2': 1, 'D3': 0, 'D1': 1, 'D2': 1}

    for i in range(100):
        c.apply_to(sdm)

    assert len(m1.measurements) == 100
    assert len(m2.measurements) == 100

    assert sdm.classical == {}

    # in a clean run, we expect just one possible path
    assert np.allclose(sdm.trace(), 1)

    assert m1.measurements == [1] * 100
    assert m2.measurements == [0, 1] * 50


def test_three_qbit_clean_qasm():
    config_qasm = os.path.join(os.path.dirname(__file__),
                                'config_qasm_5q.json')
    config_sim = os.path.join(os.path.dirname(__file__),
                                'config_simulator.json')
    parser = qasm.ConfigurableParser(config_qasm, config_sim)
    with pytest.warns(UserWarning):
        circuits = parser.parse(threequbit_qasm.split('\n'))
    assert len(circuits) == 1
    c = circuits[0]

    qubit_names = ["q0", "q1", "q2", "q3", "q4"]

    with pytest.warns(UserWarning):
        m1 = circuit.Measurement("q1", time=400, sampler=None)
    c.add_gate(m1)
    with pytest.warns(UserWarning):
        m2 = circuit.Measurement("q3", time=400, sampler=None)
    c.add_gate(m2)

    c.add_waiting_gates(tmin=0, tmax=1500)

    c.order()

    assert len(c.gates) == 29

    sdm = sparsedm.SparseDM(qubit_names)

    for bit in sdm.classical:
        sdm.classical[bit] = 1

    sdm.classical["q4"] = 0

    assert sdm.classical == {'q1': 1, 'q3': 1, 'q4': 0, 'q0': 1, 'q2': 1}

    for i in range(100):
        c.apply_to(sdm)

    assert len(m1.measurements) == 100
    assert len(m2.measurements) == 100

    assert sdm.classical == {}

    # in a clean run, we expect just one possible path
    assert np.allclose(sdm.trace(), 1)

    assert m1.measurements == [1] * 100
    assert m2.measurements == [0, 1] * 50

def test_noisy_measurement_sampler():
    c = circuit.Circuit()
    c.add_qubit("A", 0, 0)

    c.add_hadamard("A", 1)

    sampler = circuit.uniform_noisy_sampler(seed=42, readout_error=0.1)
    m1 = c.add_measurement("A", time=2, sampler=sampler)

    sdm = sparsedm.SparseDM("A")

    true_state = []
    for _ in range(20):
        c.apply_to(sdm)
        true_state.append(sdm.classical['A'])

    # these samples assume a certain seed (=42)
    assert m1.measurements == [0, 1, 0, 0, 1, 0,
                               1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1]
    assert true_state != m1.measurements
    assert true_state == [0, 1, 0, 0, 1, 0, 1,
                          0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1]

    # we have two measurement errors
    mprob = 0.9**18 * 0.1**2
    assert np.allclose(sdm.classical_probability, mprob)
    # and each measurement has outcome 1/2
    totprob = mprob * 0.5**20
    assert np.allclose(sdm.trace(), totprob)


def test_measurement_with_output_bit():
    c = circuit.Circuit()
    c.add_qubit("A")

    c.add_qubit("O")
    c.add_qubit("O2")

    c.add_rotate_y("A", time=0, angle=np.pi / 2)

    sampler = circuit.selection_sampler(1)
    c.add_measurement("A", time=1, sampler=sampler, output_bit="O")

    c.add_rotate_y("A", time=3.5, angle=np.pi / 2)

    sampler = circuit.selection_sampler(1)
    c.add_measurement("A", time=4, sampler=sampler, output_bit="O2")

    c.add_rotate_y("A", time=5, angle=np.pi / 2)
    c.order()

    sdm = sparsedm.SparseDM(c.get_qubit_names())

    assert sdm.classical['O'] == 0
    assert sdm.classical['O2'] == 0

    c.apply_to(sdm)

    assert np.allclose(sdm.trace(), 0.25)

    assert sdm.classical == {'O': 1, 'O2': 1}


@pytest.mark.skip()
def test_integration_surface17():
    def make_circuit(
            t1=np.inf,
            t2=np.inf,
            seed=42,
            readout_error=0.015,
            t_gate=40,
            t_rest=1000):
        surf17 = circuit.Circuit("Surface 17")

        t_rest += t_gate  # nominal rest time is between two gates

        x_bits = ["X%d" % i for i in range(4)]
        z_bits = ["Z%d" % i for i in range(4)]

        d_bits = ["D%d" % i for i in range(9)]

        for b in x_bits + z_bits + d_bits:
            surf17.add_qubit(b, t1, t2)

        def add_x(c, x_anc, d_bits, t=0, t_gate=t_gate):
            t += t_gate
            for d in d_bits:
                if d is not None:
                    c.add_cphase(d, x_anc, time=t)
                t += t_gate

        add_x(surf17, "X0", [None, None, "D2", "D1"], t=0)
        add_x(surf17, "X1", ["D1", "D0", "D4", "D3"], t=0)
        add_x(surf17, "X2", ["D5", "D4", "D8", "D7"], t=0)
        add_x(surf17, "X3", ["D7", "D6", None, None], t=0)

        t2 = 4 * t_gate + t_rest

        add_x(surf17, "Z0", ["D0", "D3", None, None], t=t2)
        add_x(surf17, "Z1", ["D2", "D5", "D1", "D4"], t=t2)
        add_x(surf17, "Z2", ["D4", "D7", "D3", "D6"], t=t2)
        add_x(surf17, "Z3", [None, None, "D5", "D8"], t=t2)

        sampler = circuit.BiasedSampler(
            readout_error=readout_error, alpha=1, seed=seed)

        for b in x_bits + d_bits:
            surf17.add_hadamard(b, time=0)
            surf17.add_hadamard(b, time=5 * t_gate)

        for b in z_bits:
            surf17.add_hadamard(b, time=4 * t_gate + t_rest)
            surf17.add_hadamard(b, time=4 * t_gate + t_rest + 5 * t_gate)

        for b in z_bits:
            surf17.add_measurement(
                b, time=10 * t_gate + t_rest, sampler=sampler)

        for b in x_bits:
            surf17.add_measurement(b, time=6 * t_gate, sampler=sampler)

        surf17.add_waiting_gates(
            only_qubits=x_bits, tmax=6 * t_gate, tmin=-t_rest - 5 * t_gate)
        surf17.add_waiting_gates(only_qubits=z_bits + d_bits, tmin=0)

        surf17.order()

        return surf17

    def syndrome_to_byte(syndrome):
        byte = 0

        for i in range(4):
            byte += syndrome["X%d" % i] << (i + 4)
        for i in range(4):
            byte += syndrome["Z%d" % i] << i

        return byte

    seed = 890793515

    t1 = 25000.0
    t2 = 35000.0
    ro_error = 0.015
    t_gate = 40.0
    t_rest = 1000.0

    rounds = 20

    c = make_circuit(t1=t1, t2=t2, seed=seed,
                     readout_error=ro_error, t_gate=t_gate, t_rest=t_rest)

    sdm = sparsedm.SparseDM(c.get_qubit_names())
    for b in ["D%d" % i for i in range(9)]:
        sdm.ensure_dense(b)

    syndromes = []
    for _ in range(rounds):
        c.apply_to(sdm)

        sdm.renormalize()

        syndromes.append(syndrome_to_byte(sdm.classical))

    syndrome = bytes(syndromes)

    assert syndrome == b'jHhJhL\x08L\tK)K\x08K\x08K\x08K\x08I'


def test_free_decay():

    for t1, t2 in [(np.inf, np.inf), (1000, 2000),
                   (np.inf, 1000), (1000, 1000)]:
        c = circuit.Circuit("Free decay")
        c.add_qubit("Q", t1=t1, t2=t2)
        c.add_rotate_y("Q", time=0, angle=np.pi)
        c.add_rotate_y("Q", time=1000, angle=-np.pi)
        c.add_waiting_gates()
        c.order()

        sdm = sparsedm.SparseDM(c.get_qubit_names())
        c.apply_to(sdm)
        sdm.project_measurement("Q", 0)

        assert np.allclose(sdm.trace(), np.exp(-1000 / t1))


def test_ramsey():

    for t1, t2 in [(np.inf, np.inf), (1000, 2000),
                   (np.inf, 1000), (1000, 1000)]:
        c = circuit.Circuit("Ramsey")
        c.add_qubit("Q", t1=t1, t2=t2)
        c.add_rotate_y("Q", time=0, angle=np.pi / 2)
        c.add_rotate_y("Q", time=1000, angle=-np.pi / 2)
        c.add_waiting_gates()
        c.order()

        sdm = sparsedm.SparseDM(c.get_qubit_names())
        c.apply_to(sdm)
        sdm.project_measurement("Q", 0)

        assert np.allclose(sdm.trace(), 0.5 * (1 + np.exp(-1000 / t2)))


def test_two_qubit_tpcp():
    c = circuit.Circuit("test")
    c.add_qubit("A", t1=30000, t2=30000)
    c.add_qubit("B", t1=30000, t2=30000)

    c.add_gate("rotate_y", "A", angle=1.2, time=0)
    c.add_gate("rotate_y", "B", angle=0.2, time=0)
    c.add_gate("rotate_z", "A", angle=0.1, time=1)
    c.add_gate("rotate_x", "B", angle=0.3, time=1)
    c.add_gate("cphase", "A", "B", time=2)

    sdm = sparsedm.SparseDM(c.get_qubit_names())
    for i in range(100):
        c.apply_to(sdm)
        x = sdm.full_dm.get_diag()
        assert np.allclose(x.sum(), 1)  # trace preserved
        assert np.all(x > 0)  # probabilities greater than zero

    assert np.allclose(
        np.linalg.eigvalsh(
            sdm.full_dm.to_array()), [
            0, 0, 0, 1])


def test_cphase_rotation():

    c = circuit.Circuit("test")
    c.add_qubit("A")
    c.add_qubit("B")

    c.add_gate("rotate_y", "A", angle=1.2, time=0)
    c.add_gate("rotate_y", "B", angle=1.2, time=0)

    for t in [1, 2, 3, 4, 5]:
        g = circuit.CPhaseRotation("A", "B", 2 * np.pi / 5, t)
        c.add_gate(g)

    c.add_gate("rotate_y", "A", angle=-1.2, time=6)
    c.add_gate("rotate_y", "B", angle=-1.2, time=6)

    c.order()

    sdm = sparsedm.SparseDM(c.get_qubit_names())

    c.apply_to(sdm)

    d = sdm.full_dm.get_diag()

    assert np.allclose(d, [1, 0, 0, 0])


def test_euler_rotation():
    c = circuit.Circuit("test")
    c.add_qubit("A")

    theta = 0.3
    lamda = 0.7
    phi = 4.2

    g = circuit.RotateEuler(bit="A", time=0, theta=theta, lamda=lamda, phi=phi)
    gconj = circuit.RotateEuler(
        bit="A",
        time=10,
        theta=-theta,
        lamda=-phi,
        phi=-lamda)

    c.add_gate(g)
    c.add_gate(gconj)

    c.order()

    sdm = sparsedm.SparseDM(c.get_qubit_names())

    c.apply_to(sdm)

    d = sdm.full_dm.get_diag()

    assert np.allclose(d, [1, 0])



def test_classical_not():
    sdm = sparsedm.SparseDM("A")
    c = circuit.Circuit()
    c.add_qubit(circuit.ClassicalBit("A"))
    c.add_gate(circuit.ClassicalNOT("A", time=0))
    c.order()


    assert sdm.classical['A'] == 0

    c.apply_to(sdm)

    assert sdm.classical['A'] == 1


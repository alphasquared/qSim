"""
DiCarlo_setup: functions to return the parameters for noise and experimental
design of DiCarlo qubits, in a format compatable with a circuit builder.
"""

# Parameters to insert
# RB numbers - 98 - 99.9 - mostly decoherence limited
# T2_star = 2 - 100 us
# T1 = infinite
# Need to write conversion of Rz into Rx and Ry gates.
# Need to write a PSB measurement function - include valley state?
# PSB not yet used so no numbers.
# Reset is for pairs of spins.
# Swap gate allowed 5ns - no gate fidelities yet but hope above 98%.
# Sqrt(swap) is similar.
# Cannot get C-Phase *and* Sqrt(swap).
# do repetition code with XX instead of ZZ
# Potentially possible to 'shunt' qubits.
# Pure Z gate - global rotating frame.

# TODO: Tom - write code for Sqrt(swap), finishing packaging.
# Stephan - get 2 qubit PTM for Sqrt(swap) + C-Phase
# Both - design some comparison experiments.
# Both - write circuits for repetition code.

import numpy as np
from numpy import pi
from quantumsim.circuit import uniform_noisy_sampler, uniform_sampler
from .setup_functions import make_1q2q_gateset
from .gate_templates import CZ, CPhase, RotateX, RotateY, RotateZ, Measure,\
                   ISwap, ISwapRotation, ResetGate, Had, CNOT
from .update_functions import update_quasistatic_flux


def quick_setup(qubit_list,
                **kwargs):
    '''
    Quick setup: a function to return a setup that may be immediately
    used to make a qsoverlay builder.
    '''

    setup = {
        'gate_dic': get_gate_dic(**kwargs),
        'update_rules': get_update_rules(**kwargs),
        'qubit_dic': {
            q: get_qubit(**kwargs) for q in qubit_list
        }
    }

    setup['gate_set'] = make_1q2q_gateset(qubit_dic=setup['qubit_dic'],
                                          gate_dic=setup['gate_dic'])
    return setup


def get_gate_dic():
    '''
    Returns the set of gates allowed on DiCarlo qubits.
    Measurement time is something that's still being optimized,
    so this might change.
    (msmt_time = the total time taken for measurement + depletion)
    '''

    # Initialise gate set with all allowed gates
    gate_dic = {
        'CZ': CZ,
        'C-Phase': CPhase,
        'CPhase': CPhase,
        'RotateX': RotateX,
        'RX': RotateX,
        'Rx': RotateX,
        'RotateY': RotateY,
        'RY': RotateY,
        'Ry': RotateY,
        'RotateZ': RotateZ,
        'RZ': RotateZ,
        'Rz': RotateZ,
        'Measure': Measure,
        'ISwap': ISwap,
        'ISwapRotation': ISwapRotation,
        'ResetGate': ResetGate,
        'Reset': ResetGate,
        'Had': Had,
        'H': Had,
        'CNOT': CNOT
    }

    return gate_dic


def get_qubit(noise_flag=True,
              t1=np.inf,
              t2=100000,
              dephasing_axis=1e-5,
              dephasing_angle=1e-5,
              dephasing=1e-5,
              p_exc_init=0,
              p_dec_init=0,
              p_exc_fin=0,
              p_dec_fin=0,
              dephase_var=1e-2/(2*pi),
              msmt_time=3000,
              interval_time=1000,
              oneq_gate_time=100,
              CZ_gate_time=40,
              reset_time=100,
              sampler=None,
              seed=None,
              readout_error=0.02,
              static_flux_std=None,
              **kwargs):
    '''
    The dictionary for parameters of the DiCarlo qubits, with standard
    parameters pre-set.

    This is a bit messy right now, but has the advantage of telling
    the user which parameters they can set. Not sure how to improve
    over this.
    '''
    if sampler is None:
        if noise_flag is True:
            sampler = uniform_noisy_sampler(seed=seed,
                                            readout_error=readout_error)
        else:
            sampler = uniform_sampler(seed=seed)

    if static_flux_std is not None:
        quasistatic_flux = static_flux_std * np.random.randn()
    else:
        quasistatic_flux = None

    if noise_flag is True:

        param_dic = {
            't1': t1,
            't2': t2,
            'dephasing_axis': dephasing_axis,
            'dephasing': dephasing,
            'dephasing_angle': dephasing_angle,
            'dephase_var': dephase_var,
            'p_exc_init': p_exc_init,
            'p_dec_init': p_dec_init,
            'p_exc_fin': p_exc_fin,
            'p_dec_fin': p_dec_fin,
            'msmt_time': msmt_time,
            'interval_time': interval_time,
            'oneq_gate_time': oneq_gate_time,
            'CZ_gate_time': CZ_gate_time,
            'ISwap_gate_time': CZ_gate_time*np.sqrt(2),
            'reset_time': reset_time,
            'photons': photons,
            'alpha0': alpha0,
            'kappa': kappa,
            'chi': chi,
            'quasistatic_flux': quasistatic_flux,
            'high_frequency': high_frequency,
            'sampler': sampler
        }
    else:

        param_dic = {
            't1': np.inf,
            't2': np.inf,
            'dephasing_axis': 0,
            'dephasing': 0,
            'dephasing_angle': 0,
            'dephase_var': 0,
            'p_exc_init': 0,
            'p_dec_init': 0,
            'p_exc_fin': 0,
            'p_dec_fin': 0,
            'msmt_time': msmt_time,
            'interval_time': interval_time,
            'CZ_gate_time': CZ_gate_time,
            'ISwap_gate_time': CZ_gate_time*np.sqrt(2),
            'reset_time': reset_time,
            'photons': False,
            'quasistatic_flux': None,
            'high_frequency': False,
            'sampler': sampler
        }

    for key, val in kwargs.items():
        param_dic[key] = val

    return param_dic


def get_update_rules(**kwargs):
    update_rules = [update_quasistatic_flux]
    return update_rules

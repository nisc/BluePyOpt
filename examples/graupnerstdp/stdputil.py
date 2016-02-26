# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 17:33:41 2013.

Utility functions for calcium-based STDP using simplified calcium model as in
(Graupner and Brunel, 2012).

@author: Giuseppe Chindemi
@remark: Copyright © BBP/EPFL 2005-2016; All rights reserved.
         Do not distribute without further notice.
"""
import logging
import numpy as np
from scipy.special import erf

logging.basicConfig(level=logging.WARN)


# Parameters for cortical slices (Sjostrom et al., 2001)
param_cortical = {
    'tau_ca': 22.6936e-3,  # [s]
    'C_pre': 0.5617539,
    'C_post': 1.23964,
    'theta_d': 1.0,
    'theta_p': 1.3,
    'gamma_d': 331.909,
    'gamma_p': 725.085,
    'sigma': 3.3501,
    'tau': 346.3615,  # [s]
    'rho_star': 0.5,
    'D': 4.6098e-3,  # [s]
    'beta': 0.5,
    'b': 5.40988}


# Parameters for hippocampal slices (Wittenberg and Wang, 2006)
param_hippocampal = {
    'tau_ca': 48.8373e-3,  # [s]
    'C_pre': 1.0,
    'C_post': 0.275865,
    'theta_d': 1.0,
    'theta_p': 1.3,
    'gamma_d': 313.0965,
    'gamma_p': 1645.59,
    'sigma': 9.1844,
    'tau': 688.355,  # [s]
    'rho_star': 0.5,
    'D': 18.8008e-3,  # [s]
    'beta': 0.7,
    'b': 5.28145}


class Protocol:
    def __init__(self, stim_vec, delta_vec, f, n, prot_id=None):
        """A generic stimulation protocol.

        :param stim_vec: list of stimuli ['pre'|'post'|'burst']
        :param delta_vec: list of deltas
        :param f: frequency in Hz
        :param n: number of repetitions
        :param prot_id: ID of the protocol
        """
        # Check stim strings
        valid_stim = set(['pre', 'post'])
        for s in stim_vec:
            assert s in valid_stim, '\'{0}\' is not a recognised stimulus'.format(s)

        self.stim_vec = np.array(stim_vec, dtype='a10')
        self.delta_vec = np.array(delta_vec)
        self.f = f
        self.n = n
        self.prot_id = prot_id

        # Compute time of stimuli
        self.stim_t = np.zeros(len(self.stim_vec))
        for i in xrange(len(self.delta_vec)):
            self.stim_t[i + 1] = self.stim_t[i] + self.delta_vec[i]

    def sort(self):
        """
        Sort stimuli.
        """
        logging.debug('Protocol.sort()')

        # Check if the stimuli are already sorted
        if np.all(self.delta_vec >= 0.0):
            logging.info('Protocol is already sorted.')
        else:
            logging.debug('Before sorting:')
            logging.debug('stim_vec = [%s]' % ', '.join(map(str, self.stim_vec)))
            logging.debug('delta_vec = [%s]' % ', '.join(map(str, self.delta_vec)))

            # Sort stimuli
            index_vec = np.argsort(self.stim_t)
            self.stim_vec = self.stim_vec[index_vec]
            self.delta_vec = np.diff(self.stim_t[index_vec])
            self.stim_t = self.stim_t[index_vec]

            logging.debug('After sorting:')
            logging.debug('stim_vec = [%s]' % ', '.join(map(str, self.stim_vec)))
            logging.debug('delta_vec = [%s]' % ', '.join(map(str, self.delta_vec)))


class CalciumTrace(object):
    def __init__(self, protocol, model):
        """Calcium trace produced by **model** when stimulated with **protocol**.
        :param protocol: stdputil.Protocol
            The stimulation protocol.
        :param model: dict
            Parameters of the Graupner model
        """
        self.protocol = protocol
        self.model = model

        # Generate the events corresponding to the configuration
        n_stim = len(protocol.stim_vec)
        curr_time = 0.0

        event = []
        time = []
        amplitude = []
        for i in xrange(n_stim):
            if protocol.stim_vec[i] == 'pre':
                event.append('Cpre')
                time.append(curr_time + model['D'])
                amplitude.append(model['C_pre'])
            elif protocol.stim_vec[i] == 'post':
                event.append('Cpost')
                time.append(curr_time)
                amplitude.append(model['C_post'])

            if i < n_stim - 1:
                # Delta vector is shorter than Stimulus vector
                curr_time += protocol.delta_vec[i]

        # Convert into numpy arrays for convenience
        event = np.array(event, dtype='a10')
        time = np.array(time)
        amplitude = np.array(amplitude)

        # Sort calcium events
        index_vec = np.argsort(time)

        logging.debug('Sorted indices = [%s]' % ', '.join(map(str, index_vec)))
        logging.debug('Calcium event = [%s]' % ', '.join(map(str, event[index_vec])))
        logging.debug('Calcium time = [%s]' % ', '.join(map(str, time[index_vec])))
        logging.debug('Calcium amplitude = [%s]' % ', '.join(map(str, amplitude[index_vec])))

        self.__evnt = event[index_vec]
        self.__t = time[index_vec]
        self.__amp = amplitude[index_vec]

    def materializetrace(self):
        # Create exemplary traces for plotting
        period = 1.0 / self.protocol.f
        tstart = -0.01
        tstop = tstart + period
        dt = 0.0001
        n = int((tstop - tstart) / dt)
        tvec = np.linspace(tstart, tstop, n)

        trace = np.zeros(n)
        for j in xrange(len(self.__evnt)):
            offset = int((self.time[j] - tstart) / dt)
            component = self.amplitude[j] * np.exp(-(tvec[:n-offset] / self.model['tau_ca']))
            trace[offset:] += component

        return tvec, trace

    @property
    def event(self):
        return self.__evnt

    @property
    def time(self):
        return self.__t

    @property
    def amplitude(self):
        return self.__amp


def load_neviansakmann():
    protocols = [Protocol(['post', 'post', 'post', 'pre'], [20e-3, 20e-3, 50e-3], 0.1, 60.0, prot_id='-90ms'),
                 Protocol(['post', 'post', 'post', 'pre'], [20e-3, 20e-3, 10e-3], 0.1, 60.0, prot_id='-50ms'),
                 Protocol(['post', 'post', 'pre', 'post'], [20e-3, 10e-3, 10e-3], 0.1, 60.0, prot_id='-30ms'),
                 Protocol(['post', 'pre', 'post', 'post'], [10e-3, 10e-3, 20e-3], 0.1, 60.0, prot_id='-10ms'),
                 Protocol(['pre', 'post', 'post', 'post'], [10e-3, 20e-3, 20e-3], 0.1, 60.0, prot_id='+10ms'),
                 Protocol(['pre', 'post', 'post', 'post'], [50e-3, 20e-3, 20e-3], 0.1, 60.0, prot_id='+50ms')]

    sg = [1.0, 0.68, 0.98, 1.42, 2.01, 0.92]

    stdev = None

    stderr = [0.09, 0.05, 0.12, 0.19, 0.22, 0.11]

    return protocols, sg, stdev, stderr


def time_above_threshold(ca_event_t, ca_event_amp, protocol, param):
    """

    :param ca_event_t:
    :param ca_event_amp:
    :param protocol:
    :param param:
    """
    # Sort the protocol if not already sorted
    protocol.sort()

    # Compute calcium rise time/delta
    ca_event_delta = np.diff(np.append(ca_event_t, 1.0 / protocol.f))

    # Compute calcium baseline
    A_f = (1.0 / (1.0 - np.exp(-1.0 / (protocol.f * param['tau_ca']))))
    if A_f != 1.0:
        baseline = (A_f - 1.0) * (ca_event_amp[0])
        for i in xrange(len(ca_event_amp) - 1):
            baseline += (A_f - 1.0) * (
                ca_event_amp[i + 1] * np.exp(np.sum(np.abs(ca_event_delta[:i + 1])) / param['tau_ca']))
    else:
        baseline = 0.0

    # Calcium amplitudes
    logging.debug('Calcium amplitudes')
    n_events = len(ca_event_amp)
    C_amp = np.zeros(2 * n_events)
    for i in xrange(n_events - 1):
        C_amp[i] = baseline * np.exp(-np.sum(np.abs(ca_event_delta[:i + 1])) / param['tau_ca'])
        logging.debug('C_amp[%d] = 0.0', i)
        for j in xrange(i + 1):
            C_amp[i] += ca_event_amp[j] * np.exp(-np.sum(np.abs(ca_event_delta[j:i + 1])) / param['tau_ca'])
            logging.debug('C_amp[%d] += %s * exp(-sum(abs(deltas[%d:%d])))',
                          i, protocol.stim_vec[j], j, i + 1)
        logging.debug('C_amp[%d] = %f', i, C_amp[i])
    C_amp[n_events - 1] = baseline
    logging.debug('C_amp[%d] = 0.0', n_events - 1)
    C_amp[n_events] = baseline + ca_event_amp[0]  # For convenience
    logging.debug('C_amp[%d] = %f', n_events, ca_event_amp[0])
    for i in xrange(n_events + 1, 2 * n_events):
        C_amp[i] = C_amp[i - n_events - 1] + ca_event_amp[i - n_events]
        logging.debug('C_amp[%d] = C_amp[%d] + %s',
                      i, i - n_events - 1, ca_event_amp[i - n_events])

    # Time spent above depression threshold
    t_d = np.zeros(n_events)
    for i in xrange(n_events):
        if C_amp[i] > param['theta_d']:
            t_d[i] = ca_event_delta[i]
        elif C_amp[i] <= param['theta_d'] < C_amp[i + n_events]:
            t_d[i] = param['tau_ca'] * np.log(C_amp[i + n_events] / param['theta_d'])
        else:
            t_d[i] = 0.0
    t_d_tot = np.sum(t_d)
    logging.debug('Time above depression threshold = %f', t_d_tot)

    # Time spent above potentiation threshold
    t_p = np.zeros(n_events)
    for i in xrange(n_events):
        if C_amp[i] > param['theta_p']:
            t_p[i] = ca_event_delta[i]
        elif C_amp[i] <= param['theta_p'] < C_amp[i + n_events]:
            t_p[i] = param['tau_ca'] * np.log(C_amp[i + n_events] / param['theta_p'])
        else:
            t_p[i] = 0.0
    t_p_tot = np.sum(t_p)
    logging.debug('Time above potentiation threshold = %f', t_p_tot)

    return t_d_tot, t_p_tot


def transition_prob(protocol, param=param_cortical):
    """
    """
    # Sort the protocol if not already sorted
    protocol.sort()

    # Generate all the possible realizations of the protocol, due to synaptic
    # transmission failures
    calcium_trace = CalciumTrace(protocol, param)

    t_d_tot, t_p_tot = time_above_threshold(calcium_trace.time, calcium_trace.amplitude, protocol, param)

    # TODO Ask Michael
    if t_d_tot == 0.0 and t_p_tot == 0.0:
        up = 0.0
        down = 0.0
        return up, down

    # Define aliases for convenience
    f = protocol.f
    n = protocol.n

    # Compute alpha depression and alpha potentiation
    alpha_d = t_d_tot * f
    alpha_p = t_p_tot * f

    # Compute Gamma depression and potentiation
    big_gamma_d = alpha_d * param['gamma_d']
    big_gamma_p = alpha_p * param['gamma_p']

    # Compute rho bar
    rho_bar = big_gamma_p / (big_gamma_p + big_gamma_d)
    sigma_rho_sq = param['sigma'] ** 2 * (alpha_p + alpha_d) / (big_gamma_p + big_gamma_d)
    tau_eff = param['tau'] / (big_gamma_p + big_gamma_d)

    # Up transition
    rho_0 = 0.0
    erf_arg = -((param['rho_star'] - rho_bar + (rho_bar - rho_0) * np.exp(-n / (tau_eff * f))) /
                (np.sqrt(sigma_rho_sq * (1.0 - np.exp(-2.0 * n / (tau_eff * f))))))
    up = 0.5 * (1.0 + erf(erf_arg))

    # Down transition
    rho_0 = 1.0
    erf_arg = -((param['rho_star'] - rho_bar + (rho_bar - rho_0) * np.exp(-n / (tau_eff * f))) /
                (np.sqrt(sigma_rho_sq * (1.0 - np.exp(-2.0 * n / (tau_eff * f))))))
    down = 0.5 * (1.0 - erf(erf_arg))

    return up, down


def protocol_outcome(protocol, param=param_cortical):
    """Compute the average synaptic gain for a given stimulation protocol.

    :param protocol:
    :param param:
    """
    # Compute Up and Down transition probabilities
    up, down = transition_prob(protocol, param)

    # Compute synaptic gain
    sg = ((1.0 - up) * param['beta'] + down * (1.0 - param['beta']) +
          param['b'] * (up * param['beta'] + (1.0 - down) * (1.0 - param['beta']))) / \
         (param['beta'] + (1.0 - param['beta']) * param['b'])

    return sg
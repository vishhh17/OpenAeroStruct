from __future__ import division, print_function
import numpy as np

from openmdao.api import ExplicitComponent

try:
    from openaerostruct.fortran import OAS_API
    fortran_flag = True
    data_type = float
except:
    fortran_flag = False
    data_type = complex


class BreguetRange(ExplicitComponent):
    """
    Computes the fuel burn using the Breguet range equation using
    the computed CL, CD, weight, and provided specific fuel consumption, speed of sound,
    Mach number, initial weight, and range.

    Note that we add information from each lifting surface.

    Parameters
    ----------
    CL : float
        Total coefficient of lift (CL) for the lifting surface.
    CD : float
        Total coefficient of drag (CD) for the lifting surface.
    weight : float
        Total weight of the structural spar.

    Returns
    -------
    fuelburn : float
        Computed fuel burn in kg based on the Breguet range equation.

    """

    def initialize(self):
        self.metadata.declare('surfaces', type_=list, required=True)

    def setup(self):
        for surface in self.metadata['surfaces']:
            name = surface['name']
            self.add_input(name + 'structural_weight', val=1.)

        self.add_input('CT', val=1.)
        self.add_input('CL', val=1.)
        self.add_input('CD', val=1.)
        self.add_input('a', val=1.)
        self.add_input('R', val=1.)
        self.add_input('M', val=1.)
        self.add_input('W0', val=1.)
        self.add_input('load_factor', val=1.)

        self.add_output('fuelburn', val=1.)

    def compute(self, inputs, outputs):

        g = 9.80665 * inputs['load_factor']
        CT = inputs['CT']
        a = inputs['a']
        R = inputs['R']
        M = inputs['M']
        W0 = inputs['W0'] * g

        # Loop through the surfaces and add up the structural weights
        # to get the total structural weight.
        Ws = 0.
        for surface in self.metadata['surfaces']:
            name = surface['name']
            Ws += inputs[name + 'structural_weight']

        CL = inputs['CL']
        CD = inputs['CD']

        fuelburn = (W0 + Ws) * (np.exp(R * CT / a / M * CD / CL) - 1)

        # Convert fuelburn from N to kg
        outputs['fuelburn'] = fuelburn / g

    def compute_partials(self, inputs, outputs, partials):

        g = 9.80665 * inputs['load_factor']
        CT = inputs['CT']
        a = inputs['a']
        R = inputs['R']
        M = inputs['M']
        W0 = inputs['W0'] * g

        Ws = 0.
        for surface in self.metadata['surfaces']:
            name = surface['name']
            Ws += inputs[name + 'structural_weight']

        CL = inputs['CL']
        CD = inputs['CD']

        dfb_dCL = -(W0 + Ws) * np.exp(R * CT / a / M * CD / CL) \
            * R * CT / a / M * CD / CL ** 2
        dfb_dCD = (W0 + Ws) * np.exp(R * CT / a / M * CD / CL) \
            * R * CT / a / M / CL
        dfb_dWs = np.exp(R * CT / a / M * CD / CL) - 1

        partials['fuelburn', 'CL'] = dfb_dCL / g
        partials['fuelburn', 'CD'] = dfb_dCD / g

        for surface in self.metadata['surfaces']:
            name = surface['name']
            inp_name = name + 'structural_weight'
            partials['fuelburn', inp_name] = dfb_dWs / g

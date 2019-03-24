"""
Business-Taxation Investor class.
"""
import copy
import numpy as np
import pandas as pd
import taxcalc as itax
from biztax.data import Data


class Investor():
    """
    Constructor for the Investor class.

    This class provides information on effective marginal tax rates on
    investment income and distributes changes in corporate after-tax income
    and pass-through business net income.

    Parameters:
        itax_policy: individual-tax Policy object
        data: investor data for itax.Records class
    """

    def __init__(self, itax_policy, data='puf.csv'):
        # Check argument types
        if not isinstance(itax_policy, itax.Policy):
            raise ValueError('itax_policy must be an itax.Policy object')
        if not isinstance(data, (str, pd.DataFrame)):
            raise ValueError('data must be a string or a Pandas DataFrame')
        # Save policy and records needed to create itax.Calculator object
        self.itax_policy = itax_policy
        self.records_data = data
        # Specify MTRs needed for calculating tax rates on business equity
        self.needed_mtr_list = ['e00900p', 'e26270', 'e02000', 'e01700',
                                'e00650', 'p22250', 'p23250']
        # Declare results calculated by Investor class
        self.mtrlist_nc = None
        self.mtrlist_e = None
        self.revenue_predistribution = None
        self.revenue_postdistribution = None

    def initiate_itax_calculator(self):
        """
        Creates and calculates an itax.Calculator object for 2014
        """
        calc = itax.Calculator(policy=self.itax_policy,
                               records=itax.Records(data=self.records_data),
                               verbose=False)
        calc.advance_to_year(2014)
        calc.calc_all()
        return calc

    @staticmethod
    def calc_tauNC(mtrdict, incdict):
        """
        Calculate effective marginal tax rate on noncorporate business income.
        """
        # Shares of noncorporate equity in fully taxable and tax-deferred form.
        alpha_nc_ft = 0.763
        alpha_nc_td = 0.101
        mtr1 = mtrdict['e00900p']
        mtr2 = mtrdict['e26270']
        mtr3 = mtrdict['e02000']
        mtr4 = mtrdict['e01700']
        posti = (incdict['taxinc'] > 0.)
        inc1 = np.abs(incdict['SchC'])
        inc2 = np.abs(incdict['SchEactive'])
        inc3 = np.abs(incdict['SchEpassive'])
        inc4 = incdict['definc']
        wgt = incdict['wgt']
        mtr_ft = (sum((mtr1 * inc1 + mtr2 * inc2 + mtr3 * inc3) * posti * wgt) /
                  sum((inc1 + inc2 + inc3) * posti * wgt))
        mtr_td = sum(mtr4 * inc4 * posti * wgt) / sum(inc4 * posti * wgt)
        mtr_nc = alpha_nc_ft * mtr_ft + alpha_nc_td * mtr_td
        return mtr_nc

    @staticmethod
    def calc_tauE(mtrdict, incdict, year):
        """
        Calculate the effective marginal tax rate on equity income in year.
        """
        # Retained earnings rate
        m = 0.44
        # Nominal expected return to equity
        E = Data().econ_defaults['r_e_c'][year-2014] + Data().econ_defaults['pi'][year-2014]
        # shares of cg in short-term, long-term, and held until death
        omega_scg = 0.034
        omega_lcg = 0.496
        omega_xcg = 1 - omega_scg - omega_lcg
        # shares of corp equity in taxable, deferred and nontaxable form
        alpha_ft = 0.572
        alpha_td = 0.039
        alpha_nt = 0.389
        # holding period for equity
        h_scg = 0.5
        h_lcg = 8.0
        h_td = 8.0
        # Get MTRs
        mtr_d = mtrdict['e00650']
        mtr_scg = mtrdict['p22250']
        mtr_lcg = mtrdict['p23250']
        mtr_td = mtrdict['e01700']
        # Get income measures
        inc_d = incdict['div']
        inc_scg = np.where(incdict['stcg'] >= 0, incdict['stcg'], 0)
        inc_lcg = np.where(incdict['ltcg'] >= 0, incdict['ltcg'], 0)
        inc_td = incdict['definc']
        posti = (incdict['taxinc'] > 0.)
        wgt = incdict['wgt']
        # MTR on dividend income
        tau_d = sum(mtr_d * inc_d * posti * wgt) / sum(inc_d * posti * wgt)
        # accrual effective mtr on stcg
        tau_scg1 = (sum(mtr_scg * inc_scg * posti * wgt) /
                    sum(inc_scg * posti * wgt))
        tau_scg = 1 - (np.log(np.exp(m * E * h_scg) * (1 - tau_scg1) + tau_scg1) /
                       (m * E * h_scg))
        # accrual effective mtr on ltcg
        tau_lcg1 = (sum(mtr_lcg * inc_lcg * posti * wgt) /
                    sum(inc_lcg * posti * wgt))
        tau_lcg = 1 - (np.log(np.exp(m * E * h_lcg) * (1 - tau_lcg1) + tau_lcg1) /
                       (m * E * h_lcg))
        # mtr on capital gains held until death
        tau_xcg = 0.0
        tau_cg = omega_scg * tau_scg + omega_lcg * tau_lcg + omega_xcg * tau_xcg
        tau_ft = (1 - m) * tau_d + m * tau_cg
        tau_td1 = sum(mtr_td * inc_td * posti * wgt) / sum(inc_td * posti * wgt)
        tau_td = 1 - (np.log(np.exp(E * h_td) * (1 - tau_td1) + tau_td1) /
                      (E * h_td))
        tau_e = alpha_ft * tau_ft + alpha_td * tau_td + alpha_nt * 0.0
        return tau_e

    def gen_mtr_lists(self):
        """
        Calculate the EMTR on income from corporate equity
        and non-corporate business.
        """
        mtrlist_nc = np.zeros(14)
        mtrlist_e = np.zeros(14)
        icalc = self.initiate_itax_calculator()
        for year in range(2014, 2028):
            icalc.advance_to_year(year)
            icalc.calc_all()
            # Get individual MTRs on each income type
            mtr1 = dict()
            for var in self.needed_mtr_list:
                _, _, mtr1[var] = icalc.mtr(var, calc_all_already_called=True)
            # Get relevant income measures
            inc1 = dict()
            inc1['SchC'] = icalc.array('e00900')
            inc1['SchEactive'] = icalc.array('e26270')
            inc1['SchEpassive'] = icalc.array('e02000') - icalc.array('e26270')
            inc1['definc'] = icalc.array('e01700')
            inc1['div'] = icalc.array('e00650')
            inc1['stcg'] = icalc.array('p22250')
            inc1['ltcg'] = icalc.array('p23250')
            inc1['wgt'] = icalc.array('s006')
            inc1['taxinc'] = icalc.array('c04800')
            # Calculate and save overall MTRs
            mtrlist_nc[year-2014] = self.calc_tauNC(mtr1, inc1)
            mtrlist_e[year-2014] = self.calc_tauE(mtr1, inc1, year)
        self.mtrlist_nc = mtrlist_nc
        self.mtrlist_e = mtrlist_e

    def get_tauNClist(self):
        """
        Returns mtrlist_nc as an array
        """
        return np.array(self.mtrlist_nc)

    def get_tauElist(self):
        """
        Returns mtrlist_e as an array
        """
        return np.array(self.mtrlist_e)

    def distribute_results(self, multipliers):
        """
        Pass effects of business tax reform to taxcalc.
        Adjusts individual income based on growth factors.
        Adjusts noncorporate business credits based on rescaling factors from
        legal shifting response.
        """
        icalc = self.initiate_itax_calculator()
        indiv_revenue = np.zeros(14)
        for i in range(2014, 2028):
            icalc2 = copy.deepcopy(icalc)
            # Change Sch C business income
            ref2_e00900p = icalc2.array('e00900p')
            ref2_e00900s = icalc2.array('e00900s')
            ref2_e00900 = icalc2.array('e00900')
            ref3_e00900p = np.where(ref2_e00900p >= 0,
                                    ref2_e00900p * multipliers['SchC_pos'][i-2014],
                                    ref2_e00900p * multipliers['SchC_neg'][i-2014])
            ref3_e00900s = np.where(ref2_e00900s >= 0,
                                    ref2_e00900s * multipliers['SchC_pos'][i-2014],
                                    ref2_e00900s * multipliers['SchC_neg'][i-2014])
            ref3_e00900 = np.where(ref2_e00900 >= 0,
                                   ref2_e00900 * multipliers['SchC_pos'][i-2014],
                                   ref2_e00900 * multipliers['SchC_neg'][i-2014])
            icalc2.array('e00900p', ref3_e00900p)
            icalc2.array('e00900s', ref3_e00900s)
            icalc2.array('e00900', ref3_e00900)
            # Change Sch E business income
            ref2_e26270 = icalc2.array('e26270')
            change_e26270 = np.where(ref2_e26270 >= 0,
                                     ref2_e26270 * (multipliers['e26270_pos'][i-2014] - 1),
                                     ref2_e26270 * (multipliers['e26270_neg'][i-2014] - 1))
            ref3_e26270 = ref2_e26270 + change_e26270
            ref3_e02000 = icalc2.array('e02000') + change_e26270
            icalc2.array('e26270', ref3_e26270)
            icalc2.array('e02000', ref3_e02000)
            # Change investment income
            icalc2.array('e00600', icalc2.array('e00600') * multipliers['equity'][i-2014])
            icalc2.array('e00650', icalc2.array('e00650') * multipliers['equity'][i-2014])
            icalc2.array('p22250', icalc2.array('p22250') * multipliers['equity'][i-2014])
            icalc2.array('p23250', icalc2.array('p23250') * multipliers['equity'][i-2014])
            # Change noncorporate business credits
            icalc2.array('e07300', icalc2.array('e07300') * multipliers['rescale_noncorp'][i-2014])
            icalc2.array('e07400', icalc2.array('e07400') * multipliers['rescale_noncorp'][i-2014])
            icalc2.array('e07600', icalc2.array('e07600') * multipliers['rescale_noncorp'][i-2014])
            icalc2.calc_all()
            # Calculate total individual income and payroll tax revenue
            indiv_revenue[i-2014] = sum(icalc2.array('combined') * icalc2.array('s006')) / 10**9
            # Advance icalc to the next year and recalculate
            if i < 2027:
                icalc.increment_year()
                icalc.calc_all()
        self.revenue_postdistribution = indiv_revenue

    def undistributed_revenue(self):
        """
        Calculates individual income tax revenue for each year without
        distributing any tax changes.
        """
        icalc = self.initiate_itax_calculator()
        indiv_revenue = np.zeros(14)
        for i in range(2014, 2028):
            indiv_revenue[i-2014] = sum(icalc.array('combined') * icalc.array('s006')) / 10**9
            if i < 2027:
                icalc.increment_year()
                icalc.calc_all()
        self.revenue_predistribution = indiv_revenue

    def get_revenue_withdistribution(self):
        """
        Returns total individual income tax revenue after corporate tax
        distribution and noncorporate business income distribution.
        """
        return np.array(self.revenue_postdistribution)

    def get_revenue_nodistribution(self):
        """
        Returns total individual income tax revenue with no business income
        distribution.
        """
        return np.array(self.revenue_predistribution)

import copy
import numpy as np
import pandas as pd
from biztax.years import START_YEAR, END_YEAR, NUM_YEARS
from biztax.data import Data
from biztax.domesticmne import DomesticMNE
from biztax.asset import Asset
from biztax.debt import Debt


class CorpTaxReturn():
    """
    Constructor for the CorpTaxReturn object.
    This class includes objects relevant to the calculation of
    corporate income tax liability:
        assets: an associated Asset object
        debts: an associated debt object
        combined_return: a DataFrame with tax calculations for each year

    Parameters:
        btax_params: dict of business tax policy parameters
        assets: Asset object for the corporation
        debts: Debt object for the corporation
        earnings: list or array of earnings for each year in the budget window
    """

    def __init__(self, btax_params, revenues, deductions,
                 credit, dmne=None,
                 data=None, assets=None, debts=None):
        # Create an associated Data object
        if isinstance(data, Data):
            self.data = data
        else:
            self.data = Data()
        if isinstance(btax_params, pd.DataFrame):
            self.btax_params = btax_params
        else:
            raise ValueError('btax_params must be DataFrame')
        if isinstance(revenues, pd.DataFrame):
            self.revenues = copy.deepcopy(revenues)
        else:
            raise ValueError('revenues must be in DataFrame')
        if isinstance(deductions, pd.DataFrame):
            self.deductions = copy.deepcopy(deductions)
        else:
            raise ValueError('deductions must be in DataFrame')
        if isinstance(credit, pd.DataFrame):
            self.credits = copy.deepcopy(credit)
        else:
            raise ValueError('credits must be in DataFrame')
        if dmne is None:
            # Note: Don't do this in general
            self.dmne = DomesticMNE(self.btax_params)
            self.dmne.calc_all()
        elif isinstance(dmne, DomesticMNE):
            self.dmne = dmne
        else:
            raise ValueError('dmne must be a DomesticMNE object')
        if assets is not None:
            if isinstance(assets, Asset):
                self.assets = assets
            else:
                raise ValueError('assets must be Asset object')
        else:
            self.assets = Asset(btax_params)
            self.assets.calc_all()
        if debts is not None:
            if isinstance(debts, Debt):
                self.debts = debts
            else:
                raise ValueError('debts must be Debt object')
        else:
            assets_forecast = self.assets.get_forecast()
            self.debts = Debt(btax_params, assets_forecast)
            self.debts.calc_all()
        # Prepare unmodeled components of tax return
        self.revenues['capgains'] = (self.revenues['capgains'] *
                                     (1. - self.btax_params['capgains_corp_hc']))
        self.revenues['domestic_divs'] = (self.revenues['domestic_divs'] *
                                          self.btax_params['domestic_dividend_inclusion'])
        self.revenues['total'] = (self.revenues['receipts']
                                  + self.revenues['rent']
                                  + self.revenues['royalties']
                                  + self.revenues['capgains']
                                  + self.revenues['domestic_divs']
                                  + self.revenues['other']
                                  + self.dmne.dmne_results['foreign_taxinc'])
        self.deductions['charity'] = (self.deductions['charity'] *
                                      (1. - self.btax_params['charity_hc']))
        self.deductions['statelocaltax'] = (self.deductions['statelocaltax'] *
                                            (1. - self.btax_params['statelocaltax_hc']))
        self.deductions['total'] = (self.deductions['cogs']
                                    + self.deductions['execcomp']
                                    + self.deductions['wages']
                                    + self.deductions['repairs']
                                    + self.deductions['baddebt']
                                    + self.deductions['rent']
                                    + self.deductions['statelocaltax']
                                    + self.deductions['charity']
                                    + self.deductions['amortization']
                                    + self.deductions['depletion']
                                    + self.deductions['advertising']
                                    + self.deductions['pensions']
                                    + self.deductions['benefits']
                                    + self.deductions['other'])
        combined = pd.DataFrame({'year': range(START_YEAR, END_YEAR + 1),
                                 'ebitda': (self.revenues['total'] -
                                            self.deductions['total'])})
        # Add tax depreciation
        combined['taxDep'] = self.assets.get_taxdep()
        self.combined_return = combined

    def update_assets(self, assets):
        """
        Updates the Asset object associated with the tax return.
        """
        if isinstance(assets, Asset):
            self.assets = assets
        else:
            raise ValueError('assets must be Asset object')

    def update_debts(self, debts):
        """
        Updates the Debt object associated with the tax return.
        """
        if isinstance(debts, Debt):
            self.debts = debts
        else:
            raise ValueError('debts must be Debt object')

    def update_earnings(self, dearnings):
        """
        Updates the earnings DataFrame associated with the tax return.
        """
        assert len(dearnings) == NUM_YEARS
        fearnings = np.asarray(self.dmne.dmne_results['foreign_taxinc'])
        self.combined_return['ebitda'] = dearnings + fearnings

    def calcInterestDeduction(self):
        """
        Computes interest deduction.
        """
        # Compute adjusted taxable income
        adjTaxInc = np.maximum(self.combined_return['ebitda'] -
                               self.revenues['capgains'] -
                               self.combined_return['taxDep'] +
                               self.btax_params['adjustedTaxInc_def'] *
                               (self.combined_return['taxDep'] +
                                self.deductions['amortization'] +
                                self.deductions['depletion']), 0.0001)
        # Section 163(j) deduction limitation
        deductible_int = (adjTaxInc *
                          self.btax_params['adjustedTaxInc_limit'] +
                          self.debts.get_intInc())
        intded0 = self.debts.get_intDed()
        intded1 = np.zeros(NUM_YEARS)
        for i in range(NUM_YEARS):
            if i > 0:
                # Add disallowed interest as carryforward from prior year
                intded0[i] = intded0[i] + intded0[i-1] - intded1[i-1]
            intded1[i] = min(deductible_int[i], intded0[i])
        # Apply interest haircuts
        intTaxInc = (self.debts.get_intInc() *
                     (1. - self.btax_params['intIncome_corp_hc']) +
                     self.debts.get_muniInc() *
                     (1. - self.btax_params['muniIntIncome_corp_hc']))
        intTaxDed = intded1 * (1. - self.btax_params['intPaid_corp_hc'])
        # Compute net interest deduction
        self.combined_return['nid'] = intTaxDed - intTaxInc
        # Assign fraction of interest deductible to Debt object
        fracded = intTaxDed / (self.debts.get_intPaid() + 0.000001)
        self.btax_params['fracded_c'] = fracded

    def calcInitialTax(self):
        """
        Calculates taxable income and tax before credits.
        """
        netinc1 = (self.combined_return['ebitda'] -
                   self.combined_return['taxDep'] -
                   self.combined_return['nid'])
        self.combined_return['sec199'] = (netinc1 * self.deductions['sec199share']
                                          * self.btax_params['sec199_rt'])
        netinc2 = netinc1 - self.combined_return['sec199']
        self.combined_return['taxinc'] = np.maximum(netinc2, 0.)
        self.combined_return['tau'] = self.btax_params['tau_c']
        self.combined_return['taxbc'] = (self.combined_return['taxinc'] *
                                         self.combined_return['tau'])

    def calcFTC(self):
        """
        Gets foreign tax credit from DomesticMNE
        """
        self.combined_return['ftc'] = self.dmne.dmne_results['ftc']

    def calcAMT(self):
        """
        Calculates the AMT revenue and PYMTC for [START_YEAR, END_YEAR]
        """
        # Overall transition rates and parameters
        trans_amt0 = self.data.trans_amt0
        trans_amt1 = self.data.trans_amt1
        userate =self.data.userate_pymtc
        amt2013 = self.data.corp_tax2013.loc[40, 'ALL']
        # Get relevant tax information
        taxinc = np.array(self.combined_return['taxinc'])
        amt_rates = np.array(self.btax_params['tau_amt'])
        ctax_rates = np.array(self.btax_params['tau_c'])
        pymtc_hc = np.array(self.btax_params['pymtc_hc'])
        pymtc_refund = np.array(self.btax_params['pymtc_refund'])
        # Create empty arrays for AMT, PYMTC, and stocks (by status)
        A = np.zeros(NUM_YEARS)
        P = np.zeros(NUM_YEARS)
        stock0 = np.zeros(NUM_YEARS + 1)
        stock1 = np.zeros(NUM_YEARS + 1)
        # Set initial stocks using steady-state equations
        stock0[0] = amt2013 / userate
        stock1[0] = amt2013 * (trans_amt1 / (1. - trans_amt1) +
                               (1. - userate) / userate *
                               (1. - trans_amt0) / (1. - trans_amt1))
        for iyr in range(NUM_YEARS):
            # Calculate AMT
            if amt_rates[iyr] == 0.:
                # If no AMT
                A[iyr] = 0.
                frac_amt = 0.
                # Update transition rate parameters
                pi0 = 1.
                pi1 = 0.
            elif ctax_rates[iyr] <= amt_rates[iyr]:
                # If AMT rate exceeds regular rate (all subject to AMT)
                A[iyr] = ((amt_rates[iyr] - ctax_rates[iyr]
                           + amt_rates[iyr] / self.data.param_amt)
                          * taxinc[iyr])
                frac_amt = 0.999
                # Update transition rate parameters
                pi0 = 0.
                pi1 = 1.
            else:
                A[iyr] = (amt_rates[iyr] / self.data.param_amt *
                          np.exp(-self.data.param_amt
                                 * (ctax_rates[iyr] / amt_rates[iyr] - 1))
                          * taxinc[iyr])
                # Compute new fraction subject to AMT
                frac_amt = np.exp(-self.data.param_amt
                                  * (ctax_rates[iyr] / amt_rates[iyr] - 1))
                # Adjust transition params for change in AMT frequency
                pi1 = max(min(self.data.trans_amt1 * (frac_amt / self.data.amt_frac) ** 0.5, 1.), 0.)
                pi0 = max(min(1. - frac_amt * (1 - pi1) / (1 - frac_amt), 1.), 0.)
            # Compute PYMTC
            P[iyr] = ((pymtc_refund[iyr] * stock0[iyr]
                       + (1. - pymtc_refund[iyr]) * stock0[iyr] * userate)
                      * (1. - pymtc_hc[iyr]))
            # Update credits carried forward
            stock0[iyr+1] = ((stock1[iyr] + A[iyr]) * (1. - pi1)
                             + (stock0[iyr] - P[iyr]) * pi0)
            stock1[iyr+1] = ((stock1[iyr] + A[iyr]) * pi1
                             + (stock0[iyr] - P[iyr]) * (1. - pi0))
        # Rescale for any cross-sector shifting
        amt_final = A * self.data.rescale_corp
        pymtc_final = P * self.data.rescale_corp
        self.combined_return['amt'] = amt_final
        self.combined_return['pymtc'] = pymtc_final

    def calcTax(self):
        """
        Calculates final tax liability.
        """
        self.combined_return['gbc'] = self.credits['gbc']
        # Calculate final tax liability
        taxliab1 = (self.combined_return['taxbc'] +
                    self.combined_return['amt'] -
                    self.combined_return['ftc'] -
                    self.combined_return['pymtc'] -
                    self.combined_return['gbc'])
        self.combined_return['taxrev'] = np.maximum(taxliab1, 0.)

    def calc_all(self):
        """
        Executes all tax calculations.
        """
        self.calcInterestDeduction()
        self.calcInitialTax()
        self.calcFTC()
        self.calcAMT()
        self.calcTax()

    def getReturn(self):
        """
        Returns the tax return information
        """
        combined_result = copy.deepcopy(self.combined_return)
        return combined_result

    def get_tax(self):
        """
        Returns the total tax liability.
        """
        tax = np.array(self.combined_return['taxrev'])
        return tax

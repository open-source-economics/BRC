import copy
import numpy as np
import pandas as pd
import taxcalc as itax
from biztax.policy import Policy
from biztax.investor import Investor
from biztax.corporation import Corporation
from biztax.passthrough import PassThrough
from biztax.response import Response


class BusinessModel():
    """
    Constructor for the BusinessModel class.

    This is the top-level Business-Taxation class.

    In order to correctly estimate the effects of changing business and
    individual tax policy parameters, this class includes
    a baseline Policy object and a reform Policy object for both
    business and individual taxes.  
    The following objects are created (for both baseline and reform policy):
      Investor
      Corporation
      PassThrough
    Furthermore, the BusinessModel uses a Response object when the
    calc_all method is called with a Response object as an argument.

    It is important to note that the inclusion of both baseline and reform
    Policy objects in the constructor is important: the necessity of both
    comes into play when calculating the responses to a reform and when
    distributing the changes in corporate income and business income to
    individual tax units.

    Parameters:
        btax_policy_ref: Business-Taxation Policy object for btax reform
        itax_policy_ref: Tax-Calculator Policy object for itax reform
        btax_policy_base: Business-Taxation Policy object for btax baseline
        itax_policy_base: Tax-Calculator Policy object for itax baseline
        investor_data: filename or DataFrame containing individual sample
    """

    def __init__(self, btax_policy_ref, itax_policy_ref,
                 # baseline defaults are current-law policy
                 btax_policy_base=Policy(), itax_policy_base=itax.Policy(),
                 investor_data='puf.csv'):
        # Check policy argument types
        assert isinstance(btax_policy_ref, Policy)
        assert isinstance(itax_policy_ref, itax.Policy)
        assert isinstance(btax_policy_base, Policy)
        assert isinstance(itax_policy_base, itax.Policy)
        # Create Investor objects incorporating itax policy and investor data
        # self.investor_base = Investor(itax_policy_base, investor_data)
        # self.investor_ref = Investor(itax_policy_ref, investor_data)
        self.investor_base = Investor(itax_policy_base, investor_data)
        self.investor_ref = Investor(itax_policy_ref, investor_data)
        # Create btax policy parameters DataFrame objects
        self.btax_params_base = btax_policy_base.parameters_dataframe()
        self.btax_params_ref = btax_policy_ref.parameters_dataframe()
        # Create Corporations
        self.corp_base = Corporation(self.btax_params_base)
        self.corp_ref = Corporation(self.btax_params_ref)
        # Create PassThroughs
        self.passthru_base = PassThrough(self.btax_params_base)
        self.passthru_ref = PassThrough(self.btax_params_ref)
        # Declare calculated results objects
        self.multipliers = None
        self.ModelResults = None

    def check_btax_reform(self, paramdict):
        """
        Checks that the btax_param dictionary are acceptable
        """
        assert isinstance(paramdict, dict)
        paramnames = list(self.btax_defaults)
        paramnames.remove('year')
        for key in paramdict:
            key2 = int(key)
            assert key2 in range(2014, 2027)
            for param in paramdict[key]:
                assert param in paramnames

    def update_btax_params(self, param_dict):
        """
        Updates btax_params
        param_dict is a year: {param: value} dictionary.
        Acceptable years are 2017-2027. Ex:
            {'2018': {'tau_c': 0.3}}
        """
        self.check_btax_reform(param_dict)
        params_df = copy.deepcopy(self.btax_defaults)
        yearlist = []
        for key in param_dict:
            yearlist.append(key)
        yearlist.sort()
        years = np.asarray(params_df['year'])
        for year in yearlist:
            for param in param_dict[year]:
                paramlist1 = np.asarray(params_df[param])
                paramlist1[years >= int(year)] = param_dict[year][param]
                params_df[param] = paramlist1
        return params_df

    def calc_all(self, response=None):
        """
        Executes all BusinessModel calculations.

        Parameters:
          response: must be either None (for no-response calculations) or
                    a Response object (for with-response calculations).
        """
        # Run static calculations for baseline
        self.corp_base.calc_static()
        self.passthru_base.calc_static()
        if response is None:
            # Run calculations for reform with no response
            self.corp_ref.calc_static()
            self.passthru_ref.calc_static()
        else:
            # Run calculations for reform with response
            assert isinstance(response, Response)
            if response.calc_all_already_called():
                msg = ('cannot call response.calc_all before '
                       'using it as BusinessModel.calc_all argument')
                raise ValueError(msg)
            self.update_mtrlists()  # do this before doing response.calc_all
            response.calc_all(self.btax_params_base, self.btax_params_ref)
            self.corp_ref.apply_responses(response)
            self.passthru_ref.apply_responses(response)
        # Compare corporations and pass-throughs to get income changes
        self.produce_multipliers()
        # Distribute changes to reform investor
        self.investor_ref.distribute_results(self.multipliers)
        # Calculate baseline investor without distributing
        self.investor_base.undistributed_revenue()
        # Calculate and save total revenue changes
        self.calc_revenue_changes()

    def produce_multipliers(self):
        # Get corporate net after-tax incomes
        netinc_corp_base = self.corp_base.get_netinc()
        netinc_corp_ref = self.corp_ref.get_netinc()
        # Calculate multiplier for equity income
        equity_multiplier = netinc_corp_ref / netinc_corp_base
        # Save into DataFrame
        multipliers = pd.DataFrame({'year': range(2014, 2028),
                                    'equity': equity_multiplier})
        # Get net income results for the pass-throughs
        netinc_ptbase = copy.deepcopy(self.passthru_base.netinc_results)
        netinc_ptref = copy.deepcopy(self.passthru_ref.netinc_results)
        multipliers['SchC_pos'] = netinc_ptref['SchC_pos'] / netinc_ptbase['SchC_pos']
        multipliers['SchC_neg'] = netinc_ptref['SchC_neg'] / netinc_ptbase['SchC_neg']
        multipliers['e26270_pos'] = (netinc_ptref['partner_pos'] + netinc_ptref['Scorp_pos']) / (netinc_ptbase['partner_pos'] + netinc_ptbase['Scorp_pos'])
        multipliers['e26270_neg'] = (netinc_ptref['partner_neg'] + netinc_ptref['Scorp_neg']) / (netinc_ptbase['partner_neg'] + netinc_ptbase['Scorp_neg'])
        # Corporate interest share of all interest
        # Note: interest income not distributed to debtholders (yet)
        corpshare_totalint = 1.0
        multipliers['debt'] = (1 + (self.corp_ref.real_results['NIP'] / self.corp_base.real_results['NIP'] - 1) * corpshare_totalint)
        # Add recale results
        multipliers['rescale_corp'] = self.corp_ref.data.rescale_corp / self.corp_base.data.rescale_corp
        multipliers['rescale_noncorp'] = self.corp_ref.data.rescale_noncorp / self.corp_base.data.rescale_noncorp
        # Save multipliers
        self.multipliers = multipliers

    def calc_revenue_changes(self):
        """
        Calculates the change in corporate tax revenue, the change in
        individual income tax/payroll tax revenue, and the combination.
        Saves these changes in a DataFrame.
        """
        corprev_base = self.corp_base.get_taxrev()
        corprev_ref = self.corp_ref.get_taxrev()
        corprev_change = corprev_ref - corprev_base
        indivrev_base = self.investor_base.get_revenue_nodistribution()
        indivrev_ref = self.investor_ref.get_revenue_withdistribution()
        indivrev_change = indivrev_ref - indivrev_base
        alltax_change = corprev_change + indivrev_change
        self.ModelResults = pd.DataFrame({'year': range(2014, 2028),
                                          'CTax_change': corprev_change,
                                          'ITax_change': indivrev_change,
                                          'AllTax_change': alltax_change})

    def update_mtrlists(self):
        """
        Calls Investors to calculate MTRs on noncorporate business equity
        and on corporate equity, and updates these in the Investor objects.
        """
        # Generate MTRs for baseline investor
        self.investor_base.gen_mtr_lists()
        self.btax_params_base['tau_nc'] = self.investor_base.get_tauNClist()
        self.btax_params_base['tau_e'] = self.investor_base.get_tauElist()
        # Generate MTRs for reform investor
        self.investor_ref.gen_mtr_lists()
        self.btax_params_ref['tau_nc'] = self.investor_ref.get_tauNClist()
        self.btax_params_ref['tau_e'] = self.investor_ref.get_tauElist()

"""
Using the Business-Taxation model: An example

This file provides an example of how to use the B-T model and walks through
the process of creating a business model and getting the results.

Executing this example (by entering "python example.py" without the
quotes at the operating-system command prompt) should produce the same
results as stored in the example_results directory.  Note that to
execute this example a copy of the Tax-Calculator puf.csv micro-data
input file is required to be in the same directory as this file.

The example here includes 3 changes to policy beginning in 2018:
  - Apply 28% corporate tax rate
  - Eliminate bonus depreciation
  - Impose 50% haircut on the deductibility of interest on new debt
"""
import taxcalc as itax  # capabilities of individual Tax-Calculator
from biztax import Policy, BusinessModel, Response

# Create a business-tax Policy object with the following reform
btax_reform_dict = {
    2018: {
        '_tau_c': [0.28],
        '_depr_3yr_bonus': [0.0],
        '_depr_5yr_bonus': [0.0],
        '_depr_7yr_bonus': [0.0],
        '_depr_10yr_bonus': [0.0],
        '_depr_15yr_bonus': [0.0],
        '_depr_20yr_bonus': [0.0],
        '_depr_25yr_bonus': [0.0],
        '_depr_275yr_bonus': [0.0],
        '_depr_39yr_bonus': [0.0],
        '_pymtc_status': [1],
        '_newIntPaid_corp_hc': [1.0],
        '_newIntPaid_corp_hcyear': [2018],
        '_oldIntPaid_corp_hc': [1.0],
        '_oldIntPaid_corp_hcyear': [2018],
        '_newIntPaid_noncorp_hc': [1.0],
        '_newIntPaid_noncorp_hcyear': [2018],
        '_oldIntPaid_noncorp_hc': [1.0],
        '_oldIntPaid_noncorp_hcyear': [2018]
    }
}
btax_policy_reform = Policy()
btax_policy_reform.implement_reform(btax_reform_dict)

# Create an individual-tax itax.Policy object with no reform
itax_policy_noreform = itax.Policy()

# Execute BusinessModel calculations with no response
BM = BusinessModel(btax_policy_reform, itax_policy_noreform)
BM.calc_all(response=None)

# Look at the changes in total corporate and individual income tax liability
output_df = BM.ModelResults.round(3)
output_df.to_csv('example_results/nresp_model_results.csv', index=False)

# Take a closer look at corporate tax items under baseline and reform policy
output_df = BM.corp_base.taxreturn.combined_return.round(3)
output_df.to_csv('example_results/nresp_base.csv', index=False)
output_df = BM.corp_ref.taxreturn.combined_return.round(3)
output_df.to_csv('example_results/nresp_refm.csv', index=False)

# Look at differences in real effects on corporations without any responses
corp_diff = (BM.corp_ref.real_results - BM.corp_base.real_results).round(3)
corp_diff['year'] = BM.corp_base.real_results['year']
corp_diff.to_csv('example_results/nresp_corp_diff.csv', index=False)

# Delete the BusinessModel object
del BM

# Execute BusinessModel calculations assuming responses just
# investment and debt responses to business tax reform
BM = BusinessModel(btax_policy_reform, itax_policy_noreform)
partial_response = Response()
partial_response.update_elasticities({'inv_usercost_c': -1.0,
                                      'inv_usercost_nc': -0.5,
                                      'debt_taxshield_c': 0.4,
                                      'debt_taxshield_nc': 0.2,
                                      'first_year_response': 2018})
BM.calc_all(response=partial_response)

# Look at the changes in total corporate and individual income tax liability
output_df = BM.ModelResults.round(3)
output_df.to_csv('example_results/wresp_model_results.csv', index=False)

# Take a closer look at corporate tax items under baseline and reform policy
output_df = BM.corp_base.taxreturn.combined_return.round(3)
output_df.to_csv('example_results/wresp_base.csv', index=False)
output_df = BM.corp_ref.taxreturn.combined_return.round(3)
output_df.to_csv('example_results/wresp_refm.csv', index=False)

# Look at differences in real effects on corporations given the responses
corp_diff = (BM.corp_ref.real_results - BM.corp_base.real_results).round(3)
corp_diff['year'] = BM.corp_base.real_results['year']
corp_diff.to_csv('example_results/wresp_corp_diff.csv', index=False)

# Delete the BusinessModel object
del BM

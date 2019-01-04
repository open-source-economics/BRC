import numpy as np
import pandas as pd

track_progress = False

OVERWRITE = False

# Noncorporate tax results to check
vars_to_check = ['SchC_pos', 'SchC_neg', 'e26270_pos', 'e26270_neg']

# No II tax changes or behavioral responses
iit_params_ref = {}
elast_dict = {}

"""
Test C0: No reform
"""
btax_dict1 = {}
btax_dict2 = {}
exec(open('run_brc.py').read())
testpass0 = True
if OVERWRITE:
    indiv_gfactors.to_csv('test_results/test_noncorp0_out.csv', index=False)
else:
    expected_output = pd.read_csv('test_results/test_noncorp0_out.csv')
    for v in vars_to_check:
        expected = expected_output[v]
        result = indiv_gfactors[v]
        testpass0 *= np.allclose(expected, result, atol = 1e-08)

"""
Test C1: Multiple policy changes
    Depreciation rules
    Net interest deduction
"""
btax_dict1 = {2017: {
        'depr_3yr_method': 'GDS',
        'depr_3yr_bonus': 0.8,
        'depr_5yr_method': 'ADS',
        'depr_5yr_bonus': 0.8,
        'depr_7yr_method': 'Economic',
        'depr_7yr_bonus': 0.8,
        'depr_10yr_method': 'GDS',
        'depr_10yr_bonus': 0.6,
        'depr_15yr_method': 'Expensing',
        'depr_15yr_bonus': 0.6,
        'depr_20yr_method': 'ADS',
        'depr_20yr_bonus': 0.4,
        'depr_25yr_method': 'EconomicDS',
        'depr_25yr_bonus': 0.2,
        'depr_275yr_method': 'GDS',
        'depr_275yr_bonus': 0.2,
        'depr_39yr_method': 'ADS',
        'depr_39yr_bonus': 0.2}}
btax_dict2 = {'netIntPaid_corp_hc': {2018: 0.5}}
exec(open('run_brc.py').read())
testpass1 = True
if OVERWRITE:
    indiv_gfactors.to_csv('test_results/test_noncorp1_out.csv', index=False)
else:
    expected_output = pd.read_csv('test_results/test_noncorp1_out.csv')
    for v in vars_to_check:
        expected = expected_output[v]
        result = indiv_gfactors[v]
        testpass1 *= np.allclose(expected, result, atol = 1e-08)

"""
Test C2: Remainiing untested changes
    Interest paid haircuts
    Haircut on undepreciated basis
    Reclassify depreciation life
"""
btax_dict1 = {}
btax_dict2 = {'oldIntPaid_noncorp_hc': {2017: 0.5},
              'newIntPaid_noncorp_hc': {2017: 1.0},
              'undepBasis_noncorp_hc': {2018: 0.5},
              'reclassify_taxdep_gdslife': {2018: {39: 25}}}
exec(open('run_brc.py').read())
testpass2 = True
if OVERWRITE:
    indiv_gfactors.to_csv('test_results/test_noncorp2_out.csv', index=False)
else:
    expected_output = pd.read_csv('test_results/test_noncorp2_out.csv')
    for v in vars_to_check:
        expected = expected_output[v]
        result = indiv_gfactors[v]
        testpass2 *= np.allclose(expected, result, atol = 1e-08)

# Display test results
if testpass0:
    print('Test noncorptax 0: PASS')
else:
    print('Test noncorptax 0: FAIL')
if testpass1:
    print('Test noncorptax 1: PASS')
else:
    print('Test noncorptax 1: FAIL')
if testpass2:
    print('Test noncorptax 2: PASS')
else:
    print('Test noncorptax 2: FAIL')




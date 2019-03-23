"""
Test Business-Taxation JSON parameter files.
"""
# CODING-STYLE CHECKS:
# pycodestyle test_parameters.py

import os
import json
import pytest
from biztax import Policy


@pytest.mark.parametrize("fname",
                         [("policy_current_law.json")])
def test_json_file_contents(tests_path, fname):
    """
    Check contents of JSON parameter files.
    """
    # specify test information
    required_keys = ['long_name', 'description',
                     'section_1', 'section_2', 'notes',
                     'row_var', 'row_label',
                     'start_year', 'cpi_inflated', 'cpi_inflatable',
                     'col_var', 'col_label',
                     'value_type', 'value', 'valid_values']
    valid_value_types = ['boolean', 'integer', 'real', 'string']
    invalid_keys = ['invalid_minmsg', 'invalid_maxmsg', 'invalid_action']
    first_year = Policy.JSON_START_YEAR
    last_known_year = Policy.LAST_KNOWN_YEAR  # for indexed parameter values
    num_known_years = last_known_year - first_year + 1
    long_params = ['_II_brk1', '_II_brk2', '_II_brk3', '_II_brk4',
                   '_II_brk5', '_II_brk6', '_II_brk7',
                   '_PT_brk1', '_PT_brk2', '_PT_brk3', '_PT_brk4',
                   '_PT_brk5', '_PT_brk6', '_PT_brk7',
                   '_PT_excl_wagelim_thd',
                   '_ALD_BusinessLosses_c',
                   '_STD', '_II_em',
                   '_AMT_em', '_AMT_em_ps', '_AMT_em_pe',
                   '_ID_ps', '_ID_AllTaxes_c']
    long_known_years = 2026 - first_year + 1  # for TCJA-reverting long_params
    # read JSON parameter file into a dictionary
    path = os.path.join(tests_path, '..', fname)
    pfile = open(path, 'r')
    allparams = json.load(pfile)
    pfile.close()
    assert isinstance(allparams, dict)
    # check elements in each parameter sub-dictionary
    failures = ''
    for pname in allparams:
        # all parameter names should be strings
        assert isinstance(pname, str)
        # check that param contains required keys
        param = allparams[pname]
        assert isinstance(param, dict)
        for key in required_keys:
            assert key in param
        if param['value_type'] == 'string':
            for key in invalid_keys:
                assert key not in param
            assert isinstance(param['valid_values']['options'], list)
        else:
            for key in invalid_keys:
                assert key in param
            assert param['invalid_action'] in ['stop', 'warn']
        # check for non-empty long_name and description strings
        assert isinstance(param['long_name'], str)
        if not param['long_name']:
            assert '{} long_name'.format(pname) == 'empty string'
        assert isinstance(param['description'], str)
        if not param['description']:
            assert '{} description'.format(pname) == 'empty string'
        # check that row_var is FLPDYR
        assert param['row_var'] == 'FLPDYR'
        # check that start_year equals first_year
        syr = param['start_year']
        assert isinstance(syr, int) and syr == first_year
        # check that cpi_inflatable and cpi_inflated are boolean
        assert isinstance(param['cpi_inflatable'], bool)
        assert isinstance(param['cpi_inflated'], bool)
        # check that cpi_inflatable and cpi_inflated are False in many files
        if fname != 'policy_current_law.json':
            assert param['cpi_inflatable'] is False
            assert param['cpi_inflated'] is False
        # check that cpi_inflatable is True when cpi_inflated is True
        if param['cpi_inflated'] and not param['cpi_inflatable']:
            msg = 'param:<{}>; cpi_inflated={}; cpi_inflatable={}'
            fail = msg.format(pname, param['cpi_inflated'],
                              param['cpi_inflatable'])
            failures += fail + '\n'
        # check that value_type is correct string
        if not param['value_type'] in valid_value_types:
            msg = 'param:<{}>; value_type={}'
            fail = msg.format(pname, param['value_type'])
            failures += fail + '\n'
        # check that cpi_inflatable param has value_type real
        if param['cpi_inflatable'] and param['value_type'] != 'real':
            msg = 'param:<{}>; value_type={}; cpi_inflatable={}'
            fail = msg.format(pname, param['value_type'],
                              param['cpi_inflatable'])
            failures += fail + '\n'
        # ensure that cpi_inflatable is False when value_type is not real
        if param['cpi_inflatable'] and param['value_type'] != 'real':
            msg = 'param:<{}>; cpi_inflatable={}; value_type={}'
            fail = msg.format(pname, param['cpi_inflatable'],
                              param['value_type'])
            failures += fail + '\n'
        # check that row_label is list
        rowlabel = param['row_label']
        assert isinstance(rowlabel, list)
        # check all row_label values
        cyr = first_year
        for rlabel in rowlabel:
            assert int(rlabel) == cyr
            cyr += 1
        # check type and dimension of value
        value = param['value']
        assert isinstance(value, list)
        assert len(value) == len(rowlabel)
        # check that col_var and col_label are consistent
        cvar = param['col_var']
        assert isinstance(cvar, str)
        clab = param['col_label']
        if cvar == '':
            assert isinstance(clab, str) and clab == ''
        else:
            assert isinstance(clab, list)
            # check different possible col_var values
            if cvar == 'MARS':
                assert len(clab) == 5
            elif cvar == 'EIC':
                assert len(clab) == 4
            elif cvar == 'idedtype':
                assert len(clab) == 7
            elif cvar == 'c00100':
                pass
            else:
                assert cvar == 'UNKNOWN col_var VALUE'
            # check length of each value row
            for valuerow in value:
                assert len(valuerow) == len(clab)
        # check that indexed parameters have all known years in rowlabel list
        # form_parameters are those whose value is available only on IRS form
        form_parameters = []
        if param['cpi_inflated']:
            error = False
            known_years = num_known_years
            if pname in long_params:
                known_years = long_known_years
            if pname in form_parameters:
                if len(rowlabel) != (known_years - 1):
                    error = True
            else:
                if len(rowlabel) != known_years:
                    error = True
            if error:
                msg = 'param:<{}>; len(rowlabel)={}; known_years={}'
                fail = msg.format(pname, len(rowlabel), known_years)
                failures += fail + '\n'
    if failures:
        raise ValueError(failures)

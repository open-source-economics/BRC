"""
Business-Taxation Policy class.
"""
import os
import pandas
import taxcalc


class Policy(taxcalc.Policy):
    """
    Policy is a subclass of the Tax-Calculator Policy class, and
    therefore, inherits its methods (none of which are shown here).

    Constructor for the Policy class, which does not have any indexed
    policy parameters.

    Parameters:
        none
    """

    DEFAULTS_FILE_NAME = 'policy_current_law.json'
    DEFAULTS_FILE_PATH = os.path.abspath(os.path.dirname(__file__))
    JSON_START_YEAR = 2014  # remains the same unless earlier data added
    LAST_KNOWN_YEAR = 2018  # last year for which indexed param vals are known
    # should increase LAST_KNOWN_YEAR by one every calendar year
    LAST_BUDGET_YEAR = 2027  # last extrapolation year
    # should increase LAST_BUDGET_YEAR by one every calendar year
    DEFAULT_NUM_YEARS = LAST_BUDGET_YEAR - JSON_START_YEAR + 1
    
    def __init__(self):
        # read default parameters and initialize
        self._vals = self._params_dict_from_json_file()
        # initialize abstract base taxcalc.Parameters class
        self.initialize(Policy.JSON_START_YEAR, Policy.DEFAULT_NUM_YEARS)
        # initialize parent taxcalc.Policy class
        taxcalc.Policy.JSON_START_YEAR = Policy.JSON_START_YEAR
        taxcalc.Policy.LAST_KNOWN_YEAR = Policy.LAST_KNOWN_YEAR
        taxcalc.Policy.LAST_BUDGET_YEAR = Policy.LAST_BUDGET_YEAR
        taxcalc.Policy.DEFAULT_NUM_YEARS = Policy.DEFAULT_NUM_YEARS
        # specify no parameter indexing rates
        self._inflation_rates = None
        self._wage_growth_rates = None
        # specify warning/error handling variables
        self.parameter_warnings = ''
        self.parameter_errors = ''
        self._ignore_errors = False

    def parameters_dataframe(self):
        """
        Return pandas DataFrame containing all parameters in
        this Policy object (as columns) for each year (as rows)
        in the [Policy.JSON_START_YEAR, Policy.LAST_BUDGET_YEAR] range.

        But note that the returned DataFrame is indexed over the
        [0, Policy.DEFAULT_NUM_YEARS] range (not over calendar years
        even though the DataFrame contains a year column).

        Also, note that the leading underscore character in each
        parameter name is removed in the returned DataFrame.
        """
        pdict = dict()
        pdict['year'] = list(range(self.start_year, self.end_year + 1))
        for pname in self._vals:
            pdict[pname[1:]] = getattr(self, pname)
        return pandas.DataFrame(data=pdict)

def calculate_loan_amortization(principal, annual_interest_rate, loan_duration_years):
    """
    Calculates the loan amortization schedule.

    Args:
        principal (float): The initial loan amount.
        annual_interest_rate (float): The annual interest rate (e.g., 0.05 for 5%).
        loan_duration_years (int): The duration of the loan in years.

    Returns:
        list: A list of tuples, where each tuple contains
              (year, annual_payment, principal_paid, interest_paid, remaining_balance).
    """
    amortization_schedule = []
    remaining_balance = principal
    monthly_interest_rate = annual_interest_rate / 12
    number_of_payments = loan_duration_years * 12

    if monthly_interest_rate > 0:
        monthly_payment = principal * (monthly_interest_rate * (1 + monthly_interest_rate)**number_of_payments) / \
                          ((1 + monthly_interest_rate)**number_of_payments - 1)
    else: # Handle zero interest rate case
        monthly_payment = principal / number_of_payments if number_of_payments > 0 else 0

    annual_payment = monthly_payment * 12

    for year in range(1, loan_duration_years + 1):
        annual_interest_paid = 0
        annual_principal_paid = 0
        for month in range(1, 13):
            interest_for_month = remaining_balance * monthly_interest_rate
            principal_for_month = monthly_payment - interest_for_month
            remaining_balance -= principal_for_month
            annual_interest_paid += interest_for_month
            annual_principal_paid += principal_for_month

        # Ensure remaining balance doesn't go significantly below zero due to floating point issues
        if remaining_balance < 0 and abs(remaining_balance) < 0.01 : # allow small tolerance
            annual_principal_paid += remaining_balance # Adjust last principal payment
            remaining_balance = 0


        amortization_schedule.append(
            (year, annual_payment, annual_principal_paid, annual_interest_paid, remaining_balance if remaining_balance > 0 else 0)
        )
        if remaining_balance <= 0:
            break

    return amortization_schedule

def calculate_scpi_revenue(investment_amount, gross_yield):
    """
    Calculates the annual SCPI revenue.

    Args:
        investment_amount (float): The total amount invested in SCPI.
        gross_yield (float): The gross yield of the SCPI (e.g., 0.05 for 5%).

    Returns:
        float: The annual SCPI revenue.
    """
    return investment_amount * gross_yield

def calculate_sci_corporate_tax(profit_before_tax):
    """
    Calculates the SCI corporate tax (IS).
    Applies IS rates: 15% on profit up to €42,500, and 25% on the portion of profit exceeding €42,500.

    Args:
        profit_before_tax (float): The profit before tax.

    Returns:
        float: The calculated corporate tax amount.
    """
    tax_rate_lower = 0.15
    tax_rate_higher = 0.25
    threshold = 42500.0

    if profit_before_tax <= 0:
        return 0.0

    if profit_before_tax <= threshold:
        tax = profit_before_tax * tax_rate_lower
    else:
        tax_on_lower_bracket = threshold * tax_rate_lower
        tax_on_higher_bracket = (profit_before_tax - threshold) * tax_rate_higher
        tax = tax_on_lower_bracket + tax_on_higher_bracket
    return tax

def calculate_sci_financials(scpi_revenue, loan_interest_for_year, loan_principal_for_year, management_fees):
    """
    Calculates the SCI's key financial metrics for a year.

    Args:
        scpi_revenue (float): Annual revenue from SCPI.
        loan_interest_for_year (float): Annual interest paid for the loan.
        loan_principal_for_year (float): Annual principal repaid for the loan.
        management_fees (float): Annual management fees for the SCI.

    Returns:
        dict: A dictionary containing:
            'profit_before_tax': float,
            'corporate_tax': float,
            'net_result_after_tax': float,
            'cash_flow': float
    """
    profit_before_tax = scpi_revenue - loan_interest_for_year - management_fees
    corporate_tax = calculate_sci_corporate_tax(profit_before_tax)
    net_result_after_tax = profit_before_tax - corporate_tax
    annual_loan_payment = loan_interest_for_year + loan_principal_for_year
    cash_flow = scpi_revenue - annual_loan_payment - management_fees - corporate_tax

    return {
        'profit_before_tax': profit_before_tax,
        'corporate_tax': corporate_tax,
        'net_result_after_tax': net_result_after_tax,
        'cash_flow': cash_flow
    }

if __name__ == "__main__":
    # Test calculate_loan_amortization
    loan_schedule = calculate_loan_amortization(150000, 0.012, 15)
    print("Loan Amortization Schedule:")
    for entry in loan_schedule:
        print(f"Year: {entry[0]}, Annual Payment: {entry[1]:.2f}, Principal Paid: {entry[2]:.2f}, Interest Paid: {entry[3]:.2f}, Remaining Balance: {entry[4]:.2f}")
    print("-" * 20)

    # Test calculate_scpi_revenue
    scpi_revenue_test = calculate_scpi_revenue(150000, 0.05) # Expected: 7500
    print(f"SCPI Revenue: {scpi_revenue_test:.2f}")
    print("-" * 20)

    # Test calculate_sci_corporate_tax
    tax1 = calculate_sci_corporate_tax(10000) # Expected: 1500.00
    print(f"Corporate Tax for 10000 profit: {tax1:.2f}")
    tax2 = calculate_sci_corporate_tax(50000) # Expected: 42500*0.15 + (50000-42500)*0.25 = 6375 + 1875 = 8250.00
    print(f"Corporate Tax for 50000 profit: {tax2:.2f}")
    tax3 = calculate_sci_corporate_tax(0) # Expected: 0.00
    print(f"Corporate Tax for 0 profit: {tax3:.2f}")
    tax4 = calculate_sci_corporate_tax(-1000) # Expected: 0.00
    print(f"Corporate Tax for -1000 profit: {tax4:.2f}")
    print("-" * 20)

    # Test calculate_sci_financials
    # scpi_revenue=7500, loan_interest_for_year=1800, loan_principal_for_year=8000, management_fees=500
    # profit_before_tax = 7500 - 1800 - 500 = 5200
    # corporate_tax = 5200 * 0.15 = 780
    # net_result_after_tax = 5200 - 780 = 4420
    # annual_loan_payment = 1800 + 8000 = 9800
    # cash_flow = 7500 - 9800 - 500 - 780 = -3580
    financials_test = calculate_sci_financials(scpi_revenue=7500, loan_interest_for_year=1800, loan_principal_for_year=8000, management_fees=500)
    print("SCI Financials:")
    for key, value in financials_test.items():
        print(f"  {key.replace('_', ' ').capitalize()}: {value:.2f}")
    print("-" * 20)

def calculate_sci_capital_gain_tax_on_resale(resale_value, purchase_value, corporate_tax_rate_on_gain):
    """
    Calculates SCI capital gain tax on resale assuming a flat rate on the gain.
    """
    capital_gain = resale_value - purchase_value
    tax_on_gain = max(0, capital_gain) * corporate_tax_rate_on_gain
    return tax_on_gain, capital_gain

def calculate_direct_investment_capital_gain_tax(resale_value, purchase_value, holding_period_years):
    """
    Calculates capital gain tax for direct investment in real estate (SCPI parts)
    applying abatements based on holding period.
    """
    capital_gain_base = max(0, resale_value - purchase_value)

    if capital_gain_base == 0:
        return {'total_tax': 0, 'tax_on_income_portion': 0, 'social_contributions_portion': 0,
                'abatement_rate_income': 0, 'abatement_rate_social': 0, 'capital_gain_base': 0}

    # Income Tax Portion (base 19%)
    abatement_income = 0
    if holding_period_years > 5: # Abatement starts from the 6th year
        # Years 6-21: 6% per year
        abatement_income += min(max(0, holding_period_years - 5), 16) * 0.06
        # Year 22: additional 4% (total 100% for income tax)
        if holding_period_years >= 22:
            abatement_income += 0.04
    abatement_income = min(abatement_income, 1.0) # Cap at 100%

    taxable_gain_income = capital_gain_base * (1 - abatement_income)
    tax_on_income_portion = taxable_gain_income * 0.19

    # Social Contributions Portion (base 17.2%)
    abatement_social = 0
    if holding_period_years > 5: # Abatement starts from the 6th year
        # Years 6-21: 1.65% per year
        abatement_social += min(max(0, holding_period_years - 5), 16) * 0.0165
        # Year 22: 1.60% for the 22nd year
        if holding_period_years >= 22:
            abatement_social += 0.0160
        # Years 23-30: 9% per year
        if holding_period_years > 22:
            abatement_social += min(max(0, holding_period_years - 22), 8) * 0.09
    abatement_social = min(abatement_social, 1.0) # Cap at 100%

    taxable_gain_social = capital_gain_base * (1 - abatement_social)
    social_contributions_portion = taxable_gain_social * 0.172

    total_tax = tax_on_income_portion + social_contributions_portion

    return {
        'total_tax': total_tax,
        'tax_on_income_portion': tax_on_income_portion,
        'social_contributions_portion': social_contributions_portion,
        'abatement_rate_income': abatement_income,
        'abatement_rate_social': abatement_social,
        'capital_gain_base': capital_gain_base
    }

if __name__ == "__main__":
    # ... (previous tests remain the same) ...

    print("Testing SCI Capital Gain Tax on Resale:")
    # Test case 1: Gain
    sci_tax, sci_gain = calculate_sci_capital_gain_tax_on_resale(200000, 150000, 0.15)
    print(f"  Gain: {sci_gain:.2f}, Tax: {sci_tax:.2f} (Expected Gain: 50000, Tax: 7500)")
    # Test case 2: No Gain
    sci_tax_no_gain, sci_gain_no = calculate_sci_capital_gain_tax_on_resale(150000, 150000, 0.15)
    print(f"  Gain: {sci_gain_no:.2f}, Tax: {sci_tax_no_gain:.2f} (Expected Gain: 0, Tax: 0)")
    # Test case 3: Loss
    sci_tax_loss, sci_gain_loss = calculate_sci_capital_gain_tax_on_resale(140000, 150000, 0.15)
    print(f"  Gain: {sci_gain_loss:.2f}, Tax: {sci_tax_loss:.2f} (Expected Gain: -10000, Tax: 0)")
    print("-" * 20)

    print("Testing Direct Investment Capital Gain Tax:")
    # Test case 1: Short holding (e.g., 5 years) - No abatement
    direct_tax_5y = calculate_direct_investment_capital_gain_tax(200000, 150000, 5)
    # Expected: Gain 50000. Income tax part: 50000 * 0.19 = 9500. Social part: 50000 * 0.172 = 8600. Total = 18100. Abatements = 0.
    print(f"  5 Years Holding (Gain 50k): {direct_tax_5y}")

    # Test case 2: Medium holding (e.g., 10 years) - Some abatement
    # Holding 10 years: 5 years of abatement.
    # Income Abatement: 5 * 6% = 30%
    # Social Abatement: 5 * 1.65% = 8.25%
    # Expected Income Tax: 50000 * (1-0.30) * 0.19 = 35000 * 0.19 = 6650
    # Expected Social Tax: 50000 * (1-0.0825) * 0.172 = 50000 * 0.9175 * 0.172 = 45875 * 0.172 = 7890.5
    # Total Tax: 6650 + 7890.5 = 14540.5
    direct_tax_10y = calculate_direct_investment_capital_gain_tax(200000, 150000, 10)
    print(f"  10 Years Holding (Gain 50k): {direct_tax_10y}")

    # Test case 3: Long holding (e.g., 22 years) - Full income abatement, significant social abatement
    # Holding 22 years:
    # Income Abatement: (16 * 6%) + 4% = 96% + 4% = 100%
    # Social Abatement: (16 * 1.65%) + 1.60% = 26.4% + 1.6% = 28%
    # Expected Income Tax: 50000 * (1-1.0) * 0.19 = 0
    # Expected Social Tax: 50000 * (1-0.28) * 0.172 = 50000 * 0.72 * 0.172 = 36000 * 0.172 = 6192
    # Total Tax: 0 + 6192 = 6192
    direct_tax_22y = calculate_direct_investment_capital_gain_tax(200000, 150000, 22)
    print(f"  22 Years Holding (Gain 50k): {direct_tax_22y}")

    # Test case 4: Very long holding (e.g., 30 years) - Full abatement for both
    # Holding 30 years:
    # Income Abatement: 100%
    # Social Abatement: (16 * 1.65%) + 1.60% + (8 * 9%) = 26.4% + 1.6% + 72% = 100%
    # Expected Total Tax: 0
    direct_tax_30y = calculate_direct_investment_capital_gain_tax(200000, 150000, 30)
    print(f"  30 Years Holding (Gain 50k): {direct_tax_30y}")

    # Test case 5: No gain
    direct_tax_no_gain = calculate_direct_investment_capital_gain_tax(150000, 150000, 10)
    print(f"  No Gain (10 Years Holding): {direct_tax_no_gain}")
    print("-" * 20)

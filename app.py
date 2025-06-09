import streamlit as st
import simulation_core as core # Assuming simulation_core.py is in the same directory
import pandas as pd

st.title("SCPI Investment Simulator via SCI à l'IS")

PFU_RATE = 0.30
SOCIAL_CONTRIBUTIONS_RATE = 0.172

# Sidebar for inputs
st.sidebar.header("Simulation Parameters")
investment_amount = st.sidebar.number_input(
    "Total SCPI Investment (€)",
    min_value=10000, value=150000, step=1000,
    help="Total amount invested in SCPI shares."
)
loan_amount = st.sidebar.number_input(
    "Loan Amount (€)",
    min_value=0, value=150000, step=1000,
    help="Amount borrowed to finance the SCPI investment. Set to 0 for no loan."
)
actual_loan_duration_input = st.sidebar.number_input(
    "Loan Duration (years)",
    min_value=0, max_value=30, value=15, step=1,
    help="Duration of the loan in years. Set to 0 if no loan."
)
annual_interest_rate = st.sidebar.number_input(
    "Annual Interest Rate (%)",
    min_value=0.1, max_value=10.0, value=1.2, step=0.1, format="%.3f",
    help="Annual interest rate for the loan."
) / 100.0
scpi_gross_yield = st.sidebar.number_input(
    "SCPI Gross Yield (%)",
    min_value=1.0, max_value=10.0, value=5.0, step=0.1, format="%.3f",
    help="Expected annual gross yield from the SCPI before any fees or taxes."
) / 100.0
annual_management_fees = st.sidebar.number_input(
    "Annual Management Fees (€)",
    min_value=0, value=462, step=10,
    help="Annual management fees for the SCI structure (e.g., accounting fees)."
)
investor_tmi = st.sidebar.number_input(
    "Investor's Marginal Tax Rate (TMI %)",
    min_value=0.0, max_value=45.0, value=30.0, step=1.0, format="%.1f",
    help="Your marginal income tax rate (e.g., 30 for 30%). Used for direct investment comparison tax calculation (TMI + Social Contributions)."
) / 100.0

# Simulation run years - this defines the length of the main results table
default_sim_years = actual_loan_duration_input if actual_loan_duration_input > 0 else 15
simulation_run_years = st.sidebar.number_input(
    "Total Simulation Years",
    min_value=1, value=default_sim_years, max_value=50, step=1,
    help="Total duration for which the simulation will run and display annual results."
)

dividend_strategy = st.sidebar.selectbox(
    "Dividend Distribution Strategy (for SCI)",
    options=[
        "No Dividends During Loan Term",
        "Distribute All Available Surplus Annually",
        "Distribute All Net Result Annually (if surplus allows)"
    ],
    index=0,  # Default to "No Dividends During Loan Term"
    help="Strategy for distributing dividends from the SCI."
)

# Resale Simulation Inputs
st.sidebar.header("Resale Simulation")
simulate_resale = st.sidebar.checkbox("Simulate SCPI Resale", value=True, help="Enable to simulate the resale of SCPI shares at a specified year.")
resale_year_input_disabled = not simulate_resale
resale_year = st.sidebar.number_input(
    "Resale Year",
    min_value=1, value=simulation_run_years, max_value=simulation_run_years, step=1,
    disabled=resale_year_input_disabled,
    help="Year at which the SCPI shares are resold. Must be <= Total Simulation Years."
)
expected_annual_appreciation_rate = st.sidebar.number_input(
    "Expected Annual SCPI Value Appreciation (%)",
    min_value=-5.0, value=1.0, max_value=10.0, step=0.1, format="%.1f",
    disabled=resale_year_input_disabled,
    help="Annual rate at which the SCPI share value is expected to appreciate (or depreciate)."
) / 100.0

SCI_CAPITAL_GAIN_TAX_RATE_FLAT = 0.15 # Flat rate for SCI capital gain tax on resale, as per simplified assumption.

if st.sidebar.button("Run Simulation"):
    annual_scpi_revenue = core.calculate_scpi_revenue(investment_amount, scpi_gross_yield)

    # Calculate amortization schedule only for the actual loan duration
    amortization_schedule_for_loan_term = []
    if loan_amount > 0 and actual_loan_duration_input > 0:
        amortization_schedule_for_loan_term = core.calculate_loan_amortization(loan_amount, annual_interest_rate, actual_loan_duration_input)

    results = []
    cca_balance = 0  # Initialize CCA balance

    # Main simulation loop runs for simulation_run_years
    for year_idx in range(simulation_run_years):
        year = year_idx + 1

        loan_annual_payment = 0
        principal_paid = 0
        interest_paid = 0

        # Check if current year is within the loan term and if a loan exists
        if loan_amount > 0 and year <= actual_loan_duration_input:
            if year_idx < len(amortization_schedule_for_loan_term):
                # amortization_schedule_for_loan_term is a list of tuples: (year, annual_payment, principal_paid, interest_paid, remaining_balance)
                current_year_loan_tuple = amortization_schedule_for_loan_term[year_idx]
                loan_annual_payment = current_year_loan_tuple[1]
                principal_paid = current_year_loan_tuple[2]
                interest_paid = current_year_loan_tuple[3]

        financials = core.calculate_sci_financials(
            scpi_revenue=annual_scpi_revenue,
            loan_interest_for_year=interest_paid,
            loan_principal_for_year=principal_paid,
            management_fees=annual_management_fees
        )

        gross_sci_cash_flow = financials['cash_flow']
        cca_injection = 0
        cca_reimbursement = 0
        sci_surplus_cash_after_cca = 0

        if gross_sci_cash_flow < 0:
            cca_injection = -gross_sci_cash_flow
            cca_balance += cca_injection
            sci_surplus_cash_after_cca = 0 # Deficit covered by CCA
        else: # gross_sci_cash_flow >= 0
            if cca_balance > 0:
                cca_reimbursement = min(gross_sci_cash_flow, cca_balance)
                cca_balance -= cca_reimbursement
            sci_surplus_cash_after_cca = gross_sci_cash_flow - cca_reimbursement

        # Dividend Distribution Logic
        distributed_dividends_gross = 0
        net_result_for_dividends = financials['net_result_after_tax']

        # current_year_is_during_loan_term should refer to actual_loan_duration_input
        current_year_is_during_loan_term = (year <= actual_loan_duration_input if loan_amount > 0 else False)

        if dividend_strategy == "No Dividends During Loan Term":
            if not current_year_is_during_loan_term:
                 if sci_surplus_cash_after_cca > 0: # Check if there is surplus to distribute
                    distributed_dividends_gross = sci_surplus_cash_after_cca
            # Else (during loan term), distributed_dividends_gross remains 0

        elif dividend_strategy == "Distribute All Available Surplus Annually":
            if sci_surplus_cash_after_cca > 0:
                distributed_dividends_gross = sci_surplus_cash_after_cca

        elif dividend_strategy == "Distribute All Net Result Annually (if surplus allows)":
            if net_result_for_dividends > 0 and sci_surplus_cash_after_cca > 0:
                distributed_dividends_gross = min(net_result_for_dividends, sci_surplus_cash_after_cca)

        pfu_on_dividends = distributed_dividends_gross * PFU_RATE
        net_dividends_received_by_investors = distributed_dividends_gross - pfu_on_dividends

        # Direct Investment Calculations
        # annual_scpi_revenue is the same
        # loan_interest_for_year is interest_paid (from loan schedule)
        # annual_loan_payment is loan_annual_payment (from loan schedule)
        taxable_income_direct = max(0, annual_scpi_revenue - interest_paid)
        income_tax_direct = taxable_income_direct * (investor_tmi + SOCIAL_CONTRIBUTIONS_RATE)
        cash_flow_direct_investment = annual_scpi_revenue - loan_annual_payment - income_tax_direct
        effort_de_tresorerie_direct = -cash_flow_direct_investment if cash_flow_direct_investment < 0 else 0

        # Effort de trésorerie for SCI investors is the CCA injection for the year
        effort_de_tresorerie_sci = cca_injection

        results.append({
            "Year": year,
            "SCPI Revenue (€)": annual_scpi_revenue,
            "Loan Interest (€)": interest_paid,
            "Loan Principal (€)": principal_paid,
            "Loan Annual Payment (€)": loan_annual_payment,
            "Management Fees (€)": annual_management_fees,
            "Profit Before Tax (€)": financials['profit_before_tax'],
            "Corporate Tax (IS) (€)": financials['corporate_tax'],
            "Net Result After Tax (€)": financials['net_result_after_tax'], # This is net_result_for_dividends
            "Gross SCI Cash Flow (€)": gross_sci_cash_flow,
            "CCA Injection (€)": cca_injection,
            "CCA Reimbursement (€)": cca_reimbursement,
            "CCA Balance at Year End (€)": cca_balance,
            "SCI Surplus Cash After CCA (€)": sci_surplus_cash_after_cca,
            "Distributed Dividends Gross (€)": distributed_dividends_gross,
            "PFU on Dividends (€)": pfu_on_dividends,
            "Net Dividends to Investors (€)": net_dividends_received_by_investors,

            # Direct Investment Calculation
            "Taxable Income (Direct) (€)": taxable_income_direct,
            "Income Tax (Direct) (€)": income_tax_direct,
            "Cash Flow (Direct) (€)": cash_flow_direct_investment,
            "Effort de Trésorerie (Direct) (€)": effort_de_tresorerie_direct,
            "Effort de Trésorerie SCI (€)": effort_de_tresorerie_sci,
        })

    if results:
        results_df = pd.DataFrame(results)

        # Define column order - Group SCI and Direct investment columns for clarity
        column_order = [
            "Year",
            # SCI Metrics
            "SCPI Revenue (€)", "Management Fees (€)",
            "Loan Interest (€)", "Loan Principal (€)", "Loan Annual Payment (€)",
            "Profit Before Tax (€)", "Corporate Tax (IS) (€)", "Net Result After Tax (€)",
            "Gross SCI Cash Flow (€)",
            "CCA Injection (€)", "CCA Reimbursement (€)", "CCA Balance at Year End (€)",
            "SCI Surplus Cash After CCA (€)",
            "Effort de Trésorerie SCI (€)",
            "Distributed Dividends Gross (€)", "PFU on Dividends (€)", "Net Dividends to Investors (€)",
            # Direct Investment Metrics
            "Taxable Income (Direct) (€)", "Income Tax (Direct) (€)",
            "Cash Flow (Direct) (€)", "Effort de Trésorerie (Direct) (€)",
        ]
        results_df = results_df[column_order]

        # Format columns for display - convert to numeric first for columns that might be object type due to mixed string/float
        columns_to_format = [col for col in column_order if col != "Year"]

        # Store a non-formatted version for charting and calculations
        results_df_numeric = results_df.copy()

        for col in columns_to_format:
            results_df[col] = pd.to_numeric(results_df[col], errors='coerce').map('{:,.2f}'.format)


        st.subheader("Detailed Annual Simulation Results (SCI vs Direct)")
        st.dataframe(results_df) # Display formatted dataframe

        # CSV Download Button
        def convert_df_to_csv(df_to_convert):
            return df_to_convert.to_csv(index=False).encode('utf-8')

        csv_data = convert_df_to_csv(results_df_numeric) # Use numeric df for CSV
        st.download_button(
            label="Download Results as CSV",
            data=csv_data,
            file_name='scpi_simulation_results.csv',
            mime='text/csv',
        )
        st.markdown("---")

        # Summary Metrics
        st.subheader("Summary Comparison over Simulation Period (Before Resale)")
        total_effort_sci = sum(r['Effort de Trésorerie SCI (€)'] for r in results)
        total_effort_direct = sum(r['Effort de Trésorerie (Direct) (€)'] for r in results)
        total_net_dividends_sci = sum(r['Net Dividends to Investors (€)'] for r in results)

        # For direct investment, "net dividends" is essentially the cash flow after tax and loan payments, if positive
        total_net_cashflow_direct_positive = sum(max(0, r['Cash Flow (Direct) (€)']) for r in results)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Effort de Trésorerie SCI", f"{total_effort_sci:,.2f} €")
        col2.metric("Total Effort de Trésorerie Direct", f"{total_effort_direct:,.2f} €")
        col3.metric("Total Net Dividends (SCI)", f"{total_net_dividends_sci:,.2f} €")
        # Adding another row for direct investment's positive cash flow
        st.metric("Total Positive Cash Flow (Direct)", f"{total_net_cashflow_direct_positive:,.2f} €")

        if simulate_resale:
            st.subheader(f"SCPI Resale Simulation Results (Resale at Year {resale_year})")

            holding_period = resale_year
            purchase_price = investment_amount
            # Ensure expected_annual_appreciation_rate is used as a decimal
            resale_value = purchase_price * ((1 + expected_annual_appreciation_rate) ** holding_period)

            # Display common resale info
            resale_info_cols = st.columns(3)
            resale_info_cols[0].metric("Holding Period", f"{holding_period} years")
            resale_info_cols[1].metric("Purchase Price", f"{purchase_price:,.2f} €")
            resale_info_cols[2].metric("Expected Resale Value", f"{resale_value:,.2f} €")

            # Determine remaining loan balance at resale
            remaining_loan_balance_at_resale = 0
            if loan_amount > 0 and actual_loan_duration_input > 0: # Check if there was a loan
                if holding_period <= actual_loan_duration_input: # Resale during loan term
                    if holding_period > 0 and (holding_period -1) < len(amortization_schedule_for_loan_term):
                         # amortization_schedule_for_loan_term stores tuples: (year, annual_payment, principal_paid, interest_paid, remaining_balance)
                         remaining_loan_balance_at_resale = amortization_schedule_for_loan_term[holding_period-1][4]
                # Else (resale after loan term), remaining_loan_balance_at_resale is already 0

            st.write(f"Remaining Loan Balance at Resale: {remaining_loan_balance_at_resale:,.2f} €")
            st.markdown("---")

            # --- SCI Resale Scenario ---
            st.markdown("#### SCI Resale Scenario")
            sci_tax_on_gain, sci_capital_gain = core.calculate_sci_capital_gain_tax_on_resale(
                resale_value, purchase_price, SCI_CAPITAL_GAIN_TAX_RATE_FLAT
            )
            st.write(f"  Capital Gain (SCI): {sci_capital_gain:,.2f} €")
            st.write(f"  Tax on Capital Gain (SCI @ {SCI_CAPITAL_GAIN_TAX_RATE_FLAT*100:.0f}%): {sci_tax_on_gain:,.2f} €")

            proceeds_for_sci_after_cg_tax_and_loan = resale_value - sci_tax_on_gain - remaining_loan_balance_at_resale
            st.write(f"  Proceeds for SCI (after CG tax & loan repayment): {proceeds_for_sci_after_cg_tax_and_loan:,.2f} €")

            final_cca_balance_at_resale_year_end = 0
            if holding_period > 0 and (holding_period -1) < len(results): # results is list of dicts from main sim
                 final_cca_balance_at_resale_year_end = results[holding_period-1]['CCA Balance at Year End (€)']

            st.write(f"  CCA Balance at End of Year {holding_period}: {final_cca_balance_at_resale_year_end:,.2f} €")

            cca_reimbursed_from_sale_proceeds = 0
            if final_cca_balance_at_resale_year_end > 0: # If associates are owed money
                cca_reimbursed_from_sale_proceeds = min(proceeds_for_sci_after_cg_tax_and_loan, final_cca_balance_at_resale_year_end)

            st.write(f"  CCA Reimbursed from Sale Proceeds: {cca_reimbursed_from_sale_proceeds:,.2f} €")

            taxable_dividend_from_sale_proceeds = proceeds_for_sci_after_cg_tax_and_loan - cca_reimbursed_from_sale_proceeds
            st.write(f"  Taxable Dividend from Sale Proceeds (SCI): {max(0, taxable_dividend_from_sale_proceeds):,.2f} €")

            pfu_on_resale_distribution = max(0, taxable_dividend_from_sale_proceeds) * PFU_RATE
            st.write(f"  PFU on Resale Distribution (SCI @ {PFU_RATE*100:.0f}%): {pfu_on_resale_distribution:,.2f} €")

            net_cash_to_associates_from_sale_event_sci = max(0, taxable_dividend_from_sale_proceeds) - pfu_on_resale_distribution + cca_reimbursed_from_sale_proceeds
            st.write(f"  Net Cash to Associates from Resale Event (SCI): {net_cash_to_associates_from_sale_event_sci:,.2f} €")

            sum_annual_net_dividends_sci = sum(r['Net Dividends to Investors (€)'] for r in results[:holding_period])
            sum_annual_effort_sci = sum(r['Effort de Trésorerie SCI (€)'] for r in results[:holding_period])

            overall_net_profit_sci = sum_annual_net_dividends_sci + net_cash_to_associates_from_sale_event_sci - sum_annual_effort_sci
            st.metric("Overall Net Profit (SCI) after Resale", f"{overall_net_profit_sci:,.2f} €", help="Sum of annual net dividends + Net cash from resale event - Sum of annual cash efforts")
            st.markdown("---")

            # --- Direct Investment Resale Scenario ---
            st.markdown("#### Direct Investment Resale Scenario")
            direct_cg_tax_details = core.calculate_direct_investment_capital_gain_tax(resale_value, purchase_price, holding_period)
            direct_total_cg_tax = direct_cg_tax_details['total_tax']

            st.write(f"  Capital Gain (Direct): {direct_cg_tax_details['capital_gain_base']:,.2f} €")
            st.write(f"  Abatement Rate (Income Tax): {direct_cg_tax_details['abatement_rate_income']*100:.2f}%")
            st.write(f"  Abatement Rate (Social Contributions): {direct_cg_tax_details['abatement_rate_social']*100:.2f}%")
            st.write(f"  Tax on Income Portion (Direct): {direct_cg_tax_details['tax_on_income_portion']:,.2f} €")
            st.write(f"  Social Contributions on Gain (Direct): {direct_cg_tax_details['social_contributions_portion']:,.2f} €")
            st.write(f"  Total Capital Gain Tax (Direct): {direct_total_cg_tax:,.2f} €")

            net_cash_to_investor_from_sale_event_direct = resale_value - direct_total_cg_tax - remaining_loan_balance_at_resale
            st.write(f"  Net Cash to Investor from Resale Event (Direct): {net_cash_to_investor_from_sale_event_direct:,.2f} €")

            sum_annual_positive_cash_flow_direct = sum(max(0, r['Cash Flow (Direct) (€)']) for r in results[:holding_period])
            sum_annual_effort_direct = sum(r['Effort de Trésorerie (Direct) (€)'] for r in results[:holding_period])

            overall_net_profit_direct = sum_annual_positive_cash_flow_direct + net_cash_to_investor_from_sale_event_direct - sum_annual_effort_direct
            st.metric("Overall Net Profit (Direct) after Resale", f"{overall_net_profit_direct:,.2f} €", help="Sum of annual positive cash flows + Net cash from resale event - Sum of annual cash efforts")
        st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    # Prepare data for charts using the numeric DataFrame
    chart_data = pd.DataFrame()
    chart_data['Year'] = results_df_numeric['Year']

    # Chart 1: Annual Net Cash Flow to Investor
    chart_data['Net Cash Flow to Investor (SCI)'] = results_df_numeric['Net Dividends to Investors (€)'] - results_df_numeric['Effort de Trésorerie SCI (€)']
    chart_data['Net Cash Flow to Investor (Direct)'] = results_df_numeric['Cash Flow (Direct) (€)']

    st.markdown("##### Annual Net Cash Flow to Investor")
    st.line_chart(chart_data.set_index('Year')[['Net Cash Flow to Investor (SCI)', 'Net Cash Flow to Investor (Direct)']])

    # Chart 2: Cumulative Net Position
    chart_data['Cumulative Net Position (SCI)'] = (results_df_numeric['Net Dividends to Investors (€)'] - results_df_numeric['Effort de Trésorerie SCI (€)']).cumsum()
    chart_data['Cumulative Net Position (Direct)'] = results_df_numeric['Cash Flow (Direct) (€)'].cumsum()

    st.markdown("##### Cumulative Net Financial Position (Investor)")
    st.line_chart(chart_data.set_index('Year')[['Cumulative Net Position (SCI)', 'Cumulative Net Position (Direct)']])
    st.markdown("---")

    # Explanations Expander
    with st.expander("Understanding the Results & Assumptions"):
        st.markdown("""
        **Effort de Trésorerie (Cash Call / Contribution)**:
        - **SCI**: Represents the `CCA Injection (€)`. This is the amount associates need to contribute to the SCI if its cash flow is negative (e.g., loan payments and fees exceed SCPI revenue).
        - **Direct**: Calculated as the negative portion of `Cash Flow (Direct) (€)`. This is the cash an investor needs to cover if annual SCPI revenues (after loan interest) are less than loan payments and income taxes.

        **SCI Taxation**:
        - **Annual Profits**: Taxed at Corporate Income Tax (IS) rates (15% up to €42,500 profit, 25% above).
        - **Distributed Dividends**: Subject to Prélèvement Forfaitaire Unique (PFU) of 30% at the associate level.
        - **Capital Gains on Resale**: For simplicity, this simulation assumes a flat tax rate (`SCI_CAPITAL_GAIN_TAX_RATE_FLAT`, e.g., 15%) on the capital gain realized by the SCI upon resale of SCPI shares. The net proceeds, after CCA settlement, are then distributed as dividends subject to PFU. *(Note: Actual SCI capital gain taxation can be more complex, potentially involving integration with annual profits or specific long-term rates depending on SCI type and holding period of underlying assets.)*

        **Direct Investment Taxation**:
        - **Annual Income (Revenus Fonciers)**: Taxed at the investor's Marginal Tax Rate (TMI) plus Social Contributions (`SOCIAL_CONTRIBUTIONS_RATE`, e.g., 17.2%). Only loan interest is deductible from SCPI revenue to determine taxable income.
        - **Capital Gains on Resale**: Subject to a specific regime involving a base rate of 19% for income tax and 17.2% for social contributions, with abatements applied based on the holding duration (significant reductions after 5 years, full exemption for income tax after 22 years, and for social contributions after 30 years).

        **Key Assumptions**:
        - **CCA for SCI**: Associates' Current Accounts (CCA) are assumed to cover all cash deficits within the SCI. Repayments of CCA occur when the SCI has surplus cash.
        - **Loan Amortization**: Standard annuity loan payment formula is used.
        - **SCPI Yield & Appreciation**: Gross yield and appreciation rates are assumed constant as per inputs.
        - **Fees**: Management fees for SCI are assumed constant. No other transaction fees (e.g., notary, SCPI subscription/exit fees) are modeled unless implicitly part of the investment amount or yield.
        - **Tax Rates**: PFU, Social Contributions, and IS rates are based on current general rates and may change. TMI is an input. The flat rate for SCI capital gain tax is a simplification.
        """)

    else:
        st.write("No results to display. Check input parameters.")

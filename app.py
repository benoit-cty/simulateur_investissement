import streamlit as st
import simulation_core as core # Assuming simulation_core.py is in the same directory
import pandas as pd

st.title("Simulateur d'Investissement en SCPI via une SCI à l'IS")

PFU_RATE = 0.30
SOCIAL_CONTRIBUTIONS_RATE = 0.172

# Sidebar for inputs
st.sidebar.header("Paramètres de Simulation")
investment_amount = st.sidebar.number_input(
    "Investissement Total SCPI (€)",
    min_value=10000, value=150000, step=1000,
    help="Montant total investi en parts de SCPI."
)
loan_amount = st.sidebar.number_input(
    "Montant du Prêt (€)",
    min_value=0, value=150000, step=1000,
    help="Montant emprunté pour financer l'investissement en SCPI. Mettre à 0 si pas de prêt."
)
actual_loan_duration_input = st.sidebar.number_input(
    "Durée du Prêt (années)",
    min_value=0, max_value=30, value=15, step=1,
    help="Durée du prêt en années. Mettre à 0 si pas de prêt."
)
annual_interest_rate = st.sidebar.number_input(
    "Taux d'Intérêt Annuel du Prêt (%)",
    min_value=0.1, max_value=10.0, value=1.2, step=0.1, format="%.3f",
    help="Taux d'intérêt annuel pour le prêt."
) / 100.0
scpi_gross_yield = st.sidebar.number_input(
    "Rendement Brut Annuel SCPI (%)",
    min_value=1.0, max_value=10.0, value=5.0, step=0.1, format="%.3f",
    help="Rendement brut annuel attendu des SCPI avant frais ou impôts."
) / 100.0
annual_management_fees = st.sidebar.number_input(
    "Frais de Gestion Annuels SCI (€)",
    min_value=0, value=462, step=10,
    help="Frais de gestion annuels pour la structure SCI (ex: comptabilité)."
)
investor_tmi = st.sidebar.number_input(
    "Taux Marginal d'Imposition (TMI %)",
    min_value=0.0, max_value=45.0, value=30.0, step=1.0, format="%.1f",
    help="Votre taux marginal d'imposition (ex: 30 pour 30%). Utilisé pour le calcul fiscal de l'investissement direct (TMI + Prélèvements Sociaux)."
) / 100.0

default_sim_years = actual_loan_duration_input if actual_loan_duration_input > 0 else 15
simulation_run_years = st.sidebar.number_input(
    "Nombre Total d'Années de Simulation",
    min_value=1, value=default_sim_years, max_value=50, step=1,
    help="Durée totale pour laquelle la simulation affichera des résultats annuels."
)

dividend_strategy = st.sidebar.selectbox(
    "Stratégie de Distribution des Dividendes (SCI)",
    options=[
        "Pas de Dividendes Pendant la Durée du Prêt",
        "Distribuer Tout l'Excédent Disponible Annuellement",
        "Distribuer Tout le Résultat Net Annuellement (si excédent disponible)"
    ],
    index=0,
    help="Stratégie de distribution des dividendes de la SCI."
)

st.sidebar.header("Simulation de Revente")
simulate_resale = st.sidebar.checkbox("Simuler la Revente des Parts de SCPI", value=True, help="Activer pour simuler la revente des parts de SCPI à une année spécifiée.")
resale_year_input_disabled = not simulate_resale
resale_year = st.sidebar.number_input(
    "Année de Revente",
    min_value=1, value=simulation_run_years, max_value=simulation_run_years, step=1,
    disabled=resale_year_input_disabled,
    help="Année à laquelle les parts de SCPI sont revendues. Doit être <= Nombre Total d'Années de Simulation."
)
expected_annual_appreciation_rate = st.sidebar.number_input(
    "Taux d'Appréciation Annuel Attendu de la Valeur des SCPI (%)",
    min_value=-5.0, value=1.0, max_value=10.0, step=0.1, format="%.1f",
    disabled=resale_year_input_disabled,
    help="Taux annuel auquel la valeur des parts de SCPI est attendue s'apprécier (ou se déprécier)."
) / 100.0

SCI_CAPITAL_GAIN_TAX_RATE_FLAT = 0.15

if st.sidebar.button("Lancer la Simulation"):
    annual_scpi_revenue = core.calculate_scpi_revenue(investment_amount, scpi_gross_yield)

    amortization_schedule_for_loan_term = []
    if loan_amount > 0 and actual_loan_duration_input > 0:
        amortization_schedule_for_loan_term = core.calculate_loan_amortization(loan_amount, annual_interest_rate, actual_loan_duration_input)

    results = []
    cca_balance = 0

    for year_idx in range(simulation_run_years):
        year = year_idx + 1

        loan_annual_payment = 0
        principal_paid = 0
        interest_paid = 0

        if loan_amount > 0 and year <= actual_loan_duration_input:
            if year_idx < len(amortization_schedule_for_loan_term):
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
            sci_surplus_cash_after_cca = 0
        else:
            if cca_balance > 0:
                cca_reimbursement = min(gross_sci_cash_flow, cca_balance)
                cca_balance -= cca_reimbursement
            sci_surplus_cash_after_cca = gross_sci_cash_flow - cca_reimbursement

        distributed_dividends_gross = 0
        net_result_for_dividends = financials['net_result_after_tax']
        current_year_is_during_loan_term = (year <= actual_loan_duration_input if loan_amount > 0 else False)

        if dividend_strategy == "Pas de Dividendes Pendant la Durée du Prêt":
            if not current_year_is_during_loan_term:
                 if sci_surplus_cash_after_cca > 0:
                    distributed_dividends_gross = sci_surplus_cash_after_cca
        elif dividend_strategy == "Distribuer Tout l'Excédent Disponible Annuellement":
            if sci_surplus_cash_after_cca > 0:
                distributed_dividends_gross = sci_surplus_cash_after_cca
        elif dividend_strategy == "Distribuer Tout le Résultat Net Annuellement (si excédent disponible)":
            if net_result_for_dividends > 0 and sci_surplus_cash_after_cca > 0:
                distributed_dividends_gross = min(net_result_for_dividends, sci_surplus_cash_after_cca)

        pfu_on_dividends = distributed_dividends_gross * PFU_RATE
        net_dividends_received_by_investors = distributed_dividends_gross - pfu_on_dividends

        taxable_income_direct = max(0, annual_scpi_revenue - interest_paid)
        income_tax_direct = taxable_income_direct * (investor_tmi + SOCIAL_CONTRIBUTIONS_RATE)
        cash_flow_direct_investment = annual_scpi_revenue - loan_annual_payment - income_tax_direct
        effort_de_tresorerie_direct = -cash_flow_direct_investment if cash_flow_direct_investment < 0 else 0
        effort_de_tresorerie_sci = cca_injection

        results.append({
            "Année": year,
            "Revenus SCPI (€)": annual_scpi_revenue,
            "Intérêts du Prêt (€)": interest_paid,
            "Principal Remboursé (€)": principal_paid,
            "Annuité du Prêt (€)": loan_annual_payment,
            "Frais de Gestion SCI (€)": annual_management_fees,
            "Bénéfice Avant Impôt (SCI) (€)": financials['profit_before_tax'],
            "Impôt sur les Sociétés (IS) (€)": financials['corporate_tax'],
            "Résultat Net Après IS (SCI) (€)": financials['net_result_after_tax'],
            "Flux de Trésorerie Brut SCI (€)": gross_sci_cash_flow,
            "Injection en CCA (€)": cca_injection,
            "Remboursement de CCA (€)": cca_reimbursement,
            "Solde CCA Fin d'Année (€)": cca_balance,
            "Excédent Trésorerie SCI post-CCA (€)": sci_surplus_cash_after_cca,
            "Effort de Trésorerie SCI (€)": effort_de_tresorerie_sci, # This is CCA Injection
            "Dividendes Bruts Distribués (SCI) (€)": distributed_dividends_gross,
            "PFU sur Dividendes (SCI) (€)": pfu_on_dividends,
            "Dividendes Nets Investisseurs (SCI) (€)": net_dividends_received_by_investors,
            "Revenu Imposable (Direct) (€)": taxable_income_direct,
            "Impôt sur le Revenu (Direct) (€)": income_tax_direct,
            "Flux de Trésorerie (Direct) (€)": cash_flow_direct_investment,
            "Effort de Trésorerie (Direct) (€)": effort_de_tresorerie_direct,
        })

    if results:
        results_df_numeric = pd.DataFrame(results) # Keep numeric for calcs and CSV
        results_df_display = results_df_numeric.copy() # For formatted display

        column_order = [
            "Année",
            "Revenus SCPI (€)", "Frais de Gestion SCI (€)",
            "Intérêts du Prêt (€)", "Principal Remboursé (€)", "Annuité du Prêt (€)",
            "Bénéfice Avant Impôt (SCI) (€)", "Impôt sur les Sociétés (IS) (€)", "Résultat Net Après IS (SCI) (€)",
            "Flux de Trésorerie Brut SCI (€)",
            "Injection en CCA (€)", "Remboursement de CCA (€)", "Solde CCA Fin d'Année (€)",
            "Excédent Trésorerie SCI post-CCA (€)",
            "Effort de Trésorerie SCI (€)",
            "Dividendes Bruts Distribués (SCI) (€)", "PFU sur Dividendes (SCI) (€)", "Dividendes Nets Investisseurs (SCI) (€)",
            "Revenu Imposable (Direct) (€)", "Impôt sur le Revenu (Direct) (€)",
            "Flux de Trésorerie (Direct) (€)", "Effort de Trésorerie (Direct) (€)",
        ]
        results_df_display = results_df_display[column_order]
        results_df_numeric = results_df_numeric[column_order] # Ensure numeric also has same order for consistency if needed

        columns_to_format = [col for col in column_order if col != "Année"]
        for col in columns_to_format:
            results_df_display[col] = pd.to_numeric(results_df_display[col], errors='coerce').map('{:,.2f}'.format)

        st.subheader("Résultats Annuels Détaillés de la Simulation (SCI vs Direct)")
        st.dataframe(results_df_display)

        def convert_df_to_csv(df_to_convert):
            return df_to_convert.to_csv(index=False).encode('utf-8')

        csv_data = convert_df_to_csv(results_df_numeric)
        st.download_button(
            label="Télécharger les Résultats en CSV",
            data=csv_data,
            file_name='resultats_simulation_scpi.csv',
            mime='text/csv',
        )
        st.markdown("---")

        st.subheader("Comparaison Synthétique sur la Période (Avant Revente)")
        total_effort_sci = results_df_numeric['Effort de Trésorerie SCI (€)'].sum()
        total_effort_direct = results_df_numeric['Effort de Trésorerie (Direct) (€)'].sum()
        total_net_dividends_sci = results_df_numeric['Dividendes Nets Investisseurs (SCI) (€)'].sum()
        total_net_cashflow_direct_positive = results_df_numeric['Flux de Trésorerie (Direct) (€)'][results_df_numeric['Flux de Trésorerie (Direct) (€)'] > 0].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Effort Total de Trésorerie SCI", f"{total_effort_sci:,.2f} €")
        col2.metric("Effort Total de Trésorerie Direct", f"{total_effort_direct:,.2f} €")
        col3.metric("Total Dividendes Nets (SCI)", f"{total_net_dividends_sci:,.2f} €")
        st.metric("Total Flux de Trésorerie Positifs (Direct)", f"{total_net_cashflow_direct_positive:,.2f} €")
        st.markdown("---")

        # Visualizations
        st.subheader("Visualisations")
        chart_data = pd.DataFrame()
        chart_data['Année'] = results_df_numeric['Année']

        # Chart 1: Annual Net Cash Flow to Investor
        # French column names for chart series
        col_name_sci_net_flow = "Flux Net de Trésorerie Investisseur (SCI) (€)"
        col_name_direct_net_flow = "Flux Net de Trésorerie Investisseur (Direct) (€)"
        chart_data[col_name_sci_net_flow] = results_df_numeric['Dividendes Nets Investisseurs (SCI) (€)'] - results_df_numeric['Effort de Trésorerie SCI (€)']
        chart_data[col_name_direct_net_flow] = results_df_numeric['Flux de Trésorerie (Direct) (€)']

        st.markdown("##### Flux Annuel Net de Trésorerie pour l'Investisseur")
        st.line_chart(chart_data.set_index('Année')[[col_name_sci_net_flow, col_name_direct_net_flow]])

        # Chart 2: Cumulative Net Position
        col_name_sci_cumulative = "Position Nette Cumulative (SCI) (€)"
        col_name_direct_cumulative = "Position Nette Cumulative (Direct) (€)"
        chart_data[col_name_sci_cumulative] = (results_df_numeric['Dividendes Nets Investisseurs (SCI) (€)'] - results_df_numeric['Effort de Trésorerie SCI (€)']).cumsum()
        chart_data[col_name_direct_cumulative] = results_df_numeric['Flux de Trésorerie (Direct) (€)'].cumsum()

        st.markdown("##### Position Financière Nette Cumulative de l'Investisseur")
        st.line_chart(chart_data.set_index('Année')[[col_name_sci_cumulative, col_name_direct_cumulative]])
        st.markdown("---")

        if simulate_resale:
            st.subheader(f"Résultats de la Simulation de Revente (Année {resale_year})")

            holding_period = resale_year
            purchase_price = investment_amount
            resale_value = purchase_price * ((1 + expected_annual_appreciation_rate) ** holding_period)

            resale_info_cols = st.columns(3)
            resale_info_cols[0].metric("Durée de Détention", f"{holding_period} ans")
            resale_info_cols[1].metric("Prix d'Achat", f"{purchase_price:,.2f} €")
            resale_info_cols[2].metric("Valeur de Revente Attendue", f"{resale_value:,.2f} €")

            remaining_loan_balance_at_resale = 0
            if loan_amount > 0 and actual_loan_duration_input > 0:
                if holding_period <= actual_loan_duration_input:
                    if holding_period > 0 and (holding_period -1) < len(amortization_schedule_for_loan_term):
                         remaining_loan_balance_at_resale = amortization_schedule_for_loan_term[holding_period-1][4]

            st.write(f"Solde Prêt Restant Dû à la Revente: {remaining_loan_balance_at_resale:,.2f} €")
            st.markdown("---")

            st.markdown("#### Scénario de Revente SCI")
            sci_tax_on_gain, sci_capital_gain = core.calculate_sci_capital_gain_tax_on_resale(
                resale_value, purchase_price, SCI_CAPITAL_GAIN_TAX_RATE_FLAT
            )
            st.write(f"  Plus-value (SCI): {sci_capital_gain:,.2f} €")
            st.write(f"  Impôt sur Plus-value (SCI @ {SCI_CAPITAL_GAIN_TAX_RATE_FLAT*100:.0f}%): {sci_tax_on_gain:,.2f} €")

            proceeds_for_sci_after_cg_tax_and_loan = resale_value - sci_tax_on_gain - remaining_loan_balance_at_resale
            st.write(f"  Produit Net pour SCI (après impôt PV & remboursement prêt): {proceeds_for_sci_after_cg_tax_and_loan:,.2f} €")

            final_cca_balance_at_resale_year_end = 0
            if holding_period > 0 and (holding_period -1) < len(results):
                 final_cca_balance_at_resale_year_end = results[holding_period-1]['Solde CCA Fin d'Année (€)'] # Using French column name from 'results' dict

            st.write(f"  Solde CCA en Fin d'Année {holding_period}: {final_cca_balance_at_resale_year_end:,.2f} €")

            cca_reimbursed_from_sale_proceeds = 0
            if final_cca_balance_at_resale_year_end > 0:
                cca_reimbursed_from_sale_proceeds = min(proceeds_for_sci_after_cg_tax_and_loan, final_cca_balance_at_resale_year_end)

            st.write(f"  CCA Remboursé sur Produit de Cession: {cca_reimbursed_from_sale_proceeds:,.2f} €")

            taxable_dividend_from_sale_proceeds = proceeds_for_sci_after_cg_tax_and_loan - cca_reimbursed_from_sale_proceeds
            st.write(f"  Dividende Imposable sur Produit de Cession (SCI): {max(0, taxable_dividend_from_sale_proceeds):,.2f} €")

            pfu_on_resale_distribution = max(0, taxable_dividend_from_sale_proceeds) * PFU_RATE
            st.write(f"  PFU sur Distribution de Revente (SCI @ {PFU_RATE*100:.0f}%): {pfu_on_resale_distribution:,.2f} €")

            net_cash_to_associates_from_sale_event_sci = max(0, taxable_dividend_from_sale_proceeds) - pfu_on_resale_distribution + cca_reimbursed_from_sale_proceeds
            st.write(f"  Trésorerie Nette aux Associés (Événement de Revente SCI): {net_cash_to_associates_from_sale_event_sci:,.2f} €")

            sum_annual_net_dividends_sci = results_df_numeric['Dividendes Nets Investisseurs (SCI) (€)'].iloc[:holding_period].sum()
            sum_annual_effort_sci = results_df_numeric['Effort de Trésorerie SCI (€)'].iloc[:holding_period].sum()

            overall_net_profit_sci = sum_annual_net_dividends_sci + net_cash_to_associates_from_sale_event_sci - sum_annual_effort_sci
            st.metric("Bénéfice Net Global (SCI) après Revente", f"{overall_net_profit_sci:,.2f} €", help="Somme des dividendes nets annuels + Trésorerie nette de l'événement de revente - Somme des efforts de trésorerie annuels")
            st.markdown("---")

            st.markdown("#### Scénario de Revente Investissement Direct")
            direct_cg_tax_details = core.calculate_direct_investment_capital_gain_tax(resale_value, purchase_price, holding_period)
            direct_total_cg_tax = direct_cg_tax_details['total_tax']

            st.write(f"  Plus-value (Direct): {direct_cg_tax_details['capital_gain_base']:,.2f} €")
            st.write(f"  Taux d'Abattement (Impôt sur le Revenu): {direct_cg_tax_details['abatement_rate_income']*100:.2f}%")
            st.write(f"  Taux d'Abattement (Prélèvements Sociaux): {direct_cg_tax_details['abatement_rate_social']*100:.2f}%")
            st.write(f"  Part Impôt sur le Revenu (Direct): {direct_cg_tax_details['tax_on_income_portion']:,.2f} €")
            st.write(f"  Part Prélèvements Sociaux sur Plus-value (Direct): {direct_cg_tax_details['social_contributions_portion']:,.2f} €")
            st.write(f"  Total Impôt sur Plus-value (Direct): {direct_total_cg_tax:,.2f} €")

            net_cash_to_investor_from_sale_event_direct = resale_value - direct_total_cg_tax - remaining_loan_balance_at_resale
            st.write(f"  Trésorerie Nette à l'Investisseur (Événement de Revente Direct): {net_cash_to_investor_from_sale_event_direct:,.2f} €")

            sum_annual_positive_cash_flow_direct = results_df_numeric['Flux de Trésorerie (Direct) (€)'].iloc[:holding_period][results_df_numeric['Flux de Trésorerie (Direct) (€)'].iloc[:holding_period] > 0].sum()
            sum_annual_effort_direct = results_df_numeric['Effort de Trésorerie (Direct) (€)'].iloc[:holding_period].sum()

            overall_net_profit_direct = sum_annual_positive_cash_flow_direct + net_cash_to_investor_from_sale_event_direct - sum_annual_effort_direct
            st.metric("Bénéfice Net Global (Direct) après Revente", f"{overall_net_profit_direct:,.2f} €", help="Somme des flux de trésorerie positifs annuels + Trésorerie nette de l'événement de revente - Somme des efforts de trésorerie annuels")
        st.markdown("---")

    with st.expander("Comprendre les Résultats & Hypothèses"):
        st.markdown("""
        **Effort de Trésorerie (Appel de Fonds / Contribution)**:
        - **SCI**: Représente l'`Injection en CCA (€)`. C'est le montant que les associés doivent apporter à la SCI si sa trésorerie est négative (ex: les remboursements de prêt et frais dépassent les revenus SCPI).
        - **Direct**: Calculé comme la part négative du `Flux de Trésorerie (Direct) (€)`. C'est la trésorerie que l'investisseur doit couvrir si les revenus annuels SCPI (après intérêts d'emprunt) sont inférieurs aux remboursements de prêt et à l'impôt sur le revenu.

        **Fiscalité SCI**:
        - **Bénéfices Annuels**: Imposés à l'Impôt sur les Sociétés (IS) (15% jusqu'à 42 500€ de bénéfice, 25% au-delà).
        - **Dividendes Distribués**: Soumis au Prélèvement Forfaitaire Unique (PFU) de 30% au niveau de l'associé.
        - **Plus-values de Cession**: Pour simplifier, cette simulation applique un taux forfaitaire (`SCI_CAPITAL_GAIN_TAX_RATE_FLAT`, ex: 15%) sur la plus-value réalisée par la SCI lors de la revente des parts de SCPI. Le produit net, après apurement du CCA, est ensuite distribué sous forme de dividendes soumis au PFU. *(Note : La fiscalité réelle des plus-values de SCI peut être plus complexe, impliquant une réintégration aux bénéfices annuels ou des taux spécifiques pour les plus-values à long terme selon le type de SCI et la durée de détention des actifs sous-jacents.)*

        **Fiscalité Investissement Direct**:
        - **Revenus Annuels (Revenus Fonciers)**: Imposés au Taux Marginal d'Imposition (TMI) de l'investisseur, majoré des Prélèvements Sociaux (`SOCIAL_CONTRIBUTIONS_RATE`, ex: 17.2%). Seuls les intérêts d'emprunt sont déductibles des revenus SCPI pour déterminer le revenu imposable.
        - **Plus-values de Cession**: Soumises à un régime spécifique avec un taux de base de 19% pour l'impôt sur le revenu et 17.2% pour les prélèvements sociaux, avec des abattements appliqués selon la durée de détention (réductions significatives après 5 ans, exonération totale d'IR après 22 ans, et de PS après 30 ans).

        **Hypothèses Clés**:
        - **CCA pour SCI**: Les Comptes Courants d'Associés (CCA) sont supposés couvrir tous les déficits de trésorerie au sein de la SCI. Les remboursements de CCA interviennent lorsque la SCI dispose d'un excédent de trésorerie.
        - **Amortissement du Prêt**: Formule standard de remboursement de prêt à annuités constantes.
        - **Rendement & Appréciation SCPI**: Le rendement brut et les taux d'appréciation sont supposés constants selon les entrées.
        - **Frais**: Les frais de gestion de la SCI sont supposés constants. Aucun autre frais de transaction (ex: notaire, frais de souscription/sortie SCPI) n'est modélisé sauf s'ils sont implicitement inclus dans le montant de l'investissement ou le rendement.
        - **Taux d'Imposition**: PFU, Prélèvements Sociaux, et taux d'IS sont basés sur les taux généraux actuels et peuvent évoluer. Le TMI est une entrée. Le taux forfaitaire pour l'impôt sur les plus-values de la SCI est une simplification.
        """)

    else:
        st.write("Aucun résultat à afficher. Vérifiez les paramètres d'entrée.")

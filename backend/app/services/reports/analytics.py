"""
Deterministic Analytics Engine for Official Reports
Computes statutory reserve deductions, stripping ratio, Life of Mine,
and Mine Closure Escrow with the mandatory 2025 Just Transition 25% earmarking.
Preserves explicit calculation lineage for every computed figure. Zero LLM math.
"""
from typing import Dict, Any, Tuple


class ReportAnalyticsEngine:

    @staticmethod
    def calculate_reserves_lineage(
        proved_mt: float,
        indicated_mt: float,
        inferred_mt: float,
        geological_deduction_pct: float,
        blocked_reserves_mt: float,
        mining_loss_pct: float,
        prior_depleted_mt: float,
    ) -> Dict[str, Any]:
        """
        Calculates the 7-step reserve deduction hierarchy per UNFC/ISP & MoC 2025 Appendix-I:
        1. Gross Geological Reserve
        2. Geological Deduction
        3. Net Geological Reserve
        4. Blocked Reserves
        5. Minable Reserve
        6. Mining Losses & Extractable Reserve
        7. Recovery % and Balance Reserves
        """
        gross_total = round(proved_mt + indicated_mt + inferred_mt, 3)
        geo_deduction = round(gross_total * (geological_deduction_pct / 100.0), 3)
        net_geological = round(max(0.0, gross_total - geo_deduction), 3)
        minable = round(max(0.0, net_geological - blocked_reserves_mt), 3)
        mining_loss = round(minable * (mining_loss_pct / 100.0), 3)
        extractable = round(max(0.0, minable - mining_loss), 3)
        recovery_pct = round((extractable / minable * 100.0), 2) if minable > 0 else 0.0
        balance = round(max(0.0, extractable - prior_depleted_mt), 3)

        lineage = {
            "methodology": "UNFC / ISP Guidelines (2025 Appendix-I Section 2.3)",
            "inputs": {
                "proved_mt": proved_mt,
                "indicated_mt": indicated_mt,
                "inferred_mt": inferred_mt,
                "geological_deduction_pct": geological_deduction_pct,
                "blocked_reserves_mt": blocked_reserves_mt,
                "mining_loss_pct": mining_loss_pct,
                "prior_depleted_mt": prior_depleted_mt,
            },
            "steps": [
                {
                    "step": 1,
                    "name": "Gross Geological Reserve",
                    "formula": "proved_mt + indicated_mt + inferred_mt",
                    "result": gross_total,
                    "unit": "MT",
                },
                {
                    "step": 2,
                    "name": "Geological Deductions (Faults/Intrusions)",
                    "formula": f"gross_total * ({geological_deduction_pct}%)",
                    "result": geo_deduction,
                    "unit": "MT",
                },
                {
                    "step": 3,
                    "name": "Net Geological Reserve",
                    "formula": "gross_total - geo_deduction",
                    "result": net_geological,
                    "unit": "MT",
                },
                {
                    "step": 4,
                    "name": "Blocked Coal Reserves",
                    "formula": "Statutory safety barriers, river HFL, rail/road corridors",
                    "result": blocked_reserves_mt,
                    "unit": "MT",
                },
                {
                    "step": 5,
                    "name": "Minable Reserve",
                    "formula": "net_geological - blocked_reserves_mt",
                    "result": minable,
                    "unit": "MT",
                },
                {
                    "step": 6,
                    "name": "Mining Losses & Extractable Reserve",
                    "formula": f"minable - ({mining_loss_pct}% operational mining loss)",
                    "mining_loss": mining_loss,
                    "extractable_reserve": extractable,
                    "recovery_pct": recovery_pct,
                    "unit": "MT",
                },
                {
                    "step": 7,
                    "name": "Balance Extractable Reserves",
                    "formula": "extractable - prior_depleted_mt",
                    "result": balance,
                    "unit": "MT",
                },
            ],
            "outputs": {
                "gross_geological_mt": gross_total,
                "geological_deduction_mt": geo_deduction,
                "net_geological_mt": net_geological,
                "blocked_reserves_mt": blocked_reserves_mt,
                "minable_mt": minable,
                "mining_loss_mt": mining_loss,
                "extractable_mt": extractable,
                "recovery_pct": recovery_pct,
                "balance_mt": balance,
            },
        }

        return lineage

    @staticmethod
    def calculate_stripping_ratio_lineage(ob_volume_mcum: float, coal_tonnage_mt: float) -> Dict[str, Any]:
        """Calculate Average Stripping Ratio: Volume of OB (Mcum) / Coal Tonnage (MT)."""
        sr = round(ob_volume_mcum / coal_tonnage_mt, 2) if coal_tonnage_mt > 0 else 0.0
        return {
            "formula": "ob_volume_mcum / coal_tonnage_mt",
            "inputs": {"ob_volume_mcum": ob_volume_mcum, "coal_tonnage_mt": coal_tonnage_mt},
            "result": sr,
            "unit": "cum/tonne",
        }

    @staticmethod
    def calculate_lom_lineage(extractable_mt: float, rated_capacity_mtpa: float) -> Dict[str, Any]:
        """Calculate Life of Mine (LOM): Extractable Reserves / Rated Capacity."""
        lom = round(extractable_mt / rated_capacity_mtpa, 1) if rated_capacity_mtpa > 0 else 0.0
        return {
            "formula": "extractable_mt / rated_capacity_mtpa",
            "inputs": {"extractable_mt": extractable_mt, "rated_capacity_mtpa": rated_capacity_mtpa},
            "result": lom,
            "unit": "Years",
        }

    @staticmethod
    def calculate_mine_closure_escrow_lineage(
        project_area_ha: float,
        is_opencast: bool = True,
        base_rate_lakh_ha: float = None,
        wpi_factor: float = 1.018,
        mine_life_years: int = 25,
    ) -> Dict[str, Any]:
        """
        Calculates Mine Closure Escrow per Section 3.5.1 and Section 8.10.2 of 2025 Guidelines.
        Base rate (May 2024): 14.0 Lakh/Ha for Opencast, 2.0 Lakh/Ha for Underground.
        Escalated by WPI ratio and compounded @ 5% annually.
        """
        if base_rate_lakh_ha is None:
            base_rate_lakh_ha = 14.0 if is_opencast else 2.0

        escalated_rate = round(base_rate_lakh_ha * wpi_factor, 4)
        total_closure_cost = round(project_area_ha * escalated_rate, 2)
        annual_deposit = round(total_closure_cost / mine_life_years, 2) if mine_life_years > 0 else 0.0
        annual_compounded_deposit = round(annual_deposit * 1.05, 2)

        return {
            "statutory_rule": "Ministry of Coal 2025 Guidelines Section 3.5.1 & Section 8.10.2",
            "source_reference": "Guidelines Page 14 & Appendix-I Item 8.10.2 (Pages 49-51 of 83)",
            "inputs": {
                "project_area_ha": project_area_ha,
                "mining_type": "Opencast (OC)" if is_opencast else "Underground (UG)",
                "base_rate_lakh_ha": base_rate_lakh_ha,
                "base_date": "May 2024",
                "wpi_factor": wpi_factor,
                "mine_life_years": mine_life_years,
            },
            "escalated_rate_lakh_ha": escalated_rate,
            "total_closure_cost_lakh": total_closure_cost,
            "annual_escrow_deposit_lakh": annual_deposit,
            "annual_compounded_deposit_lakh": annual_compounded_deposit,
            "compounding_rate_pct": 5.0,
            "lineage": [
                f"1. Base Rate ({('Opencast' if is_opencast else 'Underground')}) = {base_rate_lakh_ha} Lakh INR/Ha (Base May 2024)",
                f"2. Escalated Rate = {base_rate_lakh_ha} * {wpi_factor} = {escalated_rate} Lakh INR/Ha",
                f"3. Total Closure Cost = {project_area_ha} Ha * {escalated_rate} Lakh/Ha = {total_closure_cost} Lakh INR",
                f"4. Annual Deposit = {total_closure_cost} Lakh INR / {mine_life_years} Yrs = {annual_deposit} Lakh INR/year",
                f"5. Annual Deposit with 5% Compounding = {annual_deposit} * 1.05 = {annual_compounded_deposit} Lakh INR/year",
            ],
        }

    @staticmethod
    def calculate_community_development_escrow(
        five_yearly_escrow_deposit_lakh: float,
        activity_claims_lakh: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """
        Rule A: Community Development & Livelihood Projects (5-Yearly Escrow Head).
        Statutory Clause: Section 3.5.5(ii), Page 14 of 83 (PDF Page 16).
        - Mandatory minimum 25% of five-yearly escrow amount deposited for community development (Appendix-IX).
        - Maximum expenditure on any single activity capped at one-third (33.33%) of the earmarked amount.
        """
        min_earmarked_lakh = round(five_yearly_escrow_deposit_lakh * 0.25, 2)
        single_activity_cap_lakh = round(min_earmarked_lakh / 3.0, 2)

        claims_audit = []
        violations = []
        total_claimed = 0.0

        if activity_claims_lakh:
            for act_name, amt in activity_claims_lakh.items():
                amt_round = round(amt, 2)
                total_claimed += amt_round
                is_exceeded = amt_round > single_activity_cap_lakh + 0.01
                if is_exceeded:
                    violations.append({
                        "activity": act_name,
                        "claimed_lakh": amt_round,
                        "cap_lakh": single_activity_cap_lakh,
                        "excess_lakh": round(amt_round - single_activity_cap_lakh, 2),
                    })
                claims_audit.append({
                    "activity": act_name,
                    "claimed_lakh": amt_round,
                    "status": "EXCEEDS_STATUTORY_CAP" if is_exceeded else "COMPLIANT",
                })

        return {
            "statutory_rule": "Rule A: Community Development & Livelihood Projects (Section 3.5.5(ii))",
            "source_reference": "Guidelines Page 14 of 83 (PDF Page 16) & Appendix-IX",
            "five_yearly_deposit_lakh": five_yearly_escrow_deposit_lakh,
            "min_earmarked_lakh": min_earmarked_lakh,
            "min_earmarked_pct": 25.0,
            "single_activity_cap_lakh": single_activity_cap_lakh,
            "single_activity_cap_pct": 33.33,
            "total_claimed_lakh": round(total_claimed, 2),
            "claims_audit": claims_audit,
            "has_cap_violations": len(violations) > 0,
            "cap_violations": violations,
            "lineage": [
                f"1. Five-Yearly Escrow Deposited = {five_yearly_escrow_deposit_lakh} Lakh INR",
                f"2. Minimum Statutory Earmarking (25%) = {min_earmarked_lakh} Lakh INR",
                f"3. Maximum Single Activity Cap (1/3 of Earmarked) = {single_activity_cap_lakh} Lakh INR",
            ],
        }

    @staticmethod
    def calculate_just_transformation_corpus(
        final_closure_balance_deposited_lakh: float,
    ) -> Dict[str, Any]:
        """
        Rule B: Just Transformation Corpus (Final Mine Closure Head).
        Statutory Clause: Section 3.5.5(iv), Page 15 of 83 (PDF Page 17).
        - Corpus of 10% of the balance deposited amount from final mine closure cost created towards Just Transformation.
        - Plan must be prepared and agency engaged before reimbursement of remaining 90% balance (Section 3.5.5(iii)).
        """
        just_transformation_corpus_lakh = round(final_closure_balance_deposited_lakh * 0.10, 2)
        reimbursable_90_pct_balance_lakh = round(final_closure_balance_deposited_lakh * 0.90, 2)

        return {
            "statutory_rule": "Rule B: Just Transformation Corpus (Section 3.5.5(iv))",
            "source_reference": "Guidelines Page 15 of 83 (PDF Page 17) & Section 3.2",
            "final_closure_balance_deposited_lakh": final_closure_balance_deposited_lakh,
            "just_transformation_corpus_lakh": just_transformation_corpus_lakh,
            "just_transformation_corpus_pct": 10.0,
            "reimbursable_90_pct_balance_lakh": reimbursable_90_pct_balance_lakh,
            "release_precondition": (
                "Proponent must prepare plan for socio-transition and engage implementation agency "
                "before release of the 90% balance amount per Section 3.5.5(iv)."
            ),
            "lineage": [
                f"1. Final Closure Balance Deposited Amount = {final_closure_balance_deposited_lakh} Lakh INR",
                f"2. Dedicated Just Transformation Corpus (10%) = {just_transformation_corpus_lakh} Lakh INR",
                f"3. Balance Reimbursable upon Verification (90%) = {reimbursable_90_pct_balance_lakh} Lakh INR",
            ],
        }

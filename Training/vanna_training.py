import sqlite3
from pathlib import Path

# Use the correct path to your DB file in Drive
PROJECT_ROOT = Path(__file__).resolve().parent.parent
db_path = PROJECT_ROOT / "Underwriter_Data.db"

import vanna as vn
from vanna.remote import VannaDefault
import os
from dotenv import load_dotenv

load_dotenv()
vanna_api_key = os.getenv("vanna_api_key")
vanna_model_name = os.getenv("vanna_model_name")

# print(vanna_api_key)
# print(vanna_model_name)

vn = VannaDefault(model=vanna_model_name, api_key=vanna_api_key)
vn.connect_to_sqlite(str(db_path))
vn.allow_llm_to_see_data = True

import streamlit as st

# st.write(db_path)
st.write(vn.ask("Show me loss ratio for casualty insuarnce"))

# vn.ask("Show me loss ratio for casualty insuarnce")
# print(vn.ask("Show me loss ratio for casualty insuarnce"))

# # Example: training Vanna with your underwriting table
# vn.train(ddl="""
# CREATE TABLE underwriting_dataset (
# 	insured_name TEXT,
# 	insured_address TEXT,
#     country_of_incorporation TEXT,
#     business_description TEXT,
#     risk_type TEXT,
# 	broker_contact TEXT,
# 	class_of_business TEXT,
# 	submission_date DATE,
#     claims_frequency INT,
#     largest_single_loss FLOAT,
#     incurred_loss FLOAT,
#     ultimate_premium FLOAT,
#     loss_ratio FLOAT,
#     tiv FLOAT 
# );
# """)

# vn.train(documentation="""

# Underwriting_Dataset Table Documentation
# =========================================

# This table contains structured underwriting portfolio data used for AI-driven risk benchmarking,
# loss performance analysis, broker evaluation, and underwriting decision support.

# --------------------------------------------
# Core Loss & Performance Metrics
# --------------------------------------------

# - claims_frequency:
#   Represents the total number of reported claims for the insured account
#   within the defined observation period (typically 3–5 years).
#   Used to assess frequency-driven risk behavior.

# - largest_single_loss:
#   The highest individual claim amount recorded for the insured within the observation period.
#   Used to measure severity exposure.

# - incurred_loss:
#   Total loss incurred to date, including:
#   - Paid losses
#   - Case reserves (outstanding reported claims)
#   Excludes future projection unless stated otherwise.

# - ultimate_premium:
#   The final expected premium for the policy after adjustments,
#   endorsements, and exposure updates.
#   Used as denominator for performance metrics.

# - loss_ratio:
#   Calculated as:
#       (incurred_loss / ultimate_premium) * 100
#   Expressed as percentage.
#   Used to evaluate underwriting profitability.
#   Loss Ratio > 100% indicates underwriting loss before expenses.

# --------------------------------------------
# Insured Information
# --------------------------------------------

# - insured_name:
#   Legal name of the insured entity.

# - insured_address:
#   Primary registered or operational address of the insured.

# - country_of_incorporation:
#   Country where the insured entity is legally registered.
#   Used for geographic risk segmentation and regulatory analysis.

# - business_description:
#   Short description of insured's primary operations.
#   Used to classify hazard exposure and underwriting appetite.

# --------------------------------------------
# Risk Classification
# --------------------------------------------

# - risk_type:
#   Specifies underwriting risk category, such as:
#   'Industrial All Risks',
#   'Marine Hull',
#   'Products Liability',
#   'Professional Indemnity',
#   'Energy Offshore',
#   'General Liability'.

#   Used to segment portfolio and compare homogeneous exposures.

# - class_of_business:
#   Higher-level grouping such as:
#   'Property Damage & BI',
#   'Marine',
#   'Products Liability',
#   'Financial Lines',
#   'Energy',
#   'Casualty'.

#   Used for portfolio-level aggregation and capital allocation.

# - tiv (Total Insured Value):
#   Represents total value at risk insured under the policy.
#   For Property: total asset value.
#   For Liability: may represent proxy exposure (e.g., turnover-based limit indicator).
#   Used to measure severity potential.

# --------------------------------------------
# Broker & Placement Information
# --------------------------------------------

# - broker_contact:
#   Name of intermediary or brokerage firm responsible for placement.
#   Used to evaluate broker performance and distribution analytics.

# - submission_date:
#   Date the underwriting submission was received.
#   Used for trend analysis, time-based performance tracking,
#   and underwriting cycle assessment.

# --------------------------------------------
# Derived / Analytical Metrics
# --------------------------------------------

# - Premium to TIV Ratio:
#   Calculated as:
#       ultimate_premium / tiv
#   Used to approximate rate-on-line or pricing adequacy proxy.

# - Weighted Portfolio Loss Ratio:
#   Calculated as:
#       SUM(incurred_loss) / SUM(ultimate_premium) * 100
#   Used to evaluate aggregate underwriting performance.

# - Risk Band Classification:
#   Suggested segmentation based on loss_ratio:
#       <= 50%   → Low Risk
#       50–80%   → Medium Risk
#       > 80%    → High Risk

# - Case Reserve Proxy:
#   If paid_loss is available:
#       Case Reserve = incurred_loss - paid_loss

# --------------------------------------------
# Underwriting Interpretation Guidelines
# --------------------------------------------

# - Loss Ratio < 60%:
#   Generally attractive risk, subject to trend stability.

# - Loss Ratio 60–80%:
#   Acceptable but requires pricing discipline.

# - Loss Ratio 80–100%:
#   Marginal; requires loading, deductible adjustment, or referral.

# - Loss Ratio > 100%:
#   Underperforming account; strong justification required.

# - High Frequency + Low Severity:
#   Operational control issue.

# - Low Frequency + High Severity:
#   Catastrophic exposure profile.

# --------------------------------------------
# AI / SQL Agent Usage Context
# --------------------------------------------

# This dataset is used by:
# - SQL Agent for benchmarking similar risks.
# - Risk Scoring Engine for normalization and weighted scoring.
# - Broker performance analysis.
# - Portfolio concentration risk assessment.
# - Underwriting appetite validation.

# All calculations must remain deterministic and auditable.
# LLM models should not calculate performance metrics unless validated against SQL outputs.

# --------------------------------------------
# Governance Note
# --------------------------------------------

# All derived fields such as loss_ratio must be recalculated
# at query time when possible to avoid data drift.

# Underwriting decisions should not rely solely on loss_ratio
# but must consider:
# - Risk type
# - Geographic exposure
# - Portfolio correlation
# - Limit adequacy
# - Broker quality

# """)

# # Question SQL Pairs

# vn.train(
#     question="What is the average loss ratio by risk type?",
#     sql="""
#     SELECT risk_type,
#            AVG(loss_ratio) AS avg_loss_ratio
#     FROM underwriting_dataset
#     GROUP BY risk_type
#     ORDER BY avg_loss_ratio DESC;
#     """
# )

# vn.train(
#     question="Show total incurred loss by country.",
#     sql="""
#     SELECT country_of_incorporation,
#            SUM(incurred_loss) AS total_incurred
#     FROM underwriting_dataset
#     GROUP BY country_of_incorporation
#     ORDER BY total_incurred DESC;
#     """
# )

# vn.train(
#     question="Show top 10 accounts by largest single loss.",
#     sql="""
#     SELECT insured_name, largest_single_loss
#     FROM underwriting_dataset
#     ORDER BY largest_single_loss DESC
#     LIMIT 10;
#     """
# )

# vn.train(
#     question="Which accounts have loss ratio above portfolio average?",
#     sql="""
#     SELECT insured_name, loss_ratio
#     FROM underwriting_dataset
#     WHERE loss_ratio > (
#         SELECT AVG(loss_ratio)
#         FROM underwriting_dataset
#     );
#     """
# )

# vn.train(
#     question="What is the average ultimate premium by class of business?",
#     sql="""
#     SELECT class_of_business,
#            AVG(ultimate_premium) AS avg_premium
#     FROM underwriting_dataset
#     GROUP BY class_of_business;
#     """
# )

# vn.train(
#     question="Show accounts with TIV above 100 million and loss ratio above 80%.",
#     sql="""
#     SELECT insured_name, tiv, loss_ratio
#     FROM underwriting_dataset
#     WHERE tiv > 100000000
#       AND loss_ratio > 80
#     ORDER BY loss_ratio DESC;
#     """
# )

# vn.train(
#     question="Which accounts have low claims frequency but high largest single loss?",
#     sql="""
#     SELECT insured_name, claims_frequency, largest_single_loss
#     FROM underwriting_dataset
#     WHERE claims_frequency <= 2
#       AND largest_single_loss > 1000000;
#     """
# )

# vn.train(
#     question="Summarize average largest loss and claims frequency by class.",
#     sql="""
#     SELECT class_of_business,
#            AVG(claims_frequency) AS avg_frequency,
#            AVG(largest_single_loss) AS avg_severity
#     FROM underwriting_dataset
#     GROUP BY class_of_business;
#     """
# )

# vn.train(
#     question="What is the premium-weighted loss ratio of the portfolio?",
#     sql="""
#     SELECT 
#       SUM(incurred_loss) / SUM(ultimate_premium) * 100 AS weighted_loss_ratio
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="Rank accounts by loss ratio within each class of business.",
#     sql="""
#     SELECT insured_name,
#            class_of_business,
#            loss_ratio,
#            RANK() OVER (
#                PARTITION BY class_of_business
#                ORDER BY loss_ratio DESC
#            ) AS rank_within_class
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="What is the 75th percentile loss ratio by class?",
#     sql="""
#     SELECT class_of_business,
#            PERCENTILE_CONT(0.75) 
#            WITHIN GROUP (ORDER BY loss_ratio) AS p75_loss_ratio
#     FROM underwriting_dataset
#     GROUP BY class_of_business;
#     """
# )

# vn.train(
#     question="Calculate 3-month moving average of premium.",
#     sql="""
#     SELECT submission_date,
#            AVG(ultimate_premium) OVER (
#                ORDER BY submission_date
#                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
#            ) AS moving_avg_premium
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="Which risks have loss ratio greater than 100% and incurred loss above 1 million?",
#     sql="""
#     SELECT insured_name, loss_ratio, incurred_loss
#     FROM underwriting_dataset
#     WHERE loss_ratio > 100
#       AND incurred_loss > 1000000;
#     """
# )

# vn.train(
#     question="What is the average loss ratio by broker?",
#     sql="""
#     SELECT broker_contact,
#            AVG(loss_ratio) AS avg_loss_ratio
#     FROM underwriting_dataset
#     GROUP BY broker_contact
#     ORDER BY avg_loss_ratio DESC;
#     """
# )

# vn.train(
#     question="Which broker generated the highest total premium?",
#     sql="""
#     SELECT broker_contact,
#            SUM(ultimate_premium) AS total_premium
#     FROM underwriting_dataset
#     GROUP BY broker_contact
#     ORDER BY total_premium DESC
#     LIMIT 1;
#     """
# )

# vn.train(
#     question="Classify risks into Low, Medium and High risk based on loss ratio.",
#     sql="""
#     SELECT insured_name,
#            CASE
#                WHEN loss_ratio <= 50 THEN 'Low'
#                WHEN loss_ratio <= 80 THEN 'Medium'
#                ELSE 'High'
#            END AS risk_band
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="How many risks fall into each loss ratio band?",
#     sql="""
#     SELECT risk_band, COUNT(*)
#     FROM (
#         SELECT CASE
#                  WHEN loss_ratio <= 50 THEN 'Low'
#                  WHEN loss_ratio <= 80 THEN 'Medium'
#                  ELSE 'High'
#                END AS risk_band
#         FROM underwriting_dataset
#     ) sub
#     GROUP BY risk_band;
#     """
# )

# vn.train(
#     question="Show accounts performing worse than their class average.",
#     sql="""
#     SELECT u1.insured_name,
#            u1.class_of_business,
#            u1.loss_ratio
#     FROM underwriting_dataset u1
#     WHERE u1.loss_ratio >
#           (SELECT AVG(u2.loss_ratio)
#            FROM underwriting_dataset u2
#            WHERE u2.class_of_business = u1.class_of_business);
#     """
# )

# vn.train(
#     question="Which accounts contribute to top 10% of premium volume?",
#     sql="""
#     SELECT insured_name, ultimate_premium
#     FROM underwriting_dataset
#     WHERE ultimate_premium >= (
#         SELECT PERCENTILE_CONT(0.90)
#         WITHIN GROUP (ORDER BY ultimate_premium)
#         FROM underwriting_dataset
#     );
#     """
# )

# vn.train(
#     question="What is the premium to TIV ratio for each account?",
#     sql="""
#     SELECT insured_name,
#            ultimate_premium / NULLIF(tiv,0) AS premium_to_tiv_ratio
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="Give overall portfolio summary statistics.",
#     sql="""
#     SELECT COUNT(*) AS total_accounts,
#            SUM(ultimate_premium) AS total_premium,
#            SUM(incurred_loss) AS total_incurred,
#            SUM(incurred_loss)/SUM(ultimate_premium)*100 AS portfolio_loss_ratio
#     FROM underwriting_dataset;
#     """
# )

# vn.train(
#     question="Which countries have the highest average loss ratio?",
#     sql="""
#     SELECT country_of_incorporation,
#            AVG(loss_ratio) AS avg_lr
#     FROM underwriting_dataset
#     GROUP BY country_of_incorporation
#     ORDER BY avg_lr DESC
#     LIMIT 5;
#     """
# )

# vn.train(
#     question="Show accounts with claims frequency above 4 but largest loss below 200k.",
#     sql="""
#     SELECT insured_name
#     FROM underwriting_dataset
#     WHERE claims_frequency > 4
#       AND largest_single_loss < 200000;
#     """
# )

# vn.train(
#     question="Find accounts with unusually high loss ratio.",
#     sql="""
#     SELECT insured_name, loss_ratio
#     FROM underwriting_dataset
#     WHERE loss_ratio >
#         (SELECT AVG(loss_ratio) + 2 * STDDEV(loss_ratio)
#          FROM underwriting_dataset);
#     """
# )

# vn.train(
#     question="Show monthly average loss ratio trend.",
#     sql="""
#     SELECT DATE_TRUNC('month', submission_date) AS month,
#            AVG(loss_ratio) AS avg_loss_ratio
#     FROM underwriting_dataset
#     GROUP BY month
#     ORDER BY month;
#     """
# )

# vn.train(
#     question="Which accounts are in the worst 5 percent by loss ratio?",
#     sql="""
#     SELECT insured_name, loss_ratio
#     FROM underwriting_dataset
#     WHERE loss_ratio >= (
#         SELECT PERCENTILE_CONT(0.95)
#         WITHIN GROUP (ORDER BY loss_ratio)
#         FROM underwriting_dataset
#     );
#     """
# )

# vn.train(
#     question="What percentage of premium comes from top 5 accounts?",
#     sql="""
#     SELECT SUM(ultimate_premium) /
#            (SELECT SUM(ultimate_premium) FROM underwriting_dataset) * 100
#     FROM (
#         SELECT ultimate_premium
#         FROM underwriting_dataset
#         ORDER BY ultimate_premium DESC
#         LIMIT 5
#     ) top_accounts;
#     """
# )

# vn.train(
#     question="Show frequency and loss ratio side by side.",
#     sql="""
#     SELECT claims_frequency,
#            AVG(loss_ratio) AS avg_lr
#     FROM underwriting_dataset
#     GROUP BY claims_frequency
#     ORDER BY claims_frequency;
#     """
# )

# vn.train(
#     question="Find risks with increasing premium but worsening loss ratio.",
#     sql="""
#     SELECT insured_name, ultimate_premium, loss_ratio
#     FROM underwriting_dataset
#     WHERE ultimate_premium > (
#         SELECT AVG(ultimate_premium)
#         FROM underwriting_dataset
#     )
#     AND loss_ratio > 80;
#     """
# )

# vn.train(
#     question="Show casualty accounts in UK with loss ratio above 70% and TIV above 50 million.",
#     sql="""
#     SELECT insured_name, loss_ratio, tiv
#     FROM underwriting_dataset
#     WHERE class_of_business = 'Casualty'
#       AND country_of_incorporation = 'United Kingdom'
#       AND loss_ratio > 70
#       AND tiv > 50000000;
#     """
# )


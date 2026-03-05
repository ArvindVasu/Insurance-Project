from services.Common_Functions import get_schema_description,load_qs_pairs,prune_state
from config.global_variables import DB_PATH

from services.Graph_state import GraphState
from services.llm_service import call_llm



import streamlit as st
from langchain_core.runnables import Runnable
from serpapi import GoogleSearch



from dotenv import load_dotenv
import json
import re


load_dotenv()

QSPairs = load_qs_pairs()
qs_examples = "\n".join(
    f"Q: {pair['question']}\nSQL: {pair['sql']}" for pair in QSPairs[:7]  # Limit to 7 to avoid token overflow
)


documentation = """
You are provided with the metadata summary of the ASTRA Underwriter PnC dataset.
Use this information to understand column semantics when analyzing user queries.

Column Definitions

1. insured_name - Unique insured entity; used for entity-specific queries.

2. insured_address - Business location; used for geography or jurisdiction-based queries.

3. country_of_incorporation - Possible values: United States, Germany, Netherlands, France, United Kingdom, Singapore.
Used for regulatory or jurisdictional analysis.

4. business_description - Possible values: Food Processing, Oil & Gas Services, Construction Contractor, Electronics Manufacturing, Manufacturing, Retail & Distribution, Marine Shipping, Financial Advisory.
Used for sector-based analysis.

5. risk_type - Possible values: Marine Hull, Products Liability, General Liability, Industrial All Risks, Energy Offshore, Professional Indemnity.
Used for coverage and risk categorization.

6. broker_contact - Possible values: BMS Group, Gallagher London, Howden UK, Aon UK Ltd, Lockton Companies, WTW London, Marsh Ltd.
Used for broker-level analysis.

7. class_of_business - Possible values: Marine, Casualty, Products Liability, Property Damage & BI, Energy, Financial Lines.
Used for portfolio segmentation.

8. submission_date - Underwriting submission timeline; used for trend and pipeline analysis.

9. claims_frequency - Discrete numeric values (0-6); used for frequency modelling.

9. largest_single_loss - High-severity loss indicator.

10. incurred_loss - Aggregate incurred loss metric.

11. ultimate_premium - Final written premium; revenue metric.

12. loss_ratio - Profitability indicator (ratio of loss to premium).

13. total_insured_value (TIV) - Exposure metric representing insured value.
"""

STATE_KEYS_SET_AT_ENTRY = []


# ---- Router Node (with prompt generation) ----
class RouterNode(Runnable):
    def invoke(self, state: GraphState, config=None) -> GraphState:
        #doc_flag = "yes" if state['doc_loaded'] else "no"
        # excel_flag1 = "yes" if state.get("uploaded_file1_is_excel") else "no"
        # docx_flag1 = "yes" if state.get("uploaded_file1_is_docx") else "no"
        # doc1_exist = "yes" if state.get("uploaded_file1_path") else "no"

        schema = get_schema_description(DB_PATH)

        router_prompt = f"""
    You are an intelligent routing agent. Your job is to:
    1. Choose one of the paths: "sql", "search", "comp", "faissdb","intranet" based on the user prompt.

    2. Choose:
    - "sql" if the user is asking a question about structured insurance data (e.g. submissions, premiums, loss ratio, incurred loss, claims frequency, largest single loss, total insured value (TIV), broker performance, risk type, class of business, portfolio trends) or something that can be answered from the following database schema:
        {schema}
    - Use this additional documentation to better understand column meanings:
        {documentation}
    - Additionally, here are some examples of SQL-style questions and their corresponding queries (QSPairs):
        {qs_examples}
    - Make sure no document is attached
    -EVEN IF the user also says things like "plot", "draw", "visualize", "graph", "bar chart", etc. — that still means they want structured data **along with** a chart. SO route it to SQL
    -Route it to "sql" if queries includes the below mentioned:
        - Asks for trends, breakdowns, or aggregations of internal metrics (e.g., incurred loss, loss ratio, claims frequency, largest single loss, exposure (TIV), premiums, ultimate premium)
        - Ask for trends **within internal data only**
        - Compares **internal data over time or segments** (e.g., years, lines of business, regions)
        - Ask for charts or visualizations ("plot", "bar chart", etc.)
        - Does NOT involve external benchmarking
        Even if the prompt includes words like "compare" or "change", still route to SQL if the context is strictly internal.
    -If the route is "sql", include vanna_prompt, but don't include fuzzy_prompt
        -(eg: User Prompt is "Show me exposure year wise incurred loss and plot a graph", then 
        -vanna_prompt will be "Show me exposure year wise incurred loss".
        -Your work is to remove the noise and focus only on things that are required to generate sql query from vanna. SO remove all the extra stuffs out of the user prompt.

    3. Choose "search" if:
        - The user is asking about general or external information
        - Involves real-time info, news, global economic trends, regulations
        - The query cannot be answered by internal structured data or uploaded document
    - If the route is "search", DO NOT include vanna_prompt or fuzzy_prompt.

    4. Choose "comp" when the user is comparing internal data against external data, competitors, or industry benchmarks. But no file should be attached.
        Examples include peer review, benchmarking, market positioning, or competitive ratios.

        Trigger words/phrases:
        - "as compared to"
        - "industry benchmark"
        - "market average"
        - "how do we compare to..."
        - "peer comparison"
        - "market trend vs ours"
        - "against competitors"
        - "vs industry"
        - "benchmarking analysis"
        - "loss ratio gap with peers"
        - "pricing differential with market"
        - "expense ratio compared to competition"
        - "where do we stand in market"
        - "relative to industry"
        - "competitive advantage in reserves"
        - "our severity vs others"
        - "compare to S&P average" / "AM Best stats" / "regulatory benchmark"

    -Do not include fuzzy_prompt
    -Only include relevant columns in vanna_prompt. Do not include ClaimNumber or ID columns unless the user specifically asks for them.

    5. Choose "faissdb" when:
        - The prompt asks about the Sparta platform, Earmark Template, Branch Adjustment Template/Module, Projects in Sparta, or any internal process or documentation.
        - The user seems to be referring to internal workflows, operating processes, or knowledge base content.
        - Example prompts:
            - "What are the steps in the Branch Adjustment Module?"
            - "Explain how Earmark Template is used in our process."
            - "Can you summarize Projects in Sparta?"

    6. Choose "intranet" when:
        - The user asks about policy documents, rules and guidelines, R&G, underwriting guidelines, claims guidelines, coverage terms, policy wording, exclusions, endorsements, EOI (Expression of Interest), broker submissions, or any insurance policy framework stored on Google Drive.
        - The user uses terms like:
            - "guidelines"
            - "underwriting guidelines"
            - "claims framework"
            - "policy framework"
            - "coverage terms"
            - "policy exclusions"
            - "endorsement wording"
            - "submission requirements"
            - "risk selection criteria"
            - "policy conditions"
            - "standard operating procedure for claims"
            - "internal policy document"
        - The question is asking about qualitative policy content, not structured database metrics.
        - The answer is expected to come from internal documents rather than SQL data.

        Examples:
            - "What are the underwriting guidelines for Marine?"
            - "Show me policy exclusions under Construction CAR."
            - "What deductible applies under Aero guidelines?"
            - "Summarize the claims handling framework."
            - "Find policy documents for XYZ company."
            - "What are the coverage terms in the EOI?"

        If route is "intranet":
            - DO NOT include vanna_prompt
            - DO NOT include fuzzy_prompt

            
        Return output strictly in valid JSON format using double quotes and commas properly.
        DO NOT include any trailing commas. Your JSON must be parseable by Python's json.loads().

        Examples:

        For SQL:
        {{
            "route": "sql",
            "vanna_prompt": "Show IBNR trends for exposure year 2025"
        }}

        For Document:
        {{
            "route": "document",
        }}

        For Comp:
        {{
             "route": "comp",
             "vanna_prompt": "Show IBNR trends for exposure year 2025"
        }}

        For Search:
        {{
            "route": "search"
        }}

        For faissdb: 
        {{
            "route": "faissdb"
        }}

        For Intranet: 
        {{
            "route": "intranet"
        }}
        

        User Prompt: "{state['user_prompt']}"
        """
        #Document Uploaded: {doc_flag}
        
        try:
            response = call_llm(router_prompt)
            #st.write("Route:", response)

            match = re.search(r'{.*}', response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                chart_info = parsed.get("chart_info")
            else:
                st.warning("LLM did not return valid JSON. Routing to 'search' as fallback.")
                parsed = {"route": "search"}

        except Exception as e:
            st.error(f"[RouterNode] LLM call failed: {e}")
            parsed = {"route": "search"}

        # ✅ Enforce safety: remove vanna_prompt
        if parsed.get("route") == "document":
            parsed["fuzzy_prompt"] = state["user_prompt"]   # alias
            parsed["vanna_prompt"] = None                   # will be set later
        elif parsed.get("route") not in ["sql", "comp", "faissdb"]:
            parsed["vanna_prompt"] = None
            parsed["fuzzy_prompt"] = None

        # Ensure chart_info is only kept for SQL route
        if parsed.get("route") != "sql":
            chart_info = None

        # st.write("route: ")
        # st.write(parsed.get("route"))
        
        return {
            **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
            "route": parsed.get("route"),
            "vanna_prompt": parsed.get("vanna_prompt"),
            "fuzzy_prompt": parsed.get("fuzzy_prompt"),
            "chart_info": chart_info,
        }
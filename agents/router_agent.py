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
PnC_Data Table:
- Reserve Class contains insurance business lines such as 'Property', 'Casualty', 'Marine', 'Motor', etc.
- Exposure Year refers to the year in which the insured risk was exposed to potential loss.
- RI Type identifies whether the record is 'Gross' or one of the reinsurance types such as 'Ceded - XOL', 'Ceded - QS', 'Ceded - CAP', 'Ceded - FAC', or 'Ceded - Others'.
- Branch indicates the geographical business unit handling the contract, e.g., 'Europe', 'LATAM', 'North America'.
- Loss Type captures the nature of the loss, and may be one of: 'ATT', 'CAT', 'LARGE', 'THREAT', or 'Disc'.
- Underwriting Year represents the year in which the policy was underwritten or originated.
- Incurred Loss represents the total loss incurred to date, including paid and case reserves.
- Paid Loss is the portion of the Incurred Loss that has already been settled and paid out.
- IBNR is calculated as the difference between Ultimate Loss and Incurred Loss.
- Ultimate Loss is the projected final value of loss.
- Ultimate Premium refers to the projected premium expected to be earned.
- Loss Ratio is calculated as Ultimate Loss divided by Ultimate Premium.
- AvE Incurred = Expected - Actual Incurred.
- AvE Paid = Expected - Actual Paid.
- Budget Premium is the forecasted premium for budgeting.
- Budget Loss is the projected loss for budgeting.
- Earned Premium is the portion of the premium that has been earned.
- Case Reserves = Incurred Loss - Paid Loss.
"""

STATE_KEYS_SET_AT_ENTRY = []


# ---- Router Node (with prompt generation) ----
class RouterNode(Runnable):
    def invoke(self, state: GraphState, config=None) -> GraphState:
        #doc_flag = "yes" if state['doc_loaded'] else "no"
        excel_flag1 = "yes" if state.get("uploaded_file1_is_excel") else "no"
        docx_flag1 = "yes" if state.get("uploaded_file1_is_docx") else "no"
        doc1_exist = "yes" if state.get("uploaded_file1_path") else "no"

        schema = get_schema_description(DB_PATH)

        router_prompt = f"""
    You are an intelligent routing agent. Your job is to:
    1. Choose one of the paths: "sql", "search", "comp", "faissdb", "document","intranet" based on the user prompt.

    2. Choose "document" if user has attached a document. User is asking to summarize or analyse it. Also, trying to fetch internal SQL data and external web insights.  
    -ONLY one document should be uploaded in uploader2 and docx_flag2 should be yes.
    -If the route is "multiA", DO NOT include vanna_prompt or fuzzy_prompt.
    -Status for docx_flag1 = {docx_flag1}

    3. Choose:
    - "sql" if the user is asking a question about structured insurance data (e.g. claims, premiums, reserves, IBNR, trends, comparisons across years or products) or something that can be answered from the following database schema:
        {schema}
    - Use this additional documentation to better understand column meanings:
        {documentation}
    - Additionally, here are some examples of SQL-style questions and their corresponding queries (QSPairs):
        {qs_examples}
    - Make sure no document is attached
    -EVEN IF the user also says things like "plot", "draw", "visualize", "graph", "bar chart", etc. — that still means they want structured data **along with** a chart. SO route it to SQL
    -Route it to "sql" if queries includes the below mentioned:
        - Asks for trends, breakdowns, or aggregations of internal metrics (e.g., IBNR, reserves, severity, premiums, earned/ultimate loss)
        - Ask for trends **within internal data only**
        - Compares **internal data over time or segments** (e.g., years, lines of business, regions)
        - Ask for charts or visualizations ("plot", "bar chart", etc.)
        - Does NOT involve external benchmarking
        Even if the prompt includes words like "compare" or "change", still route to SQL if the context is strictly internal.
    -If the route is "sql", include vanna_prompt, but don't include fuzzy_prompt
        -(eg: User Prompt is "Show me exposure year wise incurred loss and plot a graph", then 
        -vanna_prompt will be "Show me exposure year wise incurred loss".
        -Your work is to remove the noise and focus only on things that are required to generate sql query from vanna. SO remove all the extra stuffs out of the user prompt.

    4. Choose "search" if:
        - The user is asking about general or external information
        - Involves real-time info, news, global economic trends, regulations
        - The query cannot be answered by internal structured data or uploaded document
    - If the route is "search", DO NOT include vanna_prompt or fuzzy_prompt.

    5. Choose "comp" when the user is comparing internal data against external data, competitors, or industry benchmarks. But no file should be attached.
        Examples include peer review, benchmarking, market positioning, or competitive ratios.

        Trigger words/phrases:
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

    6. Choose "faissdb" when:
        - The prompt asks about the Sparta platform, Earmark Template, Branch Adjustment Template/Module, Projects in Sparta, or any internal process or documentation.
        - The user seems to be referring to internal workflows, operating processes, or knowledge base content.
        - Example prompts:
            - "What are the steps in the Branch Adjustment Module?"
            - "Explain how Earmark Template is used in our process."
            - "Can you summarize Projects in Sparta?"

    7. Choose "intranet" when:
        - The user asks about policy documents, underwriting guidelines, claims guidelines, coverage terms, policy wording, exclusions, endorsements, EOI (Expression of Interest), broker submissions, or any insurance policy framework stored on Google Drive.
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
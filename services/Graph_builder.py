from agents.comp_agent import comp_node
from agents.document_agent import document_node
from agents.faiss_agent import faissdb_node
from agents.router_agent import RouterNode
from agents.serp_agent import serp_node
from agents.vanna_agent import vanna_node
from agents.intranet_agent import intranet_node

from services.Graph_state import GraphState

from langgraph.graph import StateGraph, END

from dotenv import load_dotenv


load_dotenv()

def router_logic(state: GraphState):
    if state['route'] == 'sql': return "vanna_sql"
    elif state['route'] == 'search': return "serp_search"
    elif state['route'] == 'document': return "doc_update"
    elif state['route'] == 'comp': return "comp"
    elif state['route'] == 'faissdb': return "faissdb"
    elif state['route'] == 'intranet': return "intranet"
    else: return END   

def build_graph():
    graph_builder = StateGraph(GraphState)
    graph_builder.add_node("router", RouterNode())
    graph_builder.add_node("vanna_sql", vanna_node)
    graph_builder.add_node("serp_search", serp_node)
    graph_builder.add_node("doc_update", document_node)
    graph_builder.add_node("comp", comp_node)
    graph_builder.add_node("faissdb", faissdb_node)
    graph_builder.add_node("intranet", intranet_node)

 
    graph_builder.set_entry_point("router")

    # ✅ Execution routing
    graph_builder.add_conditional_edges("router", router_logic)

    # Regular path to end
    graph_builder.add_edge("vanna_sql", END)
    graph_builder.add_edge("serp_search", END)
    graph_builder.add_edge("doc_update", END)
    graph_builder.add_edge("comp", END)
    graph_builder.add_edge("faissdb", END)
    graph_builder.add_edge("intranet", END)
   



    return graph_builder.compile()
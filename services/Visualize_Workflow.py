import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx


def visualize_workflow(builder, active_route=None):

    route_to_node = {
        "sql": "vanna_sql",
        "search": "serp_search",
        "faissdb": "faissdb",
        "comp": "comp",
        "intranet": "intranet"
    }

    highlight_node = route_to_node.get(active_route)

    G = nx.DiGraph()
    edge_styles = {}
    hidden_nodes = {"doc_update"}
    terminal_nodes = ["vanna_sql", "serp_search", "comp", "faissdb", "intranet"]

    # Add all nodes
    for node in builder.nodes:
        if node in hidden_nodes:
            continue
        G.add_node(node)
    G.add_node("__start__")
    G.add_node("__end__")

    # Base workflow edges
    if "router" in G.nodes:
        G.add_edge("__start__", "router")
        edge_styles[("__start__", "router")] = {"style": "solid", "color": "black", "width": 1.8}

    for source in terminal_nodes:
        if source in G.nodes:
            G.add_edge(source, "__end__")
            edge_styles[(source, "__end__")] = {"style": "solid", "color": "black", "width": 1.5}

    # Always show dashed edges from router to all 3 branches
    for target in terminal_nodes:
        if target not in G.nodes:
            continue
        if ("router", target) not in G.edges:
            G.add_edge("router", target)
        edge_styles[("router", target)] = {"style": "dashed", "color": "gray", "width": 1}

    # Highlight the active route in red
    if highlight_node:
        edge_styles[("router", highlight_node)] = {"style": "solid", "color": "red", "width": 2.5}

    # Positions for nodes with equal horizontal spacing across the terminal row.
    pos = {
        "__start__": (0.0, 4.0),
        "router": (0.0, 3.0),
        "__end__": (0.0, 1.0),
    }
    present_terminals = [n for n in terminal_nodes if n in G.nodes]
    if present_terminals:
        midpoint = (len(present_terminals) - 1) / 2
        for idx, node in enumerate(present_terminals):
            pos[node] = (idx - midpoint, 2.0)

    # Requested palette
    color_start_end = "#DCEEFF"   # light blue
    color_router = "#0077B6"      # ocean blue
    color_agent = "#93C572"       # pistachio
    color_active = "#FEF3C7"      # chosen agent fill (orange theme)

    def node_color(node: str) -> str:
        if node in {"__start__", "__end__"}:
            return color_start_end
        if node == "router":
            return color_router
        if node == highlight_node:
            return color_active
        return color_agent

    node_colors = [node_color(n) for n in G.nodes]

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.set_facecolor("#F8FBFF")
    fig.patch.set_facecolor("#F8FBFF")

    nx.draw_networkx_nodes(
        G,
        pos,
        node_size=2600,
        node_color=node_colors,
        edgecolors="#2D4F74",
        linewidths=1.1,
        ax=ax,
    )
    nx.draw_networkx_labels(
        G,
        pos,
        font_size=10,
        font_weight="bold",
        font_color="#15365C",
        ax=ax,
    )

    # Add orange border ring for the chosen agent for stronger emphasis.
    if highlight_node and highlight_node in G.nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=[highlight_node],
            node_size=2650,
            node_color=[color_active],
            edgecolors="#F59E0B",
            linewidths=2.6,
            ax=ax,
        )

    # Draw styled edges
    for edge in G.edges:
        style = edge_styles.get(edge, {"style": "solid", "color": "black", "width": 1})
        edge_color = style["color"]
        edge_width = style["width"]
        if edge[0] == "router" and edge[1] == highlight_node:
            edge_color = "#0B3C6F"  # selected edge in dark blue
            edge_width = 3.2
        elif edge[0] == "router":
            edge_color = "#5A8EC5"
            edge_width = 1.6
        elif edge[1] == "__end__":
            edge_color = "#3E6A99"
            edge_width = 1.6
        elif edge == ("__start__", "router"):
            edge_color = "#1F4E85"
            edge_width = 2.0
        nx.draw_networkx_edges(
            G, pos,
            edgelist=[edge],
            arrows=True,
            arrowstyle='-|>',
            style=style["style"],
            edge_color=edge_color,
            width=edge_width,
            connectionstyle="arc3,rad=0.0",
            min_source_margin=14,
            min_target_margin=14,
            ax=ax,
        )

    subtitle = f"Active route: {active_route}" if active_route else "Active route: pending"
    ax.set_title("Agentic LangGraph Workflow", fontsize=12, fontweight="bold", color="#0F2D52", pad=10)
    ax.text(
        0.5,
        1.01,
        subtitle,
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.8,
        color="#2E5D8F",
    )
    ax.axis("off")
    fig.tight_layout()
    st.pyplot(fig)

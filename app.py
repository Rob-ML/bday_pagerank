import matplotlib

# Use the Agg backend for non-interactive environments
matplotlib.use("Agg")

from flask import Flask, render_template, request, jsonify
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64

import pygraphviz as pgv
from networkx.drawing.nx_agraph import graphviz_layout


app = Flask(__name__)

teams = []
winner = None
graph = nx.DiGraph()
games_played = {}


@app.route("/")
def index():
    return render_template("index.html", teams=teams)


@app.route("/add_team", methods=["POST"])
def add_team():
    global teams, graph
    team_name = request.form["team_name"]
    if team_name not in teams:
        teams.append(team_name)
        graph.add_node(team_name)
        games_played[team_name] = 0

        # Add edges from every player from and to every player with weight 1
        for other_team in teams:
            if other_team != team_name:
                graph.add_edge(team_name, other_team, weight=1)
                graph.add_edge(other_team, team_name, weight=1)

    return render_template("index.html", teams=teams)


@app.route("/play_game", methods=["POST"])
def play_game():
    global winner
    participating_teams = request.form.getlist("participating_teams")
    winner = request.form["winner"]

    # Check if the winner is a participating team
    if winner not in participating_teams:
        return render_template(
            "index.html", teams=teams, error="Winner must be a participating team."
        )

    # Increment games played for participating teams
    for team in participating_teams:
        games_played[team] += 1

    # Add directed edges with weights only for losing teams to the winner
    for team in participating_teams:
        if team != winner:
            if graph.has_edge(team, winner):
                graph[team][winner]["weight"] += 1
            else:
                graph.add_edge(team, winner, weight=1)

    print(graph.edges(data=True))

    # Calculate PageRank
    pagerank = nx.pagerank(graph)

    # Calculate games played as a percentage of the total games played
    total_games = sum(games_played.values())
    games_played_percentage = {
        team: (games_played[team] / total_games) * 100 for team in teams
    }

    # Calculate final score (pagerank * games played)
    final_scores = {
        team: (pagerank[team] * (2 / 3)) + (games_played_percentage[team] * (1 / 300))
        for team in teams
    }

    # Sort teams by final scores
    sorted_teams = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    # Create the final ranking with games played, pagerank score, final score, and percentage
    ranking = [
        {
            "rank": rank + 1,
            "team": team,
            "final_score": round(final_scores[team] * 100),
            "pagerank": round(pagerank[team] * 100),
            "games_played": games_played[team],
            "games_played_percentage": games_played_percentage[team],
        }
        for rank, (team, _) in enumerate(sorted_teams)
    ]

    return render_template("index.html", teams=teams, ranking=ranking, winner=winner)


import pygraphviz as pgv
from networkx.drawing.nx_agraph import graphviz_layout


@app.route("/visualization")
def visualization():
    # Generate a graph visualization using NetworkX and Matplotlib
    pos = nx.spring_layout(graph)

    # Create a new AGraph
    A = pgv.AGraph(directed=True)

    # Add edges to the AGraph with weights as labels
    for u, v, data in graph.edges(data=True):
        A.add_edge(u, v, label=data["weight"])

    # Use graphviz to find the layout positions
    pos = graphviz_layout(graph, prog="dot")

    # Draw the nodes
    nx.draw_networkx_nodes(graph, pos, node_color="skyblue", node_size=800)
    nx.draw_networkx_labels(graph, pos, font_weight="bold")

    # Draw the edges using the positions from graphviz
    for edge in A.edges():
        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=[(edge[0], edge[1])],
            edge_color="gray",
            arrows=True,
            arrowstyle="-|>",
            arrowsize=20,
        )

    # Draw the edge labels
    edge_labels = nx.get_edge_attributes(graph, "weight")
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_color="red")

    # Calculate the total weight of incoming and outgoing edges for each node
    in_out_weights = {
        node: (
            sum(data["weight"] for _, _, data in graph.in_edges(node, data=True)),
            sum(data["weight"] for _, _, data in graph.out_edges(node, data=True)),
        )
        for node in graph.nodes()
    }

    img = BytesIO()
    plt.savefig(img, format="png", bbox_inches="tight")
    plt.close()

    # Encode the image in base64 to embed in HTML
    img.seek(0)
    graph_image = base64.b64encode(img.getvalue()).decode()

    return render_template(
        "visualization.html", graph_image=graph_image, in_out_counts=in_out_weights
    )


if __name__ == "__main__":
    app.run(debug=True)

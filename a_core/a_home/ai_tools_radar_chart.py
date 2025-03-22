from django.shortcuts import render
from .models import AiToolEvaluation
import plotly.graph_objects as go


def create_ai_tools_radar_chart():
    # Récupérer toutes les évaluations depuis la base de données
    evaluations = AiToolEvaluation.objects.all()

    # Définir les catégories correspondant aux axes du Radar Chart
    categories = [
        'Code Personalization',
        'GitHub Integration',
        'Context Understanding',
        'Suggestion Accuracy',
        'Development Speed',
        'Effort Explanation',
        'User Experience'
    ]

    fig = go.Figure()

    # Ajouter une trace pour chaque outil
    for evaluation in evaluations:
        # Créer une liste des scores pour chaque axe
        scores = [
            evaluation.code_personalization,
            evaluation.github_integration,
            evaluation.context_understanding,
            evaluation.suggestion_accuracy,
            evaluation.development_speed,
            evaluation.effort_explanation,
            evaluation.user_experience
        ]
        # Pour fermer le polygone, on répète le premier score et la première catégorie
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=evaluation.ai_tool
        ))

    # Mise à jour du layout du graphique
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=False,
                range=[0, 10]  # Ajustez la plage en fonction de vos scores
            ),
            angularaxis=dict(
                tickfont=dict(color="white", family="DynaPuff")
            )
        ),

        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(
            family="DynaPuff",  # Police moderne pour l'ensemble du graphique
            size=18,  # Taille du texte
            color="white"
        ),
        height=600  # Hauteur de la figure
    )

    # Convertir le graphique en HTML pour l'inclure dans le template
    chart_html = fig.to_html(full_html=False, config={'displayModeBar': False})

    return chart_html

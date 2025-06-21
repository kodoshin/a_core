
import re
import textwrap  # pour enlever proprement l’indentation éventuelle


def clean_mermaid_code(code):
    code = code.replace('mermaid\n', '')
    code = code.replace(')', '')
    code = code.replace('(', '')
    code = code.replace(';', ' ')
    return code


def parse_steps(message_content: str):
    """
    Transforme un flux XML composé d’un ou plusieurs blocs <insight[…]>…</insight[…]>
    en une liste de dictionnaires Python.

    Chaque dictionnaire contient :
        - number  : int | None   (numéro lorsque le tag est <insight1>, <insight2>, …)
        - diagram         : {"language": "mermaid", "content": str} | None
        - file            : str
        - component       : str
        - summary         : str
    """
    insights = []

    # Autorise à la fois <insight>…</insight> et <insight1>…</insight1>
    for match in re.finditer(r'<insight(\d*)>(.*?)</insight\1>', message_content, re.DOTALL):
        block_num  = match.group(1)           # chaîne vide si pas de numéro
        block_xml  = match.group(2)

        insight = {
            "number": int(block_num) if block_num else None,
            "diagram": None,
            "file": "",
            "component": "",
            "summary": "",
        }

        # -------- Diagram (toujours mermaid) --------
        diagram_match = re.search(r'<diagram>(.*?)</diagram>', block_xml, re.DOTALL)
        if diagram_match:
            raw_diagram = diagram_match.group(1)
            # Enlève l’indentation commune et les espaces superflus
            diagram_content = textwrap.dedent(raw_diagram).strip()
            insight["diagram"] = {
                "language": "mermaid",        # fixé par ton nouveau format
                "content": clean_mermaid_code(diagram_content),
            }

        # -------- File --------
        file_match = re.search(r'<file>(.*?)</file>', block_xml, re.DOTALL)
        if file_match:
            insight["file"] = file_match.group(1).strip()

        # -------- Component --------
        component_match = re.search(r'<component>(.*?)</component>', block_xml, re.DOTALL)
        if component_match:
            insight["component"] = component_match.group(1).strip()

        # -------- Summary --------
        summary_match = re.search(r'<summary>(.*?)</summary>', block_xml, re.DOTALL)
        if summary_match:
            # `strip()` enlève les sauts de ligne et espaces en trop en début/fin
            insight["summary"] = summary_match.group(1).strip()

        insights.append(insight)

    return insights

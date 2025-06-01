import re
import textwrap


def parse_steps(message_content):
    steps = []
    # Use re.finditer to find all steps with matching numbers
    for match in re.finditer(r'<step(\d+)>(.*?)</step\1>', message_content, re.DOTALL):
        step = {}
        step_number = int(match.group(1))
        step['step_number'] = step_number
        step_content = match.group(2)

        # Extract Justifications
        justification_match = re.search(r'<Justifications>(.*?)</Justifications>', step_content, re.DOTALL)
        if justification_match:
            step['justification'] = justification_match.group(1).strip()
        else:
            step['justification'] = ''

        # Extract app
        app_match = re.search(r'<app>(.*?)</app>', step_content, re.DOTALL)
        if app_match:
            step['app'] = app_match.group(1).strip()
        else:
            step['app'] = ''

        # Extract file
        file_match = re.search(r'<file>(.*?)</file>', step_content, re.DOTALL)
        if file_match:
            step['file'] = file_match.group(1).strip()
        else:
            step['file'] = ''

        # Extract code
        code_content = None
        code_match = re.search(r'<code>\s*<(.*?)>(.*?)</\1>\s*</code>', step_content, re.DOTALL)
        if code_match:
            code_language = code_match.group(1)
            code_content = code_match.group(2)
            # Suppression de l'indentation excessive
            #code_content = re.sub(r'^\s{4}|\t', '', code_content, flags=re.MULTILINE)
            lines = code_content.splitlines()
            indent_levels = [len(re.match(r'^\s*', line).group(0)) for line in lines if line.strip()]
            min_indent = min(indent_levels) if indent_levels else 0

            # Supprimer l'indentation minimale de toutes les lignes
            adjusted_lines = [line[min_indent:] for line in lines]

            if adjusted_lines and adjusted_lines[0].strip() == "":
                adjusted_lines = adjusted_lines[1:]

            adjusted_code_content = "\n".join(adjusted_lines)
            step['code'] = {
                'language': code_language,
                'content': adjusted_code_content
            }

        elif code_content == None :
            try :
                code_match = re.search(r'<code>(.*?)</code>', step_content, re.DOTALL)
                code_language = 'text'
                code_content = code_match.group(1)
                lines = code_content.splitlines()
                indent_levels = [len(re.match(r'^\s*', line).group(0)) for line in lines if line.strip()]
                min_indent = min(indent_levels) if indent_levels else 0

                # Supprimer l'indentation minimale de toutes les lignes
                adjusted_lines = [line[min_indent:] for line in lines]

                if adjusted_lines and adjusted_lines[0].strip() == "":
                    adjusted_lines = adjusted_lines[1:]

                adjusted_code_content = "\n".join(adjusted_lines)
                step['code'] = {
                    'language': code_language,
                    'content': adjusted_code_content
                }
            except:
                step['code'] = None
        else:
            step['code'] = None

        steps.append(step)

    return steps

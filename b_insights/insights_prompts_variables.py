pe_files_xml = """
Task:

As an AI assistant, help me with the following:

Review the provided {technology} project files paths.

List all the files paths that would be useful to resolve the user's request.
Output them in this exact XML format:

<files>
  <file>File path of first relevant file</file>
  <file>File path of second relevant file</file>
  <!-- More files if needed -->
</files>

Constraints:

Do not include any additional text or explanations outside of the specified XML formats.
Do not modify the structure of the XML formats provided.
Do not include code or code snippets in your response.
Only provide the XML formatted questions or files as per the instructions.

"""

pe_components_xml = """
Task:

As an AI assistant, help me with the following:

Review the provided {technology} project components.

List all the components that would be useful to resolve the user's request.
Output them in this exact XML format:

<components>
  <component><file>File of first relevant component</file><name>Name of first relevant component</name></component>
  <component><file>File of second relevant component</file><name>Name of second relevant component</name></component>
  <!-- More component if needed -->
</components>

Constraints:

Do not include any additional text or explanations outside of the specified XML formats.
Do not modify the structure of the XML formats provided.
Do not include code or code snippets in your response.
Only provide the XML formatted questions or files as per the instructions.

"""

pe_final_answer = """
As an AI assistant, help me with the following:

Review the provided {technology} project resources and the request

Provide me a detailed solution using the resources to solve the request.

"""

pe_final_answer_format = """
Please analyze the current code and provide a structured insight response in the following format:

<insight1>
<diagram>mermaid code for diagram</diagram>
<summary> 
A General explanation symmary of the insights.
</summary>
</insight1>
<insight2>
<file>/full/path/to/file.py</file>
<component>name_of_component</component>
<summary> 
A detailed explanation of the insight.
</summary>
</insight2>
<insight3>
<file>/full/path/to/file.py</file>
<component>name_of_component</component>
<summary> 
A detailed explanation of the insight.
</summary>
</insight3>
... other insights

Instructions:

The insight1 should containt a general summary of all the other insights, and <diagram> if it makes sense.

The insight2, insight3, etc. should containt a <file> and <component> blocks with a detailed explanation of the insight.

Constraints:

Include <diagram> only when it makes sense.

Only return structured XML-style blocks as shown.

No generic summaries, everything must be tightly linked to the actual repo context.

Use <code> blocks if you suggest improvements or fixes.
Use <language> blocks to specify the used language (example: <python>, <javascript>, etc.), else use <text> block.

Do not rename functions, models, or variables unless strictly necessary.

If no issues found, still include <summary> and explicitly mention No critical issues found in <opportunities>.

Respect file paths, indentation, and original logic.

If needed, suggest monitoring areas for future technical debt or scalability risks.

Never include speculative advice not backed by the source code.

"""

none_answer = """
<step1> <Justifications> We haven't been able to process your request, please change the prompt or try again, if the error persists, please try later. </Justifications> </step1>
"""

no_components_answer = """
<step1> <Justifications> We didn't find any components that match your request, please update the prompt, if you think this is a mistake, please try again later </Justifications><file>None</file></step1>
"""
import ast
import pathlib
import logging
import sys


def extract_docstrings(filepath: pathlib.Path, output_filepath: pathlib.Path | None = None) -> dict[str: str]:
    """
    A function that returns the value of the __doc__ variables in
    standard_instructions.py for SCPUAS

    Args:
        filename (string): the name of the file to extract, this being
            standard_instructions.py
        output_filename (string): the name of the file to output the list into

    Returns:
        a list of strings which are the values of __doc__ variables

    """
    filepath = filepath.resolve()

    with open(filepath, "r", encoding="utf8") as file:
        tree = ast.parse(file.read(), filename=filepath)

    doc_strings: dict[str: str] = {}
    rtl_strings: dict[str: str] = {}
    args: dict[str: list[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        doc_string = [
            _.value.value
            for _ in node.body if isinstance(_, ast.Assign) and any(__.id == '__doc__' for __ in _.targets)
        ]
        rtl_string = [
            _.value.value
            for _ in node.body if isinstance(_, ast.Assign) and any(__.id == '__rtl__' for __ in _.targets)
        ]
        normal_args: list[str] = [
            _.id for body in node.body if isinstance(body, ast.Assign) for _ in body.targets if not (
                _.id.startswith('__') and _.id.endswith('__')
            )
        ]

        if not doc_string:
            logging.warning("No __doc__ variable found in class %s", node.name)
            doc_string = ['Unknown']

        doc_string = doc_string[0]

        if not isinstance(doc_string, str):
            logging.warning("Invalid __doc__ variable in class %s", node.name)
            continue

        if not rtl_string:
            logging.warning("No __rtl__ variable found in class %s", node.name)
            rtl_string = ['Unknown']

        rtl_string = rtl_string[0]

        if not isinstance(rtl_string, str):
            logging.warning("Invalid __rtl__ variable in class %s", node.name)
            continue

        for i in range(len(normal_args)):
            rtl_string = rtl_string.replace(f"{{{i}}}", normal_args[i])

        doc_strings[node.name[1:].replace('_', '.')] = doc_string
        rtl_strings[node.name[1:].replace('_', '.')] = rtl_string
        args[node.name[1:].replace('_', '.')] = normal_args

    if output_filepath and len(doc_strings) != 0:
        doc_strings_string = "\n".join([f"### {key}\n ```\n{value}\n```" for key, value in doc_strings.items()])
        output_filepath = output_filepath.resolve()

        table = "| Instruction | RTL |\n| --- | --- |"

        for key, value in rtl_strings.items():
            value = value.replace("|", "│").split("\n")
            table += f"\n| [{key}](#{key}) | {'<br>'.join(value)} |"



        output = f"""
# Instructions loaded from {filepath.name}
## RTL table
{table}      
## Instructions
{doc_strings_string}
"""

        with open(output_filepath, "w", encoding="utf8") as file:
            file.write(output)

        logging.info("Docstrings extracted and saved to %s", output_filepath)

    return doc_strings

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not sys.argv[1:] or len(sys.argv) != 3:
        print("Usage: python extract_doc_strings.py <file> <output>")
        raise SystemExit

    doc_strings_list = extract_docstrings(
        pathlib.Path(sys.argv[1]),
        pathlib.Path(sys.argv[2])
    )

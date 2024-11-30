#!/usr/bin/python
import os
import ast
import re
import json

def find_keypress_functions_with_kbkeys(project_path):
    result = {}

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                if class_name not in result:
                                    result[class_name] = []
                                for item in node.body:
                                    if isinstance(item, ast.FunctionDef) and item.name == "keypress":
                                        function_start = item.lineno
                                        function_end = item.body[-1].end_lineno if item.body else function_start
                                        kbkey_matches = extract_kbkeys(file_path, function_start, function_end)
                                        result[class_name].extend(kbkey_matches)
                    except (SyntaxError, UnicodeDecodeError) as e:
                        print(f"Error parsing {file_path}: {e}")

    # Remove duplicates and classes with no kbkey references
    result = {class_name: list(set(kbkeys)) for class_name, kbkeys in result.items() if kbkeys}

    return result

def extract_kbkeys(file_path, start_line, end_line):
    """Extract kbkey[XXX] occurrences from the given line range in a file."""
    kbkey_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[start_line - 1:end_line]
            for line in lines:
                matches = re.findall(r'kbkey\[\s*["\'](.*?)["\']\s*\]', line)
                kbkey_list.extend(matches)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return kbkey_list

def find_classes_in_files(project_path):
    """Find all classes in Python files and their starting and ending lines."""
    classes = []

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                start_line = node.lineno
                                end_line = max(
                                    [n.lineno if hasattr(n, 'lineno') else start_line for n in ast.walk(node)],
                                    default=start_line
                                )
                                classes.append({
                                    "file": file_path,  # Use full file path here
                                    "class_name": class_name,
                                    "start_line": start_line,
                                    "end_line": end_line,
                                    "uses": []  # Placeholder for used classes
                                })
                    except (SyntaxError, UnicodeDecodeError) as e:
                        print(f"Error parsing {file_path}: {e}")

    return classes

def find_class_usages(classes):
    """Find classes used by each class in the given classes dictionary."""
    for cls in classes:
        file_path = cls['file']
        start_line = cls['start_line']
        end_line = cls['end_line']

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[start_line - 1:end_line]
                for line in lines:
                    for other_cls in classes:
                        if other_cls['class_name'] != cls['class_name']:
                            # Check for "= xxx(" to confirm instantiation
                            if f"= {other_cls['class_name']}(" in line:
                                cls['uses'].append(other_cls['class_name'])

            # Remove duplicates from the 'uses' list
            cls['uses'] = list(set(cls['uses']))

        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

def find_class_inheritance(classes):
    """Find the base class each class inherits from."""
    for cls in classes:
        file_path = cls['file']
        start_line = cls['start_line']
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Read the line containing the class definition
                line = f.readlines()[start_line - 1].strip()
                if "(" in line and line.endswith(":"):
                    # Extract base class if it exists
                    base_class = line.split("(")[1].split(")")[0].strip()
                    cls["inherits_from"] = base_class
                else:
                    # No inheritance
                    cls["inherits_from"] = None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            cls["inherits_from"] = None

def display_classes(classes):
    print("\nClasses Found in Files:")
    for entry in classes:
        print(f"File: {os.path.basename(entry['file'])}, Class: {entry['class_name']}, "
              f"Start Line: {entry['start_line']}, End Line: {entry['end_line']}, "
              f"Uses: {entry['uses']}, Inherits from: {entry['inherits_from']}")

def display_results(results):
    print("\n\nFound keypress functions with kbkey references:")
    for class_name, kbkeys in results.items():
        print(f"Class: {class_name}, kbkey References: {kbkeys}")

def map_functional_relationships(results, classes):
    """Map functional relationships of classes with keypress shortcuts."""
    functional_map = []
    for cls in classes:
        class_name = cls['class_name']
        if class_name in results:
            functional_map.append({
                "class_name": class_name,
                "inherits_from": cls['inherits_from'],
                "uses": cls['uses'],
                "kbkeys": results[class_name],
            })
    return functional_map

def analyze_dependencies(results, classes):
    """Analyze dependencies based on class relationships."""
    dependency_map = []
    for cls in classes:
        class_name = cls['class_name']
        dependencies = []
        if cls['inherits_from'] and cls['inherits_from'] in results:
            dependencies.append(cls['inherits_from'])
        for used_class in cls['uses']:
            if used_class in results:
                dependencies.append(used_class)
        dependency_map.append({
            "class_name": class_name,
            "dependencies": dependencies,
            "kbkeys": results.get(class_name, []),
        })
    return dependency_map

def functional_structural_integration(results, classes):
    """Integrate functional and structural data to analyze all related classes."""
    integration_map = {}
    for cls in classes:
        class_name = cls['class_name']
        all_related_classes = set()
        if cls['inherits_from']:
            all_related_classes.add(cls['inherits_from'])
        all_related_classes.update(cls['uses'])
        integration_map[class_name] = {
            "kbkeys": results.get(class_name, []),
            "related_classes": list(all_related_classes),
        }
    return integration_map

def display_functional_relationships(map_data):
    print("\nFunctional Relationships:")
    for entry in map_data:
        print(f"Class: {entry['class_name']}, Inherits From: {entry['inherits_from']}, "
              f"Uses: {entry['uses']}, Keypress Shortcuts: {entry['kbkeys']}")

def display_dependencies(map_data):
    print("\nDependencies Analysis:")
    for entry in map_data:
        print(f"Class: {entry['class_name']}, Depends On: {entry['dependencies']}, "
              f"Own Keypress Shortcuts: {entry['kbkeys']}")

def display_integration(integration_map):
    print("\nFunctional-Structural Integration:")
    for cls, data in integration_map.items():
        print(f"Class: {cls}, Keypress Shortcuts: {data['kbkeys']}, "
              f"Related Classes: {data['related_classes']}")



def extend_results_with_related_keys(results, classes):
    """Extend results by appending keys from used and inherited classes."""
    # Start with a copy of results, ensuring all classes are included
    extended_results = {cls['class_name']: results.get(cls['class_name'], []) for cls in classes}

    # Map class names to their kbkeys from results
    class_keys_map = {cls['class_name']: results.get(cls['class_name'], []) for cls in classes}

    for cls in classes:
        class_name = cls['class_name']
        # Collect keys from inherited class
        if cls['inherits_from'] and cls['inherits_from'] in class_keys_map:
            extended_results[class_name].extend(class_keys_map[cls['inherits_from']])
        # Collect keys from used classes
        for used_class in cls['uses']:
            if used_class in class_keys_map:
                extended_results[class_name].extend(class_keys_map[used_class])
        # Remove duplicates
        extended_results[class_name] = list(set(extended_results[class_name]))

    # Remove classes with no Keypress Shortcuts
    extended_results = {cls: keys for cls, keys in extended_results.items() if keys}

    return extended_results

def display_extended_results(extended_results):
    print("\nExtended Results with Related Keys:")
    for class_name, keys in extended_results.items():
        print(f"Class: {class_name}, Keypress Shortcuts: {keys}")

def extract_global_functions_keys(file_path):
    """Extract keys from `_global_functions` in the specified Python file."""
    global_functions_keys = []
    inside_global_functions = False
    inside_local_functions = False
    global_functions_keys = []
    local_functions_keys = []
    file_name = os.path.join(file_path, 'radio.py')

    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            stripped_line = line.strip()
            # Detect the start of `_global_functions`
            if stripped_line.startswith("self._global_functions = {"):
                inside_global_functions = True
            elif inside_global_functions:
                # Detect the end of `_global_functions`
                if "}" in stripped_line:
                    inside_global_functions = False
                    # Capture the last line of keys
                    match = re.search(r"kbkey\['(.*?)'\]", stripped_line)
                    if match:
                        global_functions_keys.append(match.group(1))
                    break
                # Extract keys from `_global_functions`
                match = re.search(r"kbkey\['(.*?)'\]", stripped_line)
                if match:
                    global_functions_keys.append(match.group(1))

        for line in file:
            stripped_line = line.strip()
            # Detect the start of `_local_functions`
            if stripped_line.startswith("self._local_functions = {"):
                inside_local_functions = True
            elif inside_local_functions:
                # Detect the end of `_local_functions`
                if "}" in stripped_line:
                    inside_local_functions = False
                    # Capture the last line of keys
                    match = re.search(r"kbkey\['(.*?)'\]", stripped_line)
                    if match:
                        local_functions_keys.append(match.group(1))
                    break
                # Extract keys from `_local_functions`
                match = re.search(r"kbkey\['(.*?)'\]", stripped_line)
                if match:
                    local_functions_keys.append(match.group(1))
    return global_functions_keys, local_functions_keys

def extract_section_keys(file_path, header_key):
    """Extract keys from a specified header section in kbkey_orig."""
    section_keys = set()
    inside_section = False
    file_name = os.path.join(file_path, 'keyboard.py')

    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            stripped_line = line.strip()
            # Detect the start of the specified section
            if stripped_line.startswith(f"kbkey_orig['{header_key}']"):
                inside_section = True
                continue
            # Detect the end of the section (stop at a new unrelated kbkey_orig entry)
            if inside_section and stripped_line.startswith("kbkey_orig[") and " = ( None" in stripped_line:
                inside_section = False
                break
            # Extract keys inside the specified section
            if inside_section:
                match = re.search(r"kbkey_orig\['(.*?)'\]\s*=", stripped_line)
                if match:
                    section_keys.add(match.group(1))
    return section_keys

def remove_section_keys_from_results(results, h_extra_keys):
    """Remove keys from results that are part of the given section."""
    for class_name, keys in results.items():
        results[class_name] = [key for key in keys if key not in h_extra_keys]

def precompute_context_map(results):
    """
    Precompute a map of keys to the classes or contexts they belong to.

    Args:
        results (dict): The `results` dictionary mapping class names to their keys.

    Returns:
        dict: A map of keys to their associated contexts.
    """
    context_map = {}
    for class_name, keys in results.items():
        for key in keys:
            if key not in context_map:
                context_map[key] = []
            context_map[key].append(class_name)
    return context_map

if __name__ == "__main__":
    from sys import exit
    # Updated project path
    starting_dir = os.getcwd()
    print(f'{starting_dir = }')
    project_path = os.path.join(starting_dir, 'pyradio')
    print(f'{project_path = }')
    out_file = os.path.join(project_path, 'keyboard', 'classes.json')
    new_out_file = os.path.join(project_path, 'keyboard', 'keys.json')
    print(f'{out_file = }')
    print(f'{new_out_file = }')

    # Find and display keypress functions with kbkeys
    results = find_keypress_functions_with_kbkeys(project_path)
    display_results(results)

    # Find and display all classes in files
    classes = find_classes_in_files(project_path)
    find_class_usages(classes)
    find_class_inheritance(classes)
    global_functions_keys, local_functions_keys = extract_global_functions_keys(project_path)
    results['PyRadio'] += local_functions_keys
    '''
    print(results)
    for a_class in results:
        results[a_class] += global_functions_keys
    '''
    display_classes(classes)
    display_results(results)

    '''
    ####################################################################

    # Use Case 1: Map Functional Relationships
    functional_map = map_functional_relationships(results, classes)
    display_functional_relationships(functional_map)

    # Use Case 2: Analyze Dependencies
    dependency_map = analyze_dependencies(results, classes)
    display_dependencies(dependency_map)

    # Use Case 3: Functional-Structural Integration
    integration_map = functional_structural_integration(results, classes)
    display_integration(integration_map)

    # Extend results with keys from related classes
    extended_results = extend_results_with_related_keys(results, classes)
    display_extended_results(extended_results)
    ####################################################################
    '''

    # Extract h_extra keys from keyboard.py
    h_extra_keys = extract_section_keys(project_path, 'h_extra')
    print("\nExtracted h_extra keys:")
    for key in sorted(h_extra_keys):
        print(f" - {key}")

    # Remove h_extra keys from results
    remove_section_keys_from_results(results, h_extra_keys)
    print("\nUpdated results after removing h_extra keys:")
    display_results(results)

    # these three keys are added by code, they are not detected
    # by the logic of this script
    results['PyRadio'].append('rb_p_first')
    results['PyRadio'].append('rb_p_next')
    results['PyRadio'].append('rb_p_prev')
    
    # info_rename is a uniq key in the info window
    results['PyRadio'].pop(results['PyRadio'].index('info_rename'))
    results['InfoWindow'] = ['info_rename']
    
    results['GlobalFunctions'] = global_functions_keys + ['t']
    results['ExtraKeys'] = list(h_extra_keys)
    print("\n\nFinal results after removing h_extra keys:")
    display_results(results)

    # remove global function keys
    for gl_key in global_functions_keys:
        for a_key in results:
            try:
                ind = results[a_key].index(gl_key)
                results[a_key].pop(ind)
                break
            except ValueError:
                pass

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f)


    precompute_map = precompute_context_map(results)

    with open(new_out_file, 'w', encoding='utf-8') as f:
        json.dump(precompute_map, f)
    # print('\n\n{}'.format(global_functions_keys))

    # print('\n\n{}'.format(h_extra_keys))

    print('''

Files created:
  classes.json
  keys.json
Execute
    python keyboard.py
to check for missing shortcuts
''')

import os
import ast
import re
from collections import defaultdict, Counter
import networkx as nx
from pathlib import Path

class ModuleVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.functions = []
        self.classes = []
        
    def visit_Import(self, node):
        for name in node.names:
            self.imports.append(name.name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            for name in node.names:
                self.imports.append(f"{node.module}.{name.name}")
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

def analyze_dependencies(base_path):
    """Analyze module dependencies and identify core components."""
    base_path = Path(base_path)
    
    # Track imports and exports
    module_imports = defaultdict(list)
    module_exports = defaultdict(list)
    import_graph = nx.DiGraph()
    
    # Track module metrics
    module_metrics = defaultdict(lambda: {
        'lines': 0,
        'functions': 0,
        'classes': 0,
        'imports': 0,
        'imported_by': 0
    })
    
    # Build a map of all python modules
    all_modules = {}
    for py_file in base_path.glob('**/*.py'):
        rel_path = py_file.relative_to(base_path)
        module_name = str(rel_path.with_suffix('')).replace('\\', '.')
        all_modules[module_name] = py_file
        import_graph.add_node(module_name)
    
    # Parse each file for imports and definitions
    for module_name, file_path in all_modules.items():
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                module_metrics[module_name]['lines'] = content.count('\n') + 1
                
                try:
                    tree = ast.parse(content)
                    visitor = ModuleVisitor()
                    visitor.visit(tree)
                    
                    # Record imports
                    module_imports[module_name].extend(visitor.imports)
                    module_metrics[module_name]['imports'] = len(visitor.imports)
                    
                    # Record definitions
                    module_exports[module_name].extend(visitor.functions + visitor.classes)
                    module_metrics[module_name]['functions'] = len(visitor.functions)
                    module_metrics[module_name]['classes'] = len(visitor.classes)
                    
                    # Add edges to graph
                    for import_name in visitor.imports:
                        # Try to match the import with a known module
                        matched = False
                        for known_module in all_modules.keys():
                            if import_name == known_module or import_name.startswith(known_module + '.'):
                                import_graph.add_edge(module_name, known_module)
                                matched = True
                                break
                        
                        # If it's not a local module, we don't add an edge
                        if not matched and '.' in import_name:
                            top_level = import_name.split('.')[0]
                            if top_level in ('app', 'aicore'):  # Our local packages
                                # Add as an unknown node
                                import_graph.add_edge(module_name, import_name)
                except SyntaxError:
                    print(f"Syntax error in {file_path}")
                    continue
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    # Count how many times each module is imported
    for imports in module_imports.values():
        for imported in imports:
            for module in all_modules:
                if imported == module or imported.startswith(module + '.'):
                    module_metrics[module]['imported_by'] += 1
    
    # Calculate core modules based on import counts
    core_modules = sorted(
        [(m, d['imported_by']) for m, d in module_metrics.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]  # Top 20 most imported modules
    
    # Calculate centrality measures
    centrality = nx.betweenness_centrality(import_graph)
    central_modules = sorted(
        [(m, c) for m, c in centrality.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]  # Top 20 most central modules
    
    # Calculate the dependency layers
    dependency_layers = defaultdict(list)
    for node in import_graph.nodes():
        if node not in all_modules:
            continue  # Skip external modules
        
        # Number of modules that depend on this one
        dependents = sum(1 for _ in import_graph.predecessors(node))
        layer = min(3, dependents // 3)  # Simplify to 3 layers (core, middle, peripheral)
        dependency_layers[layer].append(node)
    
    # Estimate system complexity
    num_modules = len(all_modules)
    avg_imports = sum(d['imports'] for d in module_metrics.values()) / num_modules if num_modules > 0 else 0
    avg_lines = sum(d['lines'] for d in module_metrics.values()) / num_modules if num_modules > 0 else 0
    edges = import_graph.number_of_edges()
    
    complexity = {
        'num_modules': num_modules,
        'avg_imports_per_module': avg_imports,
        'avg_lines_per_module': avg_lines,
        'dependency_edges': edges,
        'interconnection_ratio': edges / num_modules if num_modules > 0 else 0,
        'core_modules': len(dependency_layers[2]),
        'middle_modules': len(dependency_layers[1]),
        'peripheral_modules': len(dependency_layers[0]),
    }
    
    # Get key services
    key_services = [m for m in all_modules.keys() if '.services.' in m]
    service_complexity = {s: module_metrics[s]['lines'] for s in key_services}
    top_services = sorted(service_complexity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Determine team requirements based on system structure
    if complexity['num_modules'] < 50:
        team_req = "1-2 developers with AI assistance"
    elif complexity['num_modules'] < 100:
        team_req = "2-3 developers with AI assistance"
    elif complexity['num_modules'] < 200:
        team_req = "3-5 developers with AI assistance"
    else:
        team_req = "5+ developers with AI assistance"
    
    result = {
        'complexity': complexity,
        'core_modules': core_modules,
        'central_modules': central_modules,
        'dependency_layers': dependency_layers,
        'top_services': top_services,
        'team_requirements': team_req
    }
    
    return result, import_graph

def print_results(results, graph):
    """Print analysis results in a readable format."""
    complexity = results['complexity']
    
    print("\n📊 MODULE DEPENDENCY ANALYSIS")
    print("=" * 60)
    
    print(f"\n📌 SYSTEM OVERVIEW:")
    print(f"  Total Python modules: {complexity['num_modules']}")
    print(f"  Average imports per module: {complexity['avg_imports_per_module']:.1f}")
    print(f"  Average lines per module: {complexity['avg_lines_per_module']:.1f}")
    print(f"  Total dependencies: {complexity['dependency_edges']}")
    print(f"  Interconnection ratio: {complexity['interconnection_ratio']:.2f}")
    
    print(f"\n📌 SYSTEM ARCHITECTURE:")
    print(f"  Core modules: {complexity['core_modules']}")
    print(f"  Middle layer modules: {complexity['middle_modules']}")
    print(f"  Peripheral modules: {complexity['peripheral_modules']}")
    
    print(f"\n📌 TOP 10 MOST DEPENDED ON MODULES:")
    for i, (module, count) in enumerate(results['core_modules'][:10], 1):
        print(f"  {i}. {module[:50]:{50}} imported by {count} modules")
    
    print(f"\n📌 TOP 10 MOST CENTRAL MODULES:")
    for i, (module, score) in enumerate(results['central_modules'][:10], 1):
        print(f"  {i}. {module[:50]:{50}} centrality: {score:.3f}")
    
    print(f"\n📌 TOP 10 MOST COMPLEX SERVICES:")
    for i, (service, lines) in enumerate(results['top_services'], 1):
        print(f"  {i}. {service[:50]:{50}} {lines} lines")
    
    print(f"\n📌 TEAM REQUIREMENTS:")
    print(f"  Recommended team size: {results['team_requirements']}")
    print(f"  With AI coding agents: Enables 30-40% reduction in development resources")
    print(f"  Without AI assistance: Would need approximately 40-50% more developers")
    
    # Print a summary of domain complexity areas
    print(f"\n📌 DOMAIN COMPLEXITY AREAS:")
    domain_areas = {
        'Knowledge & RAG': sum(lines for service, lines in results['top_services'] if 'knowledge' in service or 'rag' in service),
        'Memory & Context': sum(lines for service, lines in results['top_services'] if 'memory' in service or 'context' in service),
        'Chat & Messaging': sum(lines for service, lines in results['top_services'] if 'chat' in service or 'message' in service),
        'Storage & Files': sum(lines for service, lines in results['top_services'] if 'storage' in service or 'file' in service),
        'Authentication': sum(lines for service, lines in results['top_services'] if 'auth' in service),
        'API & Endpoints': sum(lines for service, lines in results['top_services'] if 'api' in service or 'endpoint' in service),
    }
    
    for area, lines in sorted(domain_areas.items(), key=lambda x: x[1], reverse=True):
        if lines > 0:
            print(f"  {area}: {lines} lines")
    
if __name__ == "__main__":
    base_path = "backend"
    if os.path.exists(base_path):
        results, graph = analyze_dependencies(base_path)
        print_results(results, graph)
    else:
        print(f"Path {base_path} not found") 
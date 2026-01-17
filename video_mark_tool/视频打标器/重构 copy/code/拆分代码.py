import ast
import os
import re

def split_functions_from_file(source_file_path, exclude_functions=None):
    """
    读取指定的.py文件，提取所有def函数，为每个函数创建单独的文件存放，
    并在原文件中用import替换对应函数
    """
    # 读取源文件内容
    with open(source_file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # 解析源代码获取函数信息
    tree = ast.parse(source_code)
    
    # 提取所有顶层函数定义（只处理模块级别的函数）
    functions = []
    classes = []
    
    # 遍历模块中的节点
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append({
                'name': node.name,
                'lineno': node.lineno,
                'end_lineno': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                'type': 'function',
                'class_name': None
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                'name': node.name,
                'lineno': node.lineno,
                'end_lineno': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                'methods': []
            })
            # 提取类中的方法
            for method_node in node.body:
                if isinstance(method_node, ast.FunctionDef):
                    # 排除特殊方法
                    if not method_node.name.startswith('__') or method_node.name in ['__init__']:
                        classes[-1]['methods'].append({
                            'name': method_node.name,
                            'lineno': method_node.lineno,
                            'end_lineno': method_node.end_lineno if hasattr(method_node, 'end_lineno') else method_node.lineno,
                            'type': 'method',
                            'class_name': node.name
                        })

    # 收集所有需要处理的函数（包括类方法）
    all_functions = functions[:]
    for cls in classes:
        for method in cls['methods']:
            all_functions.append(method)
    
    # 默认应排除的函数列表（通常是核心类方法和事件处理函数）
    default_exclude_functions = [
        '__init__',           # 构造函数
        'setup_ui'           # UI设置函数
    ]
    
    # 合并传入的排除列表和默认排除列表
    if exclude_functions:
        exclude_functions = set(exclude_functions + default_exclude_functions)
    else:
        exclude_functions = set(default_exclude_functions)
    
    # 过滤掉需要排除的函数
    all_functions = [func for func in all_functions if func['name'] not in exclude_functions]
    
    if not all_functions:
        print("未找到任何需要处理的函数定义")
        return
    
    # 获取文件名（不含扩展名）
    file_dir = os.path.dirname(source_file_path)
    file_name = os.path.basename(source_file_path)
    file_base_name = os.path.splitext(file_name)[0]
    
    # 按行分割源代码
    source_lines = source_code.split('\n')
    
    # 提取原始文件中的导入语句
    import_statements = []
    for line in source_lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('import ', 'from ')) and 'import' in stripped_line:
            import_statements.append(line)
    
    # 添加: 去除重复的导入语句
    unique_import_statements = []
    seen_imports = set()
    for imp in import_statements:
        stripped_imp = imp.strip()
        if stripped_imp not in seen_imports:
            unique_import_statements.append(imp)
            seen_imports.add(stripped_imp)
    
    import_statements = unique_import_statements
    
    # 为每个函数创建单独的文件
    for func in all_functions:
        # 提取函数代码
        func_lines = source_lines[func['lineno']-1:func['end_lineno']]
        
        # 计算并移除公共缩进
        # 首先找到所有非空行的前导空白
        leading_whitespaces = []
        for line in func_lines:
            if line.strip():  # 非空行
                # 计算前导空白字符
                leading = len(line) - len(line.lstrip())
                leading_whitespaces.append(line[:leading])
        
        # 找到最小的公共前导空白
        if leading_whitespaces:
            # 找到所有前导空白的公共前缀
            common_leading = os.path.commonprefix(leading_whitespaces)
        else:
            common_leading = ""
        
        # 移除公共前导空白
        stripped_func_lines = []
        for line in func_lines:
            if line.startswith(common_leading):
                stripped_func_lines.append(line[len(common_leading):])
            else:
                stripped_func_lines.append(line)
        
        # 处理类方法的特殊情况
        if func['type'] == 'method':
            # 为类方法添加适当的装饰器和注释
            processed_lines = []
            processed_lines.append(f"# This is a method from class {func['class_name']}")
            processed_lines.append("from functools import partial")
            processed_lines.append("")
            
            # 添加导入语句
            if import_statements:
                # 确保import语句没有缩进
                for imp in import_statements:
                    processed_lines.append(imp.lstrip())  # 移除缩进
                processed_lines.append("")
            
            # 添加类方法的模拟实现或注释
            processed_lines.extend(stripped_func_lines)
            processed_lines.append("")
            processed_lines.append(f"# Note: This was originally a method of class {func['class_name']}")
            processed_lines.append(f"# You may need to adjust the implementation based on class context")
            processed_lines.append(f"__all__ = ['{func['name']}']")
            
            func_content = '\n'.join(processed_lines) + '\n'
        else:
            # 在函数文件中添加导入语句
            func_content = ""
            if import_statements:
                # 确保import语句没有缩进
                for imp in import_statements:
                    func_content += imp.lstrip() + "\n"  # 移除缩进
                func_content += "\n"
            func_content += '\n'.join(stripped_func_lines) + '\n\n'
            
            # 添加__all__以便导入
            func_content += f"__all__ = ['{func['name']}']\n"
        
        # 创建单个函数文件路径（类方法使用不同的命名方式）
        if func['type'] == 'method':
            func_file_name = f"{func['class_name']}_{func['name']}.py"
        else:
            func_file_name = f"{func['name']}.py"
            
        func_file_path = os.path.join(file_dir, func_file_name)
        
        # 写入函数文件
        with open(func_file_path, 'w', encoding='utf-8') as f:
            f.write(func_content)
        
        print(f"已创建函数文件: {func_file_path}")
    
    # 构建修改后的原文件内容
    # 从后往前替换，避免行号变化影响
    modified_source_lines = source_lines.copy()
    
    # 按照从后往前的顺序处理函数（避免行号偏移）
    for func in sorted(all_functions, key=lambda x: x['lineno'], reverse=True):
        start_line = func['lineno'] - 1
        end_line = func['end_lineno']
        
        # 计算缩进
        first_line = modified_source_lines[start_line]
        indent = ""
        for char in first_line:
            if char in [' ', '\t']:
                indent += char
            else:
                break
        
        # 用import语句替换函数定义
        if func['type'] == 'method':
            import_statement = f"{indent}from {func['class_name']}_{func['name']} import {func['name']}"
        else:
            import_statement = f"{indent}from {func['name']} import {func['name']}"
            
        # 删除函数定义的行
        del modified_source_lines[start_line:end_line]
        # 插入import语句
        modified_source_lines.insert(start_line, import_statement)
    
    # 在文件开头添加导入语句（如果还没有导入）
    # 找到第一个非注释非空行的位置
    insert_pos = 0
    for i, line in enumerate(modified_source_lines):
        if line.strip() and not line.strip().startswith('#'):
            insert_pos = i
            break
    
    # 添加必要的导入语句
    import_lines_added = 0
    for func in all_functions:
        if func['type'] == 'method':
            import_line = f"from {func['class_name']}_{func['name']} import {func['name']}\n"
        else:
            import_line = f"from {func['name']} import {func['name']}\n"
            
        if import_line not in modified_source_lines:
            modified_source_lines.insert(insert_pos + import_lines_added, import_line)
            import_lines_added += 1
    
    # 写回原文件
    with open(source_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(modified_source_lines))
    
    print(f"成功为 {len(all_functions)} 个函数创建单独的文件")
    print(f"已更新原文件 {source_file_path}")
    print(f"保留的函数: {', '.join(exclude_functions)}")

# 使用示例 - 可以指定要排除的函数列表
split_functions_from_file("video_tagger.py")
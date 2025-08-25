#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import re
import argparse

def run_command(cmd, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, 
                              text=True, encoding='utf-8', errors='ignore')
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"返回码: {result.returncode}")
            if result.stderr:
                print(f"错误输出: {result.stderr}")
            if result.stdout:
                print(f"标准输出: {result.stdout}")
            return None
        return result.stdout.strip() if capture_output else True
    except Exception as e:
        print(f"执行命令时发生异常: {cmd}")
        print(f"异常: {e}")
        return None

def get_branch_commits(branch):
    """获取指定分支的所有commit信息"""
    print(f"获取{branch}分支的commit历史...")
    cmd = f"git log {branch} --oneline --reverse"
    output = run_command(cmd)
    
    if not output:
        print("无法获取commit历史")
        return []
    
    commits = []
    for i, line in enumerate(output.split('\n')):
        if line.strip():
            parts = line.split(' ', 1)
            if len(parts) >= 2:
                commit_id = parts[0]
                description = parts[1]
                # 清理描述中的特殊字符，用于文件名
                safe_description = re.sub(r'[<>:"/\\|?*]', '_', description)
                commits.append({
                    'id': commit_id,
                    'description': description,
                    'safe_description': safe_description,
                    'index': i + 1
                })
    
    return commits

def create_output_directory(dir_name):
    """创建输出目录"""
    output_dir = os.path.join(".", dir_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建目录: {output_dir}")
    else:
        print(f"目录已存在: {output_dir}")
    return output_dir

def generate_tree_for_commit(commit_info, tree_dir, tree_mine_cmd):
    """为指定commit生成目录树"""
    commit_id = commit_info['id']
    index = commit_info['index']
    safe_description = commit_info['safe_description']
    
    print(f"\n处理第{index}个commit: {commit_id} - {commit_info['description']}")
    
    # 切换到指定commit
    print(f"  切换到commit: {commit_id}")
    if not run_command(f"git reset --hard {commit_id}"):
        print(f"  失败: 无法切换到commit {commit_id}")
        return False
    
    # 生成输出文件名
    output_filename = f"{index:02d}_{safe_description}.txt"
    output_path = os.path.join(tree_dir, output_filename)
    
    # 在当前目录运行tree_mine命令
    output_path_abs = os.path.abspath(output_path)
    full_cmd = f'{tree_mine_cmd} --to "{output_path_abs}"'
    print(f"  运行: {full_cmd}")
    
    result = run_command(full_cmd, capture_output=True)
    if result is not None:
        print(f"  成功: 生成目录树 -> {output_filename}")
        if os.path.exists(output_path):
            print(f"  确认文件已创建: {output_path}")
        else:
            print(f"  警告: 文件未找到: {output_path}")
        return True
    else:
        print(f"  失败: 无法生成目录树")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='生成项目各版本的目录树快照',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''使用示例:
  %(prog)s --exclude ".git"
  %(prog)s --exclude "node_modules" "dist" --output_dir snapshots
  %(prog)s --branch develop --exclude "build"''')
    
    parser.add_argument('--exclude', 
                       nargs='*',
                       default=[".claude",".git",".gradle",".idea","build","dist","node_modules","app/build","tree"],
                       help='要排除的目录或文件 (默认: %(default)s)')
    
    parser.add_argument('--output_dir', 
                       default='tree',
                       help='输出目录名称 (默认: %(default)s)')
    
    parser.add_argument('--branch',
                       default='main',
                       help='要处理的分支名称 (默认: %(default)s)')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 构建tree_mine命令
    tree_mine_cmd = "tree_mine.exe"
    if args.exclude:
        exclude_args = " ".join([f'"{item}"' for item in args.exclude])
        tree_mine_cmd += f" --exclude {exclude_args}"
    
    print("开始生成项目各版本的目录树快照...")
    print(f"分支: {args.branch}")
    print(f"输出目录: {args.output_dir}")
    print(f"排除项: {args.exclude}")
    print(f"Tree命令: {tree_mine_cmd}")
    
    # 检查是否在git仓库中
    if not run_command("git status"):
        print("错误: 当前目录不是git仓库")
        sys.exit(1)
    
    # 检查tree_mine.exe是否可用
    if not run_command("tree_mine.exe --help"):
        print("错误: 找不到 tree_mine.exe，请确保它在PATH环境变量中")
        sys.exit(1)
    
    # 保存当前分支
    current_branch = run_command("git branch --show-current")
    print(f"当前分支: {current_branch}")
    
    try:
        # 获取指定分支的所有commit
        commits = get_branch_commits(args.branch)
        if not commits:
            print(f"没有找到分支 {args.branch} 的任何commit")
            sys.exit(1)
        
        print(f"找到 {len(commits)} 个commit")
        
        # 创建输出目录
        tree_dir = create_output_directory(args.output_dir)
        
        # 为每个commit生成目录树
        success_count = 0
        for commit_info in commits:
            if generate_tree_for_commit(commit_info, tree_dir, tree_mine_cmd):
                success_count += 1
            else:
                print(f"警告: commit {commit_info['id']} 处理失败")
        
        print(f"\n完成! 成功处理 {success_count}/{len(commits)} 个commit")
        
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
    except Exception as e:
        print(f"\n发生异常: {e}")
    finally:
        # 恢复到原来的分支
        if current_branch:
            print(f"\n恢复到原分支: {current_branch}")
            run_command(f"git checkout {current_branch}")
        else:
            print("\n恢复到study分支")
            run_command("git checkout study")

if __name__ == "__main__":
    main()
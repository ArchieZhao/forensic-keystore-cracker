#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的结果分析脚本 - 直接调用批量结果分析器
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def main():
    try:
        from batch_result_analyzer import BatchResultAnalyzer

        print("=" * 60)
        print("批量破解结果分析器")
        print("=" * 60)

        analyzer = BatchResultAnalyzer()
        success = analyzer.analyze_and_report()

        if success:
            print("\n✅ 结果分析完成!")
            print("查看生成的文件:")
            print("  - batch_crack_output/batch_crack_results_*.xlsx")
            print("  - batch_crack_output/batch_crack_results_*.json")
            return 0
        else:
            print("\n❌ 结果分析失败")
            return 1

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保所有模块文件都在同一目录")
        return 1
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

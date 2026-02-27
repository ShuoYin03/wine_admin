import csv
from datetime import datetime

def filter_december_2025(input_file, output_file):
    """
    筛选 CSV 文件中 auction_start_date 在 2025 年 12 月的记录
    """
    december_2025_rows = []
    header = None
    
    # 读取 CSV 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        
        for row in reader:
            auction_start_date = row.get('auction_start_date', '')
            
            # 检查日期是否为 2025-12-XX 格式
            if auction_start_date.startswith('2025-12'):
                december_2025_rows.append(row)
    
    # 写入筛选后的结果
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(december_2025_rows)
    
    print(f"筛选完成！")
    print(f"找到 {len(december_2025_rows)} 条 2025 年 12 月的记录")
    print(f"结果已保存到: {output_file}")

if __name__ == '__main__':
    input_file = 'Baghera_lots.csv'
    output_file = 'Baghera_lots_december_2025.csv'
    
    filter_december_2025(input_file, output_file)

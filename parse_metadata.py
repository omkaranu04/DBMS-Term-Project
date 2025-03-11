import re
import pandas as pd

def parse_metadata_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split by product entries
    products = re.split(r'\n\nId:\s+', content)
    if products[0].startswith('Id:'):
        products[0] = products[0][3:]  # Handle first product
    else:
        products = products[1:]  # Skip header if exists
    
    product_data = []
    
    for product in products:
        if not product.strip():
            continue
            
        # Extract basic info
        product_id = product.split('\n')[0].strip()
        asin_match = re.search(r'ASIN:\s+(.*?)$', product, re.MULTILINE)
        asin = asin_match.group(1) if asin_match else None
        
        title_match = re.search(r'title:\s+(.*?)$', product, re.MULTILINE)
        title = title_match.group(1) if title_match else None
        
        group_match = re.search(r'group:\s+(.*?)$', product, re.MULTILINE)
        group = group_match.group(1) if group_match else None
        
        salesrank_match = re.search(r'salesrank:\s+(\d+)', product)
        salesrank = int(salesrank_match.group(1)) if salesrank_match else None
        
        # Extract categories
        categories = []
        categories_section = re.search(r'categories:\s+(\d+)(.*?)(?:reviews:|$)', 
                                     product, re.DOTALL)
        if categories_section:
            category_lines = categories_section.group(2).strip().split('\n')
            for line in category_lines:
                if line.strip().startswith('|'):
                    categories.append(line.strip())
        
        # Extract reviews summary
        reviews_match = re.search(r'reviews: total:\s+(\d+)\s+downloaded:\s+(\d+)\s+avg rating:\s+([\d\.]+)', 
                                product)
        if reviews_match:
            total_reviews = int(reviews_match.group(1))
            avg_rating = float(reviews_match.group(3)) if reviews_match.group(3) != '0' else None
        else:
            total_reviews = 0
            avg_rating = None
            
        # Build product dictionary
        product_dict = {
            'id': int(product_id),
            'asin': asin,
            'title': title,
            'group': group,
            'salesrank': salesrank,
            'categories': '|'.join(categories) if categories else None,
            'total_reviews': total_reviews,
            'avg_rating': avg_rating
        }
        
        product_data.append(product_dict)
    
    return pd.DataFrame(product_data)

# Parse metadata and save to CSV
metadata_df = parse_metadata_file('Amazon Dataset/amazon-meta.txt')
metadata_df.to_csv('amazon_products.csv', index=False)
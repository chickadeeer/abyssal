from mcp.server.fastmcp import FastMCP
import curl_cffi.requests as requests
import json
import re
import os
from urllib.parse import quote
from bs4 import BeautifulSoup

mcp = FastMCP("LobeHubSkillsSearch")

def write_skill_to_abyssal(name, content, description, skill_folder):
    
    import json
    from pathlib import Path
    from datetime import datetime
    
    
    skill_folder.mkdir(parents=True, exist_ok=True)
    
    
    meta_file = skill_folder / 'skill.json'
    if meta_file.exists():
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    else:
        meta = {
            'name': name,
            'description': description or name,
            'version': 0,
            'versions': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'history': []
        }
    
    
    new_version = meta.get('versions', 0) + 1
    meta['versions'] = new_version
    meta['version'] = new_version
    meta['updated_at'] = datetime.now().isoformat()
    meta['description'] = description or meta.get('description', name)
    
    
    meta['history'].append({
        'version': new_version,
        'note': f"Imported from LobeHub: {name}",
        'at': datetime.now().isoformat()
    })
    
    
    content_file = skill_folder / f'v{new_version}.md'
    content_file.write_text(content, encoding='utf-8')
    
    
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    return {
        'status': 'success',
        'name': name,
        'version': new_version,
        'path': str(skill_folder),
        'message': f"Skill '{name}' saved as version {new_version}"
    }

@mcp.tool()
def search(query: str, page: int = 1) -> str:
    
    try:
        url = f"https://lobehub.com/skills?q={quote(query)}&page={page}"
        response = requests.get(url, impersonate="chrome")
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        skill_cards = []
        cards = soup.find_all('div', class_=lambda c: c and 'acss-1gs1mq9' in c)
        
        for card in cards:
            
            name_elem = card.find('h2', class_=lambda c: c and 'acss-1hskjtg' in c)
            name = name_elem.get_text(strip=True) if name_elem else None
            
            
            desc_elem = card.find('p', class_=lambda c: c and 'acss-sjzrav' in c)
            description = desc_elem.get_text(strip=True) if desc_elem else None
            
            
            category_elem = card.find('div', class_=lambda c: c and 'acss-1xcok0i' in c)
            if category_elem:
                category_spans = category_elem.find_all('span')
                
                category = category_spans[-1].get_text(strip=True) if len(category_spans) > 1 else 'Uncategorized'
            else:
                category = 'Uncategorized'
            
            
            link_elem = card.find_parent('a')
            link = link_elem.get('href') if link_elem else None
            
            
            full_name = None
            if link:
                
                full_name = link.rstrip('/').split('/')[-1]
            if not full_name:
                full_name = name
            
            if name and description:
                skill_cards.append({
                    'name': name,
                    'full_name': full_name,
                    'author': 'unknown',
                    'description': description,
                    'category': category,
                    'category_id': len(category_spans) > 1 and category_spans[0].get_text(strip=True) if category_elem else None,
                    'url': f"https://lobehub.com{link}" if link else None
                })
        
        
        pagination = soup.find('ul', class_=lambda c: c and 'ant-pagination' in c)
        total_pages = 1
        if pagination:
            page_items = pagination.find_all('li', class_=lambda c: c and 'ant-pagination-item' in c)
            if page_items:
                total_pages = max([int(item.get_text(strip=True)) for item in page_items if item.get_text(strip=True).isdigit()], default=1)
        
        return json.dumps({
            'query': query,
            'page': page,
            'total_pages': total_pages,
            'count': len(skill_cards),
            'results': skill_cards
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_skill(skill_name: str) -> str:
    
    try:
        url = f"https://lobehub.com/skills/{quote(skill_name)}/skill.md"
        response = requests.get(url, impersonate="chrome")
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching skill: {str(e)}"

@mcp.tool()
def add_skill(skill_name: str, overwrite: bool = False, full_name: str = None) -> str:
    
    import re
    from pathlib import Path
    from datetime import datetime
    
    try:
        
        skills_dir = Path.home() / '.abyssal-cli' / 'skills'
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        
        safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', skill_name.strip())[:48]
        skill_folder = skills_dir / safe_name
        
        
        if skill_folder.exists() and not overwrite:
            return json.dumps({
                'status': 'skipped',
                'message': f"Skill '{skill_name}' already exists. Use overwrite=True to replace."
            }, indent=2)
        
        
        path_name = full_name if full_name else skill_name
        
        
        url = f"https://lobehub.com/skills/{quote(path_name)}/skill.md"
        response = requests.get(url, impersonate="chrome")
        response.raise_for_status()
        content = response.text
        
        
        search_url = f"https://lobehub.com/skills?q={quote(skill_name)}&page=1"
        search_response = requests.get(search_url, impersonate="chrome")
        search_response.raise_for_status()
        
        soup = BeautifulSoup(search_response.text, 'html.parser')
        description = skill_name  
        
        
        for card in soup.find_all('div', class_=lambda c: c and 'acss-1gs1mq9' in c):
            name_elem = card.find('h2', class_=lambda c: c and 'acss-1hskjtg' in c)
            if name_elem and name_elem.get_text(strip=True) == skill_name:
                desc_elem = card.find('p', class_=lambda c: c and 'acss-sjzrav' in c)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                break
        
        
        result = write_skill_to_abyssal(safe_name, content, description, skill_folder)
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
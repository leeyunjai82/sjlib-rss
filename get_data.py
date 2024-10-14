import requests
from bs4 import BeautifulSoup
import time
import re  # 정규표현식 모듈 임포트
import json
import datetime

# RSS 피드 URL
rss_url = 'https://rss.blog.naver.com/sjlib24.xml'

# 헤더 설정
headers = {'User-Agent': 'Mozilla/5.0'}

# 데이터를 저장할 리스트 초기화
data_list = []

try:
    # RSS 피드 요청
    response = requests.get(rss_url, headers=headers)
    response.raise_for_status()
    # 'lxml-xml' 파서 사용
    soup = BeautifulSoup(response.content, 'lxml-xml')

    # 게시글 목록 추출
    items = soup.find_all('item')
    if not items:
        print("RSS 피드에서 게시글을 찾을 수 없습니다.")
        exit()

    # category와 date 설정
    category = '문헌정보실 테마도서'
    date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for item in items:
        # 게시글 정보 추출
        post_title = item.find('title').get_text(strip=True)
        post_description = item.find('description').get_text(strip=True)
        post_category = item.find('category').get_text(strip=True) if item.find('category') else '카테고리 없음'

        if post_category != category:
            continue

        # 요약 처리
        original_description = post_description

        # 괄호 안의 내용 제거 (내용에서 태그를 제거하기 위해)
        description_no_parentheses = re.sub(r'\s*\(.*?\)\s*', '', post_description)

        # 요약 앞에 '1' 추가
        if not description_no_parentheses.strip().startswith('1'):
            description_no_parentheses = '1. ' + description_no_parentheses.strip()

        # 항목별로 분리
        items_content = re.split(r'\s*\d+\.\s*', description_no_parentheses)
        # 첫 번째 빈 항목 제거
        items_content = [item for item in items_content if item.strip()]

        # 원본에서 태그 추출
        tags_in_parentheses = re.findall(r'\(.*?\)', original_description)

        # 각 항목별 데이터와 태그를 매칭하여 리스트 생성
        summary_list = []
        for idx, content in enumerate(items_content):
            # 내용 앞뒤 공백 제거
            content = content.strip()

            # 해당하는 태그 추출
            if idx < len(tags_in_parentheses):
                tags = tags_in_parentheses[idx]
                # 괄호와 '#' 제거하고, ','로 연결
                tags = re.sub(r'[()\s#]+', ' ', tags).strip()
                tags = ', '.join(tags.split())
            else:
                tags = ''

            summary_list.append({'data': content, 'tag': tags})

        # 데이터 리스트에 추가
        data_list.append({
            'title': post_title,
            'summary': summary_list
        })

        # 지연 시간 추가
        time.sleep(1)

except Exception as e:
    print(f"오류 발생: {e}")

# 최종 데이터 구성
output_data = {
    'category': category,
    'date': date,
    'data': data_list
}

# JSON 파일로 저장
with open('record.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

